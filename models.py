"""Shared data contracts — canonical input/output types for all broker parsers and the tax engine."""

from __future__ import annotations

from dataclasses import dataclass, field

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
class ParsedData:
    """Broker-agnostic statement data after parsing. All broker parsers must produce this."""

    stocks: pd.DataFrame
    options: pd.DataFrame
    dividends: pd.DataFrame
    bond_interest: pd.DataFrame
    bank_interest: pd.DataFrame
    funds: pd.DataFrame
    cash_other: pd.DataFrame
    all_trades: pd.DataFrame
    all_cash: pd.DataFrame


@dataclass
class TaxResult:
    e1kv_fields: dict[str, float]
    category_totals: dict[str, float]
    audit: pd.DataFrame
    manual_processing: pd.DataFrame
    tax_due: float
    foreign_tax_credit: float
    taxable_27: float = 0.0
    taxable_25: float = 0.0
    stock_gain_total: float = 0.0
    stock_loss_total: float = 0.0
    deriv_gain_total: float = 0.0
    deriv_loss_total: float = 0.0
    dividend_total: float = 0.0
    bond_interest_total: float = 0.0
    bank_interest_total: float = 0.0
    excess_wht: float = 0.0
    foreign_tax_credit_27: float = 0.0
    foreign_tax_credit_25: float = 0.0
    excluded_isins: list[str] = field(default_factory=list)
    tax_year: int | None = None

    @property
    def taxable_base(self) -> float:
        return round(self.taxable_27 + self.taxable_25, 2)
