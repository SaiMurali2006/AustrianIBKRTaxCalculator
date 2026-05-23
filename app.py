from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from currency_provider import ECBRateProvider
from parsers import BROKER_REGISTRY, BROKER_SAMPLES, get_parser
from styles import FINTECH_CSS
from tax_engine import TaxAggregator


def main() -> None:
    st.set_page_config(
        page_title="Austrian KeSt Tax Engine",
        page_icon="EUR",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(FINTECH_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.title("KeSt Engine")
        broker = st.selectbox(
            "Broker",
            list(BROKER_REGISTRY),
            help="Select the format of your brokerage statement. Each broker uses a different export format.",
        )
        view = st.radio("View", ["Executive Summary", "Detailed Audit Trail"], label_visibility="collapsed")
        uploaded = st.file_uploader(
            f"Upload {broker} statement",
            type=["xml"],
            help="In IBKR: go to Reports → Flex Queries, create a query with Trades and Cash Transactions, then run and download as XML.",
        )
        sample_available = broker in BROKER_SAMPLES
        use_sample = st.toggle(
            "Use embedded sample",
            value=False,
            disabled=not sample_available,
            help="Load a built-in demonstration file to preview the dashboard without a real statement.",
        )
        export_clicked = st.button(
            "Generate CSV Exports",
            help="Saves E1kv_Report_2026.csv, transaction_audit.csv, and manual_processing_required.csv to the current directory.",
        )

    xml_payload = uploaded.getvalue() if uploaded else (BROKER_SAMPLES[broker] if use_sample and sample_available else None)

    st.markdown(
        """
        <div class="tax-hero">
            <div class="eyebrow">Austria E1kv Digital Tax Report</div>
            <div class="title">Capital Gains Tax Dashboard</div>
            <div class="subtitle">Stocks, options, dividends, interest and foreign withholding tax mapped into Austrian E1kv fields with EUR conversion and loss offsetting inside the 27.5% basket.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if use_sample and sample_available and not uploaded:
        st.info("Showing embedded sample data — upload your own statement to calculate real results.", icon="ℹ️")

    if not xml_payload:
        st.info("Upload a statement file or enable the embedded sample.")
        return

    with st.spinner("Parsing statement and calculating KeSt…"):
        parsed = get_parser(broker)(xml_payload)
        result = TaxAggregator(ECBRateProvider()).run(parsed)

    if export_clicked:
        TaxAggregator.export_reports(result)
        st.success("CSV exports generated: E1kv_Report_2026.csv, transaction_audit.csv, manual_processing_required.csv")

    if view == "Executive Summary":
        render_summary(result, parsed)
    else:
        render_audit(result)


def render_summary(result, parsed) -> None:
    # All six cards rendered in one HTML block so they actually live inside the CSS grid.
    field_cards = [
        (
            "blue", "Field 861", "Stocks realized gains", result.e1kv_fields["861"],
            "Realized gains from stock sales. Calculated using the Austrian moving-average cost method "
            "(Gleitender Durchschnittspreis). Each sale is matched against the running average purchase price. "
            "Report this amount on E1kv row 861.",
        ),
        (
            "purple", "Field 775", "Derivatives / options", result.e1kv_fields["775"],
            "Net profit and loss from options, futures, warrants, and other derivative instruments. "
            "Gains and losses are recognized at close or expiry. Report on E1kv row 775.",
        ),
        (
            "green", "Field 862", "Dividends", result.e1kv_fields["862"],
            "Gross dividend income received from domestic and foreign companies, before any tax deduction. "
            "Foreign withholding tax on dividends is tracked separately in Field 998. Report on E1kv row 862.",
        ),
        (
            "green", "Field 777/863", "Foreign interest", result.e1kv_fields["777"],
            "Interest income from bonds, cash accounts, and similar instruments. "
            "Use row 777 for domestic Austrian sources and row 863 for foreign sources.",
        ),
        (
            "gold", "Field 998", "Creditable withholding tax", result.e1kv_fields["998"],
            "Foreign withholding tax already deducted at source — for example, the US levies 15% on dividends paid to "
            "Austrian residents. This amount credits against your Austrian KeSt bill, reducing your final liability. "
            "Report on E1kv row 998.",
        ),
        (
            "red", "KeSt Due", "Net liability after credits", result.tax_due,
            "Your final Austrian capital income tax (KeSt) at 27.5%. Losses within the basket offset gains before the "
            "rate is applied, and foreign withholding taxes are then credited. This is the amount you owe to "
            "FinanzOnline after all offsets.",
        ),
    ]

    cards_html = '<div class="metric-grid">'
    for color, field, label, value, tip in field_cards:
        cards_html += f"""
        <div class="card-wrap" data-tip="{tip}">
            <div class="tax-card {color}">
                <div class="field">{field}</div>
                <div class="value">{_eur(value)}</div>
                <div class="label">{label}</div>
            </div>
        </div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="status-strip">
            <div class="status-pill"
                 title="Sum of all income in the Austrian 27.5% KeSt basket: stock gains + derivatives + dividends + interest. Losses within the basket offset gains before tax is applied.">
                Taxable basket: {_eur(result.taxable_base)}
            </div>
            <div class="status-pill"
                 title="Number of stock (STK) trade rows parsed from your statement.">
                Stock trades: {len(parsed.stocks)}
            </div>
            <div class="status-pill"
                 title="Number of option, future, and other derivative trade rows parsed.">
                Option trades: {len(parsed.options)}
            </div>
            <div class="status-pill"
                 title="ETF and fund rows flagged for manual OeKB review. Austrian fund taxation requires per-fund reporting and is not calculated automatically.">
                Manual fund rows: {len(parsed.funds)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.caption("E1KV FIELD MAPPING")
        mapping = pd.DataFrame(
            [
                ["861", "Aktien realisierte Einkuenfte",                result.e1kv_fields["861"]],
                ["775", "Derivate und Optionen",                        result.e1kv_fields["775"]],
                ["862", "Dividenden",                                   result.e1kv_fields["862"]],
                ["777/863", "Auslaendische Zinsen",                     result.e1kv_fields["777"]],
                ["998", "Anrechenbare ausl. Quellensteuer",             result.e1kv_fields["998"]],
            ],
            columns=["E1kv Field", "Meaning", "Amount EUR"],
        )
        st.dataframe(mapping, use_container_width=True, hide_index=True)
    with col2:
        st.caption("CATEGORY P/L")
        category_df = pd.DataFrame(
            [{"Category": name, "EUR": round(value, 2)} for name, value in result.category_totals.items()]
        )
        st.bar_chart(category_df.set_index("Category"), color="#00D4FF", height=220)

    st.download_button("Download E1kv CSV", _csv_bytes(mapping), "E1kv_Report_2026.csv", "text/csv")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    gross_kest = round(result.taxable_base * 0.275, 2)
    with st.expander("KeSt Calculation Breakdown"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Taxable Basket",
            _eur(result.taxable_base),
            help="Sum of stock gains, derivative P/L, dividends, and interest. Losses within the basket offset gains before any tax is applied.",
        )
        c2.metric(
            "Gross KeSt (×27.5%)",
            _eur(gross_kest),
            help="27.5% applied to the full taxable basket, before deducting any foreign tax credits.",
        )
        c3.metric(
            "Foreign Tax Credit",
            f"−{_eur(result.foreign_tax_credit)}",
            help="Withholding taxes already paid abroad (e.g. 15% US dividend withholding). Credited against your Austrian KeSt — enter on E1kv row 998.",
        )
        c4.metric(
            "Net KeSt Due",
            _eur(result.tax_due),
            help="Your final Austrian KeSt liability: Gross KeSt minus the foreign tax credit. This is the amount to declare in FinanzOnline.",
        )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if not result.manual_processing.empty:
        st.warning(
            "ETF/FUND rows detected — these require separate Austrian fund taxation review (OeKB reporting) "
            "and are not included in the automatic KeSt calculation above."
        )
        st.dataframe(result.manual_processing, use_container_width=True)

    _footer()


def render_audit(result) -> None:
    st.subheader("Detailed Audit Trail")
    st.caption("Trade-level EUR conversion, ECB FX source, cost-basis evolution, and realized P/L per line.")
    if result.audit.empty:
        st.info("No taxable trade or cash income rows found in the uploaded statement.")
    else:
        st.dataframe(result.audit, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Transaction Audit CSV",
            result.audit.to_csv(index=False).encode("utf-8"),
            "transaction_audit.csv",
            "text/csv",
        )

    st.subheader("Manual ETF/Fund Queue")
    st.caption("Rows flagged for manual OeKB review — Austrian fund taxation requires per-fund reporting.")
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

    _footer()


def _footer() -> None:
    st.markdown(
        '<div class="kest-footer">Austrian KeSt Engine — calculation aid only, not tax advice. '
        "Consult a qualified Austrian tax professional before filing.</div>",
        unsafe_allow_html=True,
    )


def _eur(value: float) -> str:
    return f"EUR {value:,.2f}"


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


if __name__ == "__main__":
    main()
