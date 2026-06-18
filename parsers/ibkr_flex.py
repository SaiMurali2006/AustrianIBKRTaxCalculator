"""IBKR Flex XML parser — produces the canonical ParsedData contract."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import pandas as pd

from models import CASH_COLUMNS, TRADE_COLUMNS, ParsedData


SAMPLE_XML = """<FlexQueryResponse>
    <FlexStatements>
        <FlexStatement>
            <Trades>
                <Trade currency="USD" fxRateToBase="0.84775" assetCategory="STK" symbol="AAPL" description="APPLE INC" isin="US0378331005" dateTime="20260414;145843" settleDateTarget="20260415" quantity="54" tradePrice="257.97" proceeds="-13930.38" ibCommission="-1" openCloseIndicator="O" cost="13931.38" fifoPnlRealized="0" buySell="BUY"/>
            </Trades>
            <CashTransactions>
                <CashTransaction currency="EUR" fxRateToBase="1" symbol="" description="CASH RECEIPTS / ELECTRONIC FUND TRANSFERS" securityID="" isin="" dateTime="20260412" settleDate="20260412" amount="1000" type="Deposits/Withdrawals"/>
            </CashTransactions>
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>"""


CORPORATE_ACTION_COLUMNS = [
    "date",
    "datetime",
    "type",
    "symbol",
    "isin",
    "description",
    "quantity",
    "proceeds",
    "currency",
]


def parse(source: str | Path | bytes) -> ParsedData:
    root = _load_xml(source)
    trades = [_normalise_trade(node.attrib) for node in root.findall(".//Trade")]
    cash = [_normalise_cash(node.attrib) for node in root.findall(".//CashTransaction")]
    corp_actions = [_normalise_corp_action(node.attrib) for node in root.findall(".//CorporateAction")]

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    cash_df = pd.DataFrame(cash, columns=CASH_COLUMNS)
    corp_actions_df = pd.DataFrame(corp_actions, columns=CORPORATE_ACTION_COLUMNS)

    if not trades_df.empty:
        trades_df["assetCategory"] = trades_df["assetCategory"].str.upper()

    if not cash_df.empty:
        cash_df["type"] = cash_df["type"].fillna("")
        cash_df["description"] = cash_df["description"].fillna("")

    # Non-securitised derivatives (OPT, FOP) → KZ 857 in the tax engine.
    # Securitised derivatives (WAR, IOPT — warrants, certificates) belong in KZ 995/896
    # which we do not auto-calculate; route them to the manual queue instead of silently
    # filing them as non-securitised.
    _known = {"STK", "OPT", "FOP", "WAR", "IOPT", "FUND"}
    stocks = trades_df[trades_df["assetCategory"].eq("STK")].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)
    options = (
        trades_df[trades_df["assetCategory"].isin(["OPT", "FOP"])].copy()
        if not trades_df.empty
        else _empty(TRADE_COLUMNS)
    )
    _securitised_deriv = (
        trades_df[trades_df["assetCategory"].isin(["WAR", "IOPT"])].copy()
        if not trades_df.empty
        else _empty(TRADE_COLUMNS)
    )
    # Unknown categories (FUT, BOND, CASH/FX, etc.) are routed to the manual review queue
    # so they are never silently excluded from the user's attention.
    _fund_rows = trades_df[trades_df["assetCategory"].eq("FUND")].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)
    _unknown_rows = trades_df[~trades_df["assetCategory"].isin(_known)].copy() if not trades_df.empty else _empty(TRADE_COLUMNS)
    funds = pd.concat([_fund_rows, _securitised_deriv, _unknown_rows], ignore_index=True)

    # PIL (Payment in Lieu) is a securities-lending substitute, NOT a §27 Abs 2 dividend.
    # Per EStR Rz 6228 it is a Surrogat — must NOT land in KZ 863 (Auslandsdividenden).
    # Route PIL rows to a separate manual-review bucket; the user reports them at the
    # progressive rate (or as the tax advisor instructs), not via the KESt 27.5% pipeline.
    pil_payments = _cash_filter_pil(cash_df)
    pil_index = pil_payments.index if not pil_payments.empty else pd.Index([])
    # True dividend rows: dividend / withholding keywords minus the PIL rows.
    dividends_raw = _cash_filter(cash_df, ["dividend", "withholding"])
    dividends = (
        dividends_raw.drop(index=pil_index, errors="ignore").copy()
        if not dividends_raw.empty
        else _empty(CASH_COLUMNS)
    )
    # Bank deposit interest (25% basket, KZ 861) vs bond coupon interest (27.5% basket, KZ 863).
    # Prefer the IBKR `type` attribute — it is authoritative. Fall back to description match
    # for older Flex exports that left `type` blank.
    #   Bank-deposit types: "Broker Interest Received/Paid", "Deposit Interest", "Credit Interest"
    #   Bond-coupon types: "Bond Interest Received/Paid", "Bond Coupon Payment"
    bank_interest = _interest_by_type(
        cash_df,
        types={"broker interest received", "broker interest paid", "deposit interest", "credit interest", "debit interest"},
        desc_keywords=["credit interest", "debit interest", "broker interest", "deposit interest", "interest on cash"],
    )
    bond_interest = _interest_by_type(
        cash_df,
        types={"bond interest received", "bond interest paid", "bond coupon payment", "bond coupon"},
        desc_keywords=["bond interest", "bond coupon", "coupon payment", "accrued interest"],
    )
    # Anything still labelled "interest" that the above did not catch: default to bond-coupon
    # bucket (27.5%) — safer than dumping into bank (25%) since bank rules forbid offset.
    interest_all = _cash_filter(cash_df, ["interest"])
    leftover_interest = (
        interest_all.drop(index=bank_interest.index.union(bond_interest.index), errors="ignore").copy()
        if not interest_all.empty
        else _empty(CASH_COLUMNS)
    )
    bond_interest = pd.concat([bond_interest, leftover_interest], ignore_index=False)
    consumed = (
        dividends.index
        .union(interest_all.index)
        .union(bank_interest.index)
        .union(bond_interest.index)
        .union(pil_index)
    )
    cash_other = (
        cash_df.drop(index=consumed, errors="ignore").copy()
        if not cash_df.empty
        else _empty(CASH_COLUMNS)
    )

    return ParsedData(
        stocks=stocks.reset_index(drop=True),
        options=options.reset_index(drop=True),
        dividends=dividends.reset_index(drop=True),
        bond_interest=bond_interest.reset_index(drop=True),
        bank_interest=bank_interest.reset_index(drop=True),
        funds=funds.reset_index(drop=True),
        cash_other=cash_other.reset_index(drop=True),
        all_trades=trades_df.reset_index(drop=True),
        all_cash=cash_df.reset_index(drop=True),
        corporate_actions=corp_actions_df.reset_index(drop=True),
        pil_payments=pil_payments.reset_index(drop=True),
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


def _normalise_corp_action(attrs: dict[str, str]) -> dict[str, object]:
    date_time = attrs.get("dateTime", attrs.get("reportDate", ""))
    return {
        "date": date_time.split(";")[0],
        "datetime": date_time,
        "type": attrs.get("type", ""),
        "symbol": attrs.get("symbol", ""),
        "isin": attrs.get("isin", ""),
        "description": attrs.get("description", attrs.get("actionDescription", "")),
        "quantity": _num(attrs.get("quantity")),
        "proceeds": _num(attrs.get("proceeds")),
        "currency": attrs.get("currency", "EUR"),
    }


def _cash_filter_pil(df: pd.DataFrame) -> pd.DataFrame:
    """Payment in Lieu of dividend — securities-lending substitute. Not §27 Abs 2 dividend."""
    if df.empty:
        return _empty(CASH_COLUMNS)
    type_lower = df["type"].fillna("").str.strip().str.lower()
    desc_lower = df["description"].fillna("").str.lower()
    haystack = type_lower + " " + desc_lower
    return df[haystack.str.contains("payment in lieu|pil ", regex=True, na=False)].copy()


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


def _interest_by_type(
    df: pd.DataFrame,
    types: set[str],
    desc_keywords: list[str],
) -> pd.DataFrame:
    if df.empty:
        return _empty(CASH_COLUMNS)
    type_lower = df["type"].fillna("").str.strip().str.lower()
    desc_lower = df["description"].fillna("").str.lower()
    by_type = type_lower.isin(types)
    # description fallback only when type is blank
    desc_pattern = "|".join(desc_keywords) if desc_keywords else ""
    by_desc = type_lower.eq("") & desc_lower.str.contains(desc_pattern, regex=True) if desc_pattern else False
    return df[by_type | by_desc].copy()


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
