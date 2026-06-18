"""JSON serialization for the engine's dataclasses + DataFrames.

This is the single place pandas leaves the building — the React frontend never sees a
DataFrame. No tax logic here: we only reshape what tax_engine already computed. The one
derived block is `performance`, a 1:1 port of app.py `_perf_data` so the browser receives
plain numbers and the engine stays the single source of P/L truth.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from models import ParsedData, TaxResult


def _clean(value: Any) -> Any:
    """One scalar → JSON-safe. NaN/NaT → None, numpy scalar → python, datetime → ISO date."""
    if value is None:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, (pd.Timestamp,)):
        return None if pd.isna(value) else value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    return value


def df_to_records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]


def df_columns(df: pd.DataFrame | None) -> list[str]:
    if df is None or df.empty:
        return []
    return [str(c) for c in df.columns]


def parsed_summary(parsed: ParsedData) -> dict[str, Any]:
    """Counts + Altbestand candidate ISINs — mirrors app.py `_altbestand_selector` dedup."""
    candidates: list[dict[str, str]] = []
    if not parsed.stocks.empty:
        pairs = (
            parsed.stocks[["symbol", "isin"]]
            .drop_duplicates()
            .sort_values("symbol")
            .to_dict("records")
        )
        for p in pairs:
            isin = str(p["isin"] or "").strip()
            if not isin:
                continue
            candidates.append({"label": f"{p['symbol']} — {isin}", "isin": isin})
    return {
        "counts": {
            "stocks": int(len(parsed.stocks)),
            "options": int(len(parsed.options)),
            "funds": int(len(parsed.funds)),
        },
        "altbestandCandidates": candidates,
    }


def _performance(result: TaxResult) -> dict[str, Any]:
    """1:1 port of app.py `_perf_data` — STK/OPT realized trades only, no PRE-2011 EXEMPT."""
    audit = result.audit
    if audit.empty:
        return {"trades": [], "monthly": [], "holdings": [], "summary": _perf_summary_empty()}

    audit = audit[
        audit["category"].isin(["STK", "OPT"])
        & (audit["e1kv_field"] != "PRE-2011 EXEMPT")
    ].copy()
    audit["_date"] = pd.to_datetime(audit["date"], format="%Y%m%d", errors="coerce")
    audit["realized_pnl_eur"] = pd.to_numeric(audit["realized_pnl_eur"], errors="coerce").fillna(0.0)
    audit["commission_eur"] = pd.to_numeric(audit["commission_eur"], errors="coerce").fillna(0.0)

    trades = audit[audit["realized_pnl_eur"] != 0].copy().sort_values("_date").reset_index(drop=True)
    if trades.empty:
        return {"trades": [], "monthly": [], "holdings": [], "summary": _perf_summary_empty()}

    trades["cumulative_pnl"] = trades["realized_pnl_eur"].cumsum()
    trades["month"] = trades["_date"].dt.to_period("M").astype(str)
    trades["date_iso"] = trades["_date"].dt.strftime("%Y-%m-%d")

    trade_rows = [
        {
            "date": r["date_iso"],
            "symbol": r["symbol"],
            "category": r["category"],
            "realized_pnl_eur": float(r["realized_pnl_eur"]),
            "commission_eur": float(r["commission_eur"]),
            "cumulative_pnl": float(r["cumulative_pnl"]),
        }
        for r in trades.to_dict("records")
    ]

    monthly_rows = []
    for month, grp in trades.groupby("month"):
        gains = float(grp.loc[grp["realized_pnl_eur"] > 0, "realized_pnl_eur"].sum())
        losses = float(grp.loc[grp["realized_pnl_eur"] < 0, "realized_pnl_eur"].sum())
        fees = float(grp["commission_eur"].sum())
        monthly_rows.append({
            "month": str(month),
            "gains": gains,
            "losses": abs(losses),
            "fees": fees,
            "est_tax": gains * 0.275,
        })

    holdings = (
        trades.groupby("symbol")
        .agg(
            total_pnl=("realized_pnl_eur", "sum"),
            total_fees=("commission_eur", "sum"),
            trade_count=("symbol", "count"),
        )
        .reset_index()
        .sort_values("total_pnl")
    )
    holding_rows = [
        {
            "symbol": r["symbol"],
            "total_pnl": float(r["total_pnl"]),
            "total_fees": float(r["total_fees"]),
            "trade_count": int(r["trade_count"]),
        }
        for r in holdings.to_dict("records")
    ]

    total_pnl = float(trades["realized_pnl_eur"].sum())
    total_fees = float(trades["commission_eur"].sum())
    gross_gains = float(trades.loc[trades["realized_pnl_eur"] > 0, "realized_pnl_eur"].sum())
    est_tax = gross_gains * 0.275
    effective_rate = (total_fees + est_tax) / gross_gains if gross_gains > 0 else 0.0

    return {
        "trades": trade_rows,
        "monthly": monthly_rows,
        "holdings": holding_rows,
        "summary": {
            "total_pnl": total_pnl,
            "total_fees": total_fees,
            "est_tax": est_tax,
            "effective_rate": effective_rate,
        },
    }


def _perf_summary_empty() -> dict[str, float]:
    return {"total_pnl": 0.0, "total_fees": 0.0, "est_tax": 0.0, "effective_rate": 0.0}


def result_to_json(result: TaxResult) -> dict[str, Any]:
    return {
        "e1kv_fields": {k: float(v) for k, v in result.e1kv_fields.items()},
        "category_totals": {k: float(v) for k, v in result.category_totals.items()},
        "audit": df_to_records(result.audit),
        "audit_columns": df_columns(result.audit),
        "manual_processing": df_to_records(result.manual_processing),
        "manual_columns": df_columns(result.manual_processing),
        "pil_payments": df_to_records(result.pil_payments),
        "pil_columns": df_columns(result.pil_payments),
        "corporate_actions": df_to_records(result.corporate_actions),
        "corporate_columns": df_columns(result.corporate_actions),
        "tax_timeline": df_to_records(result.tax_timeline),
        "tax_timeline_columns": df_columns(result.tax_timeline),
        "tax_due": float(result.tax_due),
        "foreign_tax_credit": float(result.foreign_tax_credit),
        "taxable_27": float(result.taxable_27),
        "taxable_25": float(result.taxable_25),
        "stock_gain_total": float(result.stock_gain_total),
        "stock_loss_total": float(result.stock_loss_total),
        "deriv_gain_total": float(result.deriv_gain_total),
        "deriv_loss_total": float(result.deriv_loss_total),
        "dividend_total": float(result.dividend_total),
        "bond_interest_total": float(result.bond_interest_total),
        "bank_interest_total": float(result.bank_interest_total),
        "excess_wht": float(result.excess_wht),
        "foreign_tax_credit_27": float(result.foreign_tax_credit_27),
        "foreign_tax_credit_25": float(result.foreign_tax_credit_25),
        "excluded_isins": list(result.excluded_isins),
        "tax_year": result.tax_year,
        "performance": _performance(result),
    }
