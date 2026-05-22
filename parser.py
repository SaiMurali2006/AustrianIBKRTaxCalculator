"""IBKR Flex XML parser for Austrian tax categories."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


TRADE_COLUMNS = [
    "date",
    "datetime",
    "currency",
    "fxRateToBase",
    "assetCategory",
    "symbol",
    "description",
    "isin",
    "quantity",
    "tradePrice",
    "proceeds",
    "ibCommission",
    "openCloseIndicator",
    "cost",
    "fifoPnlRealized",
    "buySell",
]

CASH_COLUMNS = [
    "date",
    "datetime",
    "currency",
    "fxRateToBase",
    "symbol",
    "description",
    "isin",
    "amount",
    "type",
    "tax",
]


@dataclass
class ParsedFlexData:
    stocks: pd.DataFrame
    options: pd.DataFrame
    dividends: pd.DataFrame
    interest: pd.DataFrame
    funds: pd.DataFrame
    cash_other: pd.DataFrame
    all_trades: pd.DataFrame
    all_cash: pd.DataFrame


def parse_flex_xml(source: str | Path | bytes) -> ParsedFlexData:
    root = _load_xml(source)
    trades = [_normalise_trade(node.attrib) for node in root.findall(".//Trade")]
    cash = [_normalise_cash(node.attrib) for node in root.findall(".//CashTransaction")]

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    cash_df = pd.DataFrame(cash, columns=CASH_COLUMNS)

    if not trades_df.empty:
        trades_df["assetCategory"] = trades_df["assetCategory"].str.upper()

    if not cash_df.empty:
        cash_df["type"] = cash_df["type"].fillna("")
        cash_df["description"] = cash_df["description"].fillna("")

    funds = trades_df[trades_df["assetCategory"].eq("FUND")].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)
    stocks = trades_df[trades_df["assetCategory"].eq("STK")].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)
    options = trades_df[trades_df["assetCategory"].isin(["OPT", "FOP", "WAR", "IOPT"])].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)

    dividends = _cash_filter(cash_df, ["dividend", "payment in lieu", "withholding"])
    interest = _cash_filter(cash_df, ["interest"])
    cash_other = cash_df.drop(index=dividends.index.union(interest.index), errors="ignore").copy() if not cash_df.empty else _empty(CASH_COLUMNS)

    return ParsedFlexData(
        stocks=stocks.reset_index(drop=True),
        options=options.reset_index(drop=True),
        dividends=dividends.reset_index(drop=True),
        interest=interest.reset_index(drop=True),
        funds=funds.reset_index(drop=True),
        cash_other=cash_other.reset_index(drop=True),
        all_trades=trades_df.reset_index(drop=True),
        all_cash=cash_df.reset_index(drop=True),
    )


def _load_xml(source: str | Path | bytes) -> ET.Element:
    if isinstance(source, bytes):
        return ET.fromstring(source)
    candidate = Path(str(source))
    if candidate.exists():
        return ET.parse(candidate).getroot()
    return ET.fromstring(str(source).encode("utf-8"))


def _normalise_trade(attrs: dict[str, str]) -> dict[str, object]:
    date_time = attrs.get("dateTime", "")
    return {
        "date": date_time.split(";")[0],
        "datetime": date_time,
        "currency": attrs.get("currency", "EUR"),
        "fxRateToBase": _num(attrs.get("fxRateToBase")),
        "assetCategory": attrs.get("assetCategory", ""),
        "symbol": attrs.get("symbol", ""),
        "description": attrs.get("description", ""),
        "isin": attrs.get("isin", ""),
        "quantity": _num(attrs.get("quantity")),
        "tradePrice": _num(attrs.get("tradePrice")),
        "proceeds": _num(attrs.get("proceeds")),
        "ibCommission": _num(attrs.get("ibCommission")),
        "openCloseIndicator": attrs.get("openCloseIndicator", ""),
        "cost": _num(attrs.get("cost")),
        "fifoPnlRealized": _num(attrs.get("fifoPnlRealized")),
        "buySell": attrs.get("buySell", "").upper(),
    }


def _normalise_cash(attrs: dict[str, str]) -> dict[str, object]:
    date_time = attrs.get("dateTime", attrs.get("settleDate", ""))
    return {
        "date": date_time.split(";")[0],
        "datetime": date_time,
        "currency": attrs.get("currency", "EUR"),
        "fxRateToBase": _num(attrs.get("fxRateToBase")),
        "symbol": attrs.get("symbol", ""),
        "description": attrs.get("description", ""),
        "isin": attrs.get("isin", ""),
        "amount": _num(attrs.get("amount")),
        "type": attrs.get("type", ""),
        "tax": _num(attrs.get("tax")),
    }


def _cash_filter(df: pd.DataFrame, needles: Iterable[str]) -> pd.DataFrame:
    if df.empty:
        return _empty(CASH_COLUMNS)
    pattern = "|".join(needles)
    haystack = (df["type"].fillna("") + " " + df["description"].fillna("")).str.lower()
    return df[haystack.str.contains(pattern, regex=True)].copy()


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _num(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

