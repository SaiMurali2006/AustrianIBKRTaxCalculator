"""Shared data contracts — canonical input/output types for all broker parsers and the tax engine."""

from __future__ import annotations

from dataclasses import dataclass

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
    interest: pd.DataFrame
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
    taxable_base: float
    tax_due: float
    foreign_tax_credit: float
