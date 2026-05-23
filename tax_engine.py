"""Austrian KESt engine — broker-agnostic, operates on ParsedData."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from currency_provider import ECBRateProvider
from models import ParsedData, TaxResult


KEST_RATE = 0.275


class CapitalGainsProcessor:
    """Moving-average stock processor following Austrian average cost logic."""

    def __init__(self, fx_provider: ECBRateProvider) -> None:
        self.fx_provider = fx_provider
        self.positions: dict[str, dict[str, float]] = {}

    def process(self, trades: pd.DataFrame) -> tuple[float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        realized_total = 0.0
        if trades.empty:
            return realized_total, pd.DataFrame(rows)

        for _, trade in trades.sort_values(["date", "datetime"]).iterrows():
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
            position = self.positions.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
            action = _trade_action(trade, signed_qty)
            realized = 0.0
            old_qty = position["qty"]
            old_avg = position["avg_cost"]

            if action == "BUY":
                old_total_cost = old_qty * old_avg
                new_total_cost = old_total_cost + (qty * price_eur) + commission_eur
                position["qty"] = old_qty + qty
                position["avg_cost"] = new_total_cost / position["qty"] if position["qty"] else 0.0
            else:
                sale_proceeds = (qty * price_eur) - commission_eur
                cost_basis = qty * old_avg
                realized = sale_proceeds - cost_basis
                realized_total += realized
                position["qty"] = old_qty - qty
                if position["qty"] <= 0.0000001:
                    position["qty"] = 0.0
                    position["avg_cost"] = 0.0

            rows.append(
                {
                    "date": trade_date,
                    "category": "STK",
                    "symbol": symbol,
                    "isin": trade.get("isin", ""),
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
                    "realized_pnl_eur": realized,
                    "e1kv_field": "861" if realized else "",
                }
            )

        return realized_total, pd.DataFrame(rows)


class DerivativeProcessor:
    """Realized P&L processor for IBKR option and derivative trades."""

    def __init__(self, fx_provider: ECBRateProvider) -> None:
        self.fx_provider = fx_provider

    def process(self, trades: pd.DataFrame) -> tuple[float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        total = 0.0
        if trades.empty:
            return total, pd.DataFrame(rows)

        for _, trade in trades.sort_values(["date", "datetime"]).iterrows():
            currency = str(trade["currency"])
            trade_date = str(trade["date"])
            proceeds = float(trade["proceeds"])
            commission = float(trade["ibCommission"])
            pnl_original = float(trade["fifoPnlRealized"]) or proceeds + commission
            pnl_eur, fx = self.fx_provider.convert(pnl_original, currency, trade_date, trade.get("fxRateToBase"))
            total += pnl_eur
            rows.append(
                {
                    "date": trade_date,
                    "category": "OPT",
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
                    "e1kv_field": "775",
                }
            )
        return total, pd.DataFrame(rows)


class TaxAggregator:
    def __init__(self, fx_provider: ECBRateProvider | None = None) -> None:
        self.fx_provider = fx_provider or ECBRateProvider()

    def run(self, parsed: ParsedData) -> TaxResult:
        stock_total, stock_audit = CapitalGainsProcessor(self.fx_provider).process(parsed.stocks)
        option_total, option_audit = DerivativeProcessor(self.fx_provider).process(parsed.options)
        dividend_total, withholding_total, dividend_audit = self._cash_income(parsed.dividends, "DIV", "862")
        interest_total, interest_tax, interest_audit = self._cash_income(parsed.interest, "INT", "777")
        foreign_tax_credit = abs(withholding_total + interest_tax)

        basket_income = stock_total + option_total + dividend_total + interest_total
        taxable_base = max(0.0, basket_income)
        gross_tax = taxable_base * KEST_RATE
        tax_due = max(0.0, gross_tax - foreign_tax_credit)
        audit = pd.concat([stock_audit, option_audit, dividend_audit, interest_audit], ignore_index=True)

        fields = {
            "861": round(stock_total, 2),
            "775": round(option_total, 2),
            "862": round(dividend_total, 2),
            "777": round(interest_total, 2),
            "863": round(interest_total, 2),
            "998": round(foreign_tax_credit, 2),
        }

        return TaxResult(
            e1kv_fields=fields,
            category_totals={
                "Stocks": stock_total,
                "Derivatives": option_total,
                "Dividends": dividend_total,
                "Interest": interest_total,
            },
            audit=audit,
            manual_processing=parsed.funds.copy(),
            taxable_base=round(taxable_base, 2),
            tax_due=round(tax_due, 2),
            foreign_tax_credit=round(foreign_tax_credit, 2),
        )

    def _cash_income(self, cash: pd.DataFrame, category: str, field: str) -> tuple[float, float, pd.DataFrame]:
        rows: list[dict[str, object]] = []
        income_total = 0.0
        tax_total = 0.0
        if cash.empty:
            return income_total, tax_total, pd.DataFrame(rows)

        for _, item in cash.sort_values(["date", "datetime"]).iterrows():
            amount = float(item["amount"])
            amount_eur, fx = self.fx_provider.convert(amount, str(item["currency"]), str(item["date"]), item.get("fxRateToBase"))
            is_tax = amount < 0 and "withholding" in f"{item.get('type', '')} {item.get('description', '')}".lower()
            if is_tax:
                tax_total += amount_eur
                pnl = 0.0
            else:
                income_total += amount_eur
                pnl = amount_eur
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
                    "e1kv_field": "998" if is_tax else field,
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
        paths = {
            "e1kv": output / "E1kv_Report_2026.csv",
            "audit": output / "transaction_audit.csv",
            "manual": output / "manual_processing_required.csv",
        }
        e1kv.to_csv(paths["e1kv"], index=False)
        result.audit.to_csv(paths["audit"], index=False)
        result.manual_processing.to_csv(paths["manual"], index=False)
        return paths


def _trade_action(trade: pd.Series, signed_qty: float) -> str:
    buy_sell = str(trade.get("buySell", "")).upper()
    if buy_sell in {"BUY", "SELL"}:
        return buy_sell
    return "BUY" if signed_qty > 0 else "SELL"

