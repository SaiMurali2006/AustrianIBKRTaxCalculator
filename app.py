from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from currency_provider import ECBRateProvider
from parser import parse_flex_xml
from styles import FINTECH_CSS
from tax_engine import TaxAggregator


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


def main() -> None:
    st.set_page_config(
        page_title="Austrian IBKR Tax Engine",
        page_icon="EUR",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(FINTECH_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.title("IBKR KESt Engine")
        view = st.radio("View", ["Executive Summary", "Detailed Audit Trail"], label_visibility="collapsed")
        uploaded = st.file_uploader("Upload IBKR Flex XML", type=["xml"])
        use_sample = st.toggle("Use embedded sample", value=uploaded is None)
        export_clicked = st.button("Generate CSV Exports")

    xml_payload = uploaded.getvalue() if uploaded else SAMPLE_XML if use_sample else None
    st.markdown(
        """
        <div class="tax-hero">
            <div class="eyebrow">Austria E1kv Digital Tax Report</div>
            <div class="title">IBKR Capital Gains Tax Dashboard</div>
            <div class="subtitle">Stocks, options, dividends, interest and foreign withholding tax mapped into Austrian E1kv fields with EUR conversion and loss offsetting inside the 27.5% basket.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not xml_payload:
        st.info("Upload a Flex Query XML or enable the embedded sample.")
        return

    parsed = parse_flex_xml(xml_payload)
    result = TaxAggregator(ECBRateProvider()).run(parsed)

    if export_clicked:
        paths = TaxAggregator.export_reports(result)
        st.success("CSV exports generated: E1kv_Report_2026.csv, transaction_audit.csv, manual_processing_required.csv")

    if view == "Executive Summary":
        render_summary(result, parsed)
    else:
        render_audit(result)


def render_summary(result, parsed) -> None:
    field_cards = [
        ("blue", "Field 861", "Stocks realized gains", result.e1kv_fields["861"]),
        ("purple", "Field 775", "Derivatives / options", result.e1kv_fields["775"]),
        ("green", "Field 862", "Dividends", result.e1kv_fields["862"]),
        ("green", "Field 777/863", "Foreign interest", result.e1kv_fields["777"]),
        ("gold", "Field 998", "Creditable foreign withholding tax", result.e1kv_fields["998"]),
        ("red", "KESt Due", "After 27.5% basket offset and credits", result.tax_due),
    ]
    st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
    for color, field, label, value in field_cards:
        st.markdown(
            f"""
            <div class="tax-card {color}">
                <div class="field">{field}</div>
                <div class="value">{_eur(value)}</div>
                <div class="label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="status-strip">
            <div class="status-pill">Taxable 27.5% basket: {_eur(result.taxable_base)}</div>
            <div class="status-pill">Stock trades: {len(parsed.stocks)}</div>
            <div class="status-pill">Option trades: {len(parsed.options)}</div>
            <div class="status-pill">Manual ETF/Fund rows: {len(parsed.funds)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1.1, 0.9])
    with col1:
        st.subheader("E1kv Field Mapping")
        mapping = pd.DataFrame(
            [
                ["861", "Aktien realisierte Einkuenfte", result.e1kv_fields["861"]],
                ["775", "Derivate und Optionen", result.e1kv_fields["775"]],
                ["862", "Dividenden", result.e1kv_fields["862"]],
                ["777/863", "Auslaendische Zinsen", result.e1kv_fields["777"]],
                ["998", "Anrechenbare auslaendische Quellensteuer", result.e1kv_fields["998"]],
            ],
            columns=["E1kv Field", "Meaning", "Amount EUR"],
        )
        st.dataframe(mapping, use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Category P/L")
        category_df = pd.DataFrame(
            [{"Category": name, "EUR": round(value, 2)} for name, value in result.category_totals.items()]
        )
        st.bar_chart(category_df.set_index("Category"), color="#00D4FF")

    st.download_button("Download E1kv CSV", _csv_bytes(mapping), "E1kv_Report_2026.csv", "text/csv")

    if not result.manual_processing.empty:
        st.warning("ETF/FUND rows detected. Austrian fund taxation can require OeKB reporting and manual processing.")
        st.dataframe(result.manual_processing, use_container_width=True)


def render_audit(result) -> None:
    st.subheader("Detailed Audit Trail")
    st.caption("Shows trade dates, EUR conversion rates, cost-basis evolution, and realized P/L per line.")
    if result.audit.empty:
        st.info("No taxable trade or cash income rows found in the uploaded XML.")
    else:
        st.dataframe(result.audit, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Transaction Audit CSV",
            result.audit.to_csv(index=False).encode("utf-8"),
            "transaction_audit.csv",
            "text/csv",
        )

    st.subheader("Manual ETF/Fund Queue")
    if result.manual_processing.empty:
        st.success("No FUND rows detected.")
    else:
        st.dataframe(result.manual_processing, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Manual Processing CSV",
            result.manual_processing.to_csv(index=False).encode("utf-8"),
            "manual_processing_required.csv",
            "text/csv",
        )


def _eur(value: float) -> str:
    return f"EUR {value:,.2f}"


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


if __name__ == "__main__":
    main()

