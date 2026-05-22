"""Currency conversion helpers using ECB reference rates with local caching."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"


def parse_ib_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.split(";")[0].strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class FxRate:
    trade_date: date
    currency: str
    eur_rate: float
    source: str


class ECBRateProvider:
    """Returns currency-to-EUR rates.

    ECB publishes rates as one EUR equals N units of foreign currency. For tax
    calculations we need one unit of foreign currency in EUR, so USD 1 becomes
    1 / ECB_USD_RATE.
    """

    def __init__(self, cache_path: str | Path = ".cache/ecb_rates.json") -> None:
        self.cache_path = Path(cache_path)
        self._rates: dict[str, dict[str, float]] = {}
        self._load_cache()

    def get_rate(
        self,
        currency: str,
        trade_date: date | str | None,
        fallback_fx_to_base: float | str | None = None,
    ) -> FxRate:
        currency = (currency or "EUR").upper()
        parsed_date = parse_ib_date(trade_date) if isinstance(trade_date, str) else trade_date
        parsed_date = parsed_date or date.today()
        if currency == "EUR":
            return FxRate(parsed_date, currency, 1.0, "EUR base")

        date_key = parsed_date.isoformat()
        if date_key not in self._rates:
            self._fetch_recent_rates()

        rate = self._rates.get(date_key, {}).get(currency)
        if rate:
            return FxRate(parsed_date, currency, 1.0 / rate, "ECB")

        nearest = self._nearest_prior_rate(currency, parsed_date)
        if nearest:
            nearest_date, ecb_rate = nearest
            return FxRate(nearest_date, currency, 1.0 / ecb_rate, "ECB previous business day")

        fallback = _to_float(fallback_fx_to_base)
        if fallback and fallback > 0:
            return FxRate(parsed_date, currency, fallback, "IBKR fxRateToBase fallback")

        return FxRate(parsed_date, currency, 1.0, "Missing FX rate fallback")

    def convert(
        self,
        amount: float,
        currency: str,
        trade_date: date | str | None,
        fallback_fx_to_base: float | str | None = None,
    ) -> tuple[float, FxRate]:
        fx = self.get_rate(currency, trade_date, fallback_fx_to_base)
        return amount * fx.eur_rate, fx

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            self._rates = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._rates = {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._rates, indent=2, sort_keys=True), encoding="utf-8")

    def _fetch_recent_rates(self) -> None:
        try:
            with urlopen(ECB_DAILY_URL, timeout=8) as response:
                payload = response.read().decode("utf-8")
        except (OSError, URLError):
            return

        import xml.etree.ElementTree as ET

        root = ET.fromstring(payload)
        namespaces = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        for day in root.findall(".//ecb:Cube[@time]", namespaces):
            day_key = day.attrib["time"]
            self._rates.setdefault(day_key, {})
            for cube in day.findall("ecb:Cube", namespaces):
                currency = cube.attrib.get("currency")
                rate = _to_float(cube.attrib.get("rate"))
                if currency and rate:
                    self._rates[day_key][currency.upper()] = rate
        self._save_cache()

    def _nearest_prior_rate(self, currency: str, trade_date: date) -> tuple[date, float] | None:
        candidates: list[tuple[date, float]] = []
        for date_key, rates in self._rates.items():
            rate = rates.get(currency)
            if not rate:
                continue
            try:
                candidate_date = datetime.strptime(date_key, "%Y-%m-%d").date()
            except ValueError:
                continue
            if candidate_date <= trade_date:
                candidates.append((candidate_date, rate))
        return max(candidates, key=lambda item: item[0]) if candidates else None

    def export_cache_csv(self, path: str | Path) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "currency", "ecb_rate_per_eur"])
            for day, rates in sorted(self._rates.items()):
                for currency, rate in sorted(rates.items()):
                    writer.writerow([day, currency, rate])


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

