"""Austrian KESt engine — broker-agnostic, operates on ParsedData.

E1kv Kennzahl mapping (foreign broker, e.g. IBKR):
  994  realized capital gains, stocks/ETFs/bonds (27.5%)
  892  realized capital losses, stocks/ETFs/bonds and non-securitised derivatives (27.5%)
  981  derivative gains, non-securitised (27.5%)
  863  foreign dividends and bond-coupon interest (27.5%)
  861  foreign bank deposit interest (25%)
  998  creditable foreign withholding tax (27.5% basket)
  901  creditable foreign withholding tax (25% basket)

Two baskets are computed independently:
  27.5% basket — stocks, derivatives, dividends, bond interest. §27a Abs. 1 EStG.
  25%   basket — bank/savings deposit interest only. §27a Abs. 2 EStG.
Losses do NOT cross the basket boundary, and neither basket carries forward to next year.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from currency_provider import ECBRateProvider
from models import ParsedData, TaxResult


KEST_RATE = 0.275
KEST_RATE_BANK = 0.25
DBA_DIVIDEND_CAP = 0.15


class CapitalGainsProcessor:
    """Moving-average stock processor following Austrian average cost logic."""

    def __init__(
        self,
        fx_provider: ECBRateProvider,
        include_fees: bool = False,
        excluded_isins: set[str] | None = None,
    ) -> None:
        self.fx_provider = fx_provider
        self.include_fees = include_fees
        self.excluded_isins = {i.strip() for i in (excluded_isins or set()) if i}
        self.positions: dict[str, dict[str, float]] = {}

    def process(self, trades: pd.DataFrame) -> tuple[float, float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        gain_total = 0.0
        loss_total = 0.0
        if trades.empty:
            return gain_total, loss_total, pd.DataFrame(rows)

        for trade in trades.sort_values(["date", "datetime"]).to_dict("records"):
            qty = abs(float(trade["quantity"]))
            signed_qty = float(trade["quantity"])
            price = float(trade["tradePrice"])
            commission = abs(float(trade["ibCommission"]))
            currency = str(trade["currency"])
            trade_date = str(trade["date"])
            fx_amount, fx = self.fx_provider.convert(1.0, currency, trade_date, trade.get("fxRateToBase"))
            price_eur = price * fx_amount
            commission_eur = commission * fx_amount
            symbol = str(trade["symbol"])
            isin = str(trade.get("isin", "") or "")
            position = self.positions.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
            action = _trade_action(trade, signed_qty)
            realized = 0.0
            old_qty = position["qty"]
            old_avg = position["avg_cost"]
            is_altbestand = isin in self.excluded_isins

            if action == "BUY":
                old_total_cost = old_qty * old_avg
                fee_buy = commission_eur if self.include_fees else 0.0
                new_total_cost = old_total_cost + (qty * price_eur) + fee_buy
                position["qty"] = old_qty + qty
                position["avg_cost"] = new_total_cost / position["qty"] if position["qty"] else 0.0
            else:
                fee_sell = commission_eur if self.include_fees else 0.0
                sale_proceeds = (qty * price_eur) - fee_sell
                cost_basis = qty * old_avg
                realized = sale_proceeds - cost_basis
                if not is_altbestand:
                    if realized > 0:
                        gain_total += realized
                    elif realized < 0:
                        loss_total += realized
                position["qty"] = old_qty - qty
                if position["qty"] <= 0.0000001:
                    position["qty"] = 0.0
                    position["avg_cost"] = 0.0

            if is_altbestand:
                field = "PRE-2011 EXEMPT"
            elif realized > 0:
                field = "994"
            elif realized < 0:
                field = "892"
            else:
                field = ""

            rows.append(
                {
                    "date": trade_date,
                    "category": "STK",
                    "symbol": symbol,
                    "isin": isin,
                    "buy_sell": action,
                    "quantity": qty,
                    "price_original": price,
                    "currency": currency,
                    "ecb_rate": fx.eur_rate,
                    "fx_source": fx.source,
                    "price_eur": price_eur,
                    "commission_eur": commission_eur,
                    "old_quantity": old_qty,
                    "old_avg_cost_eur": old_avg,
                    "new_quantity": position["qty"],
                    "new_avg_cost_eur": position["avg_cost"],
                    "realized_pnl_eur": 0.0 if is_altbestand else realized,
                    "e1kv_field": field,
                }
            )

        return gain_total, loss_total, pd.DataFrame(rows)


class DerivativeProcessor:
    """Realized P&L processor for IBKR option and derivative trades.

    IBKR Flex does not distinguish securitised (warrants, certificates) from non-securitised
    (options, futures) derivatives. We default to non-securitised treatment: gains → KZ 981,
    losses → KZ 892. Securitised derivatives map to KZ 995/896 — currently out of scope.
    """

    def __init__(self, fx_provider: ECBRateProvider, include_fees: bool = False) -> None:
        self.fx_provider = fx_provider
        self.include_fees = include_fees

    def process(self, trades: pd.DataFrame) -> tuple[float, float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        gain_total = 0.0
        loss_total = 0.0
        if trades.empty:
            return gain_total, loss_total, pd.DataFrame(rows)

        for trade in trades.sort_values(["date", "datetime"]).to_dict("records"):
            currency = str(trade["currency"])
            trade_date = str(trade["date"])
            proceeds = float(trade["proceeds"])
            commission = float(trade["ibCommission"])
            fifo_pnl = float(trade["fifoPnlRealized"])
            open_close = str(trade.get("openCloseIndicator", "")).upper()
            category = str(trade.get("assetCategory", "OPT")).upper() or "OPT"
            if fifo_pnl != 0.0:
                pnl_original = fifo_pnl if self.include_fees else fifo_pnl - commission
            elif "C" in open_close:
                pnl_original = proceeds + commission if self.include_fees else proceeds
            else:
                pnl_original = 0.0
            pnl_eur, fx = self.fx_provider.convert(pnl_original, currency, trade_date, trade.get("fxRateToBase"))
            if pnl_eur > 0:
                gain_total += pnl_eur
                field = "981"
            elif pnl_eur < 0:
                loss_total += pnl_eur
                field = "892"
            else:
                field = ""
            rows.append(
                {
                    "date": trade_date,
                    "category": category,
                    "symbol": trade.get("symbol", ""),
                    "isin": trade.get("isin", ""),
                    "buy_sell": _trade_action(trade, float(trade["quantity"])),
                    "quantity": abs(float(trade["quantity"])),
                    "price_original": float(trade["tradePrice"]),
                    "currency": currency,
                    "ecb_rate": fx.eur_rate,
                    "fx_source": fx.source,
                    "price_eur": float(trade["tradePrice"]) * fx.eur_rate,
                    "commission_eur": abs(commission * fx.eur_rate),
                    "old_quantity": "",
                    "old_avg_cost_eur": "",
                    "new_quantity": "",
                    "new_avg_cost_eur": "",
                    "realized_pnl_eur": pnl_eur,
                    "e1kv_field": field,
                }
            )
        return gain_total, loss_total, pd.DataFrame(rows)


class TaxAggregator:
    def __init__(self, fx_provider: ECBRateProvider | None = None, include_fees: bool = False) -> None:
        self.fx_provider = fx_provider or ECBRateProvider()
        self.include_fees = include_fees

    def run(self, parsed: ParsedData, excluded_isins: set[str] | None = None) -> TaxResult:
        excluded = {i.strip() for i in (excluded_isins or set()) if i}

        stock_gain, stock_loss, stock_audit = CapitalGainsProcessor(
            self.fx_provider, self.include_fees, excluded
        ).process(parsed.stocks)
        deriv_gain, deriv_loss, option_audit = DerivativeProcessor(
            self.fx_provider, self.include_fees
        ).process(parsed.options)

        dividend_total, dividend_wht, dividend_audit = self._cash_income(
            parsed.dividends, "DIV", gross_field="863", tax_field="998"
        )
        bond_interest_total, bond_wht, bond_audit = self._cash_income(
            parsed.bond_interest, "BOND_INT", gross_field="863", tax_field="998"
        )
        bank_interest_total, bank_wht, bank_audit = self._cash_income(
            parsed.bank_interest, "BANK_INT", gross_field="861", tax_field="901"
        )

        # Foreign WHT credit cap. Dividends → 15% per DBA (Austria–USA Art. 10 etc.).
        # Bond interest typically 0–10% (US DBA: 0%); we conservatively cap aggregated
        # bond WHT at 15% of bond income too, and surface excess via excess_wht.
        gross_27_for_cap = max(0.0, dividend_total) + max(0.0, bond_interest_total)
        max_creditable_27 = gross_27_for_cap * DBA_DIVIDEND_CAP
        raw_wht_27 = abs(dividend_wht) + abs(bond_wht)
        creditable_wht_27 = min(raw_wht_27, max_creditable_27)
        excess_wht_above_cap = raw_wht_27 - creditable_wht_27

        creditable_wht_25 = abs(bank_wht)

        basket_27 = stock_gain + stock_loss + deriv_gain + deriv_loss + dividend_total + bond_interest_total
        basket_25 = bank_interest_total

        taxable_27 = max(0.0, basket_27)
        taxable_25 = max(0.0, basket_25)

        gross_tax_27 = taxable_27 * KEST_RATE
        gross_tax_25 = taxable_25 * KEST_RATE_BANK

        net_27 = max(0.0, gross_tax_27 - creditable_wht_27)
        net_25 = max(0.0, gross_tax_25 - creditable_wht_25)

        used_credit_27 = gross_tax_27 - net_27
        used_credit_25 = gross_tax_25 - net_25
        # Excess WHT: the part withheld abroad that Austria will not credit — either above
        # the DBA cap, or above the Austrian tax actually owed in that basket. Per §46 EStG
        # this cannot be carried forward; it can only be reclaimed from the source country.
        excess_wht = round(
            (creditable_wht_27 - used_credit_27)
            + (creditable_wht_25 - used_credit_25)
            + excess_wht_above_cap,
            2,
        )

        tax_due = round(net_27 + net_25, 2)
        foreign_tax_credit = round(used_credit_27 + used_credit_25, 2)

        audit = pd.concat(
            [stock_audit, option_audit, dividend_audit, bond_audit, bank_audit],
            ignore_index=True,
        )

        date_strs = audit["date"].dropna().astype(str) if not audit.empty else pd.Series(dtype=str)
        years = pd.to_numeric(date_strs.str[:4], errors="coerce").dropna()
        tax_year = int(years.max()) if not years.empty else None

        fields = {
            "994": round(stock_gain, 2),
            "892": round(abs(stock_loss + deriv_loss), 2),
            "981": round(deriv_gain, 2),
            "863": round(dividend_total + bond_interest_total, 2),
            "861": round(bank_interest_total, 2),
            "998": round(creditable_wht_27, 2),
            "901": round(creditable_wht_25, 2),
        }

        return TaxResult(
            e1kv_fields=fields,
            category_totals={
                "Stocks": round(stock_gain + stock_loss, 2),
                "Derivatives": round(deriv_gain + deriv_loss, 2),
                "Dividends": round(dividend_total, 2),
                "Bond Interest": round(bond_interest_total, 2),
                "Bank Interest": round(bank_interest_total, 2),
            },
            audit=audit,
            manual_processing=parsed.funds.copy(),
            tax_due=tax_due,
            foreign_tax_credit=foreign_tax_credit,
            taxable_27=round(taxable_27, 2),
            taxable_25=round(taxable_25, 2),
            stock_gain_total=round(stock_gain, 2),
            stock_loss_total=round(stock_loss, 2),
            deriv_gain_total=round(deriv_gain, 2),
            deriv_loss_total=round(deriv_loss, 2),
            dividend_total=round(dividend_total, 2),
            bond_interest_total=round(bond_interest_total, 2),
            bank_interest_total=round(bank_interest_total, 2),
            excess_wht=excess_wht,
            foreign_tax_credit_27=round(used_credit_27, 2),
            foreign_tax_credit_25=round(used_credit_25, 2),
            excluded_isins=sorted(excluded),
            tax_year=tax_year,
        )

    def _cash_income(
        self,
        cash: pd.DataFrame,
        category: str,
        gross_field: str,
        tax_field: str,
    ) -> tuple[float, float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        income_total = 0.0
        tax_total = 0.0
        if cash.empty:
            return income_total, tax_total, pd.DataFrame(rows)

        for item in cash.sort_values(["date", "datetime"]).to_dict("records"):
            amount = float(item["amount"])
            amount_eur, fx = self.fx_provider.convert(
                amount, str(item["currency"]), str(item["date"]), item.get("fxRateToBase")
            )
            is_tax = amount < 0 and "withholding" in f"{item.get('type', '')} {item.get('description', '')}".lower()
            if is_tax:
                tax_total += amount_eur
                pnl = 0.0
                field = tax_field
            else:
                income_total += amount_eur
                pnl = amount_eur
                field = gross_field
            rows.append(
                {
                    "date": item["date"],
                    "category": category,
                    "symbol": item.get("symbol", ""),
                    "isin": item.get("isin", ""),
                    "buy_sell": "CASH",
                    "quantity": "",
                    "price_original": amount,
                    "currency": item["currency"],
                    "ecb_rate": fx.eur_rate,
                    "fx_source": fx.source,
                    "price_eur": amount_eur,
                    "commission_eur": 0.0,
                    "old_quantity": "",
                    "old_avg_cost_eur": "",
                    "new_quantity": "",
                    "new_avg_cost_eur": "",
                    "realized_pnl_eur": pnl,
                    "e1kv_field": field,
                }
            )
        return income_total, tax_total, pd.DataFrame(rows)

    @staticmethod
    def export_reports(result: TaxResult, output_dir: str | Path = ".") -> dict[str, Path]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        e1kv = pd.DataFrame(
            [{"E1kv_Field": field, "Amount_EUR": amount} for field, amount in sorted(result.e1kv_fields.items())]
        )
        year_label = str(result.tax_year) if result.tax_year else "unknown"
        paths = {
            "e1kv": output / f"E1kv_Report_{year_label}.csv",
            "audit": output / "transaction_audit.csv",
            "manual": output / "manual_processing_required.csv",
        }
        e1kv.to_csv(paths["e1kv"], index=False)
        result.audit.to_csv(paths["audit"], index=False)
        result.manual_processing.to_csv(paths["manual"], index=False)
        return paths


def _trade_action(trade: dict | pd.Series, signed_qty: float) -> str:
    buy_sell = str(trade.get("buySell", "")).upper()
    if buy_sell in {"BUY", "SELL"}:
        return buy_sell
    return "BUY" if signed_qty > 0 else "SELL"
