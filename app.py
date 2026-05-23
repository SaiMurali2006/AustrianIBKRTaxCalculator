from __future__ import annotations

import hashlib
from io import StringIO

import altair as alt
import pandas as pd
import streamlit as st

from currency_provider import ECBRateProvider
from parsers import BROKER_REGISTRY, BROKER_SAMPLES, get_parser
from styles import FINTECH_CSS
from tax_engine import TaxAggregator


_ALTAIR_THEME = {
    "config": {
        "background": "#0E1117",
        "view": {"stroke": "transparent"},
        "axis": {
            "labelColor": "#8B98A9", "titleColor": "#8B98A9",
            "gridColor": "rgba(255,255,255,0.07)",
            "domainColor": "rgba(255,255,255,0.12)",
            "tickColor": "rgba(255,255,255,0.12)",
        },
        "legend": {"labelColor": "#8B98A9", "titleColor": "#8B98A9"},
        "title": {"color": "#F4F7FB"},
    }
}
alt.themes.register("kest_dark", lambda: _ALTAIR_THEME)
alt.themes.enable("kest_dark")


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
        view = st.radio(
            "View",
            ["Executive Summary", "Detailed Audit Trail", "Performance"],
            label_visibility="collapsed",
        )
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

    # Content-hash keyed cache — avoids re-parsing on view switches; auto-invalidates on new file or broker change
    cache_key = hashlib.md5(xml_payload if isinstance(xml_payload, bytes) else xml_payload.encode()).hexdigest() + broker
    if cache_key not in st.session_state:
        with st.spinner("Parsing statement and calculating KeSt…"):
            parsed = get_parser(broker)(xml_payload)
            result = TaxAggregator(ECBRateProvider()).run(parsed)
            st.session_state[cache_key] = (parsed, result)

    parsed, result = st.session_state[cache_key]

    if export_clicked:
        TaxAggregator.export_reports(result)
        st.success("CSV exports generated: E1kv_Report_2026.csv, transaction_audit.csv, manual_processing_required.csv")

    if view == "Executive Summary":
        render_summary(result, parsed)
    elif view == "Performance":
        render_performance(result)
    else:
        render_audit(result)


def render_summary(result, parsed) -> None:
    # All six cards rendered in one HTML block so they actually live inside the CSS grid.
    field_cards = [
        (
            "blue", "Field 861", "Stocks realized gains", result.e1kv_fields["861"],
            "Realized gains from stock sales. Calculated using the Austrian moving-average cost method "
            "(Gleitender Durchschnittspreis). Each sale is matched against the running average purchase price. "
            "Report this amount on E1kv row 861. ◦ Source: bmf.gv.at",
        ),
        (
            "purple", "Field 775", "Derivatives / options", result.e1kv_fields["775"],
            "Net profit and loss from options, futures, warrants, and other derivative instruments. "
            "Gains and losses are recognized at close or expiry. Report on E1kv row 775. ◦ Source: bmf.gv.at / EStG §27",
        ),
        (
            "green", "Field 862", "Dividends", result.e1kv_fields["862"],
            "Gross dividend income received from domestic and foreign companies, before any tax deduction. "
            "Foreign withholding tax on dividends is tracked separately in Field 998. Report on E1kv row 862. ◦ Source: bmf.gv.at",
        ),
        (
            "green", "Field 777/863", "Foreign interest", result.e1kv_fields["777"],
            "Interest income from bonds, cash accounts, and similar instruments. "
            "Use row 777 for domestic Austrian sources and row 863 for foreign sources. ◦ Source: bmf.gv.at",
        ),
        (
            "gold", "Field 998", "Creditable withholding tax", result.e1kv_fields["998"],
            "Foreign withholding tax already deducted at source — for example, the US levies 15% on dividends paid to "
            "Austrian residents. This amount credits against your Austrian KeSt bill, reducing your final liability. "
            "Report on E1kv row 998. ◦ Source: bmf.gv.at / DBA treaties",
        ),
        (
            "red", "KeSt Due", "Net liability after credits", result.tax_due,
            "Your final Austrian capital income tax (KeSt) at 27.5%. Losses within the basket offset gains before the "
            "rate is applied, and foreign withholding taxes are then credited. This is the amount you owe to "
            "FinanzOnline after all offsets. ◦ Source: bmf.gv.at",
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

    with st.expander("E1kv Field References"):
        st.markdown(
            "- [KeSt overview — bmf.gv.at](https://www.bmf.gv.at/themen/steuern/kapitalvermoegenssteuern/kapitalertragsteuer.html)\n"
            "- [EStG §27 / §27a legal text — ris.bka.gv.at](https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10004570)\n"
            "- [DBA treaty credits — bmf.gv.at](https://www.bmf.gv.at/themen/steuern/internationales-steuerrecht/doppelbesteuerung.html)\n"
            "- [E1kv form and instructions — bmf.gv.at](https://www.bmf.gv.at/dam/jcr:e1kv-formular)\n"
        )

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


def render_performance(result) -> None:
    trades_df, monthly_df, holdings_df = _perf_data(result)

    if trades_df.empty:
        st.info("No realized trades yet — upload a statement with closed positions to see performance.")
        _footer()
        return

    total_pnl = float(trades_df["realized_pnl_eur"].sum())
    total_fees = float(trades_df["commission_eur"].sum())
    gross_gains = float(trades_df.loc[trades_df["realized_pnl_eur"] > 0, "realized_pnl_eur"].sum())
    est_tax = gross_gains * 0.275
    effective_rate = (total_fees + est_tax) / gross_gains if gross_gains > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Realized P/L", _eur(total_pnl), help="Sum of all closed trade P/L in EUR.")
    c2.metric("Total Fees Paid", _eur(total_fees), help="All brokerage commissions on closed trades.")
    c3.metric("Estimated KeSt", _eur(est_tax), help="Gross gains × 27.5% — does not account for loss offsets or credits.")
    c4.metric("Effective Rate", f"{effective_rate:.1%}", help="(Fees + estimated KeSt) ÷ gross gains — total drag on winning trades.")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Chart 1 — Cumulative P/L Timeline
    st.markdown('<p class="perf-section-label">CUMULATIVE REALIZED P/L</p>', unsafe_allow_html=True)

    area = (
        alt.Chart(trades_df)
        .mark_area(opacity=0.18, color="#00D4FF")
        .encode(
            x=alt.X("_date:T", title="Date", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("cumulative_pnl:Q", title="Cumulative P/L (EUR)"),
        )
    )
    line = (
        alt.Chart(trades_df)
        .mark_line(color="#00D4FF", strokeWidth=2)
        .encode(
            x=alt.X("_date:T"),
            y=alt.Y("cumulative_pnl:Q"),
        )
    )
    points = (
        alt.Chart(trades_df)
        .mark_point(size=60, filled=True)
        .encode(
            x=alt.X("_date:T"),
            y=alt.Y("cumulative_pnl:Q"),
            color=alt.condition(
                alt.datum.realized_pnl_eur > 0,
                alt.value("#00FF88"),
                alt.value("#FF4D6D"),
            ),
            tooltip=[
                alt.Tooltip("_date:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("symbol:N", title="Symbol"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("realized_pnl_eur:Q", title="P/L (EUR)", format=".2f"),
                alt.Tooltip("cumulative_pnl:Q", title="Cumulative (EUR)", format=".2f"),
            ],
        )
    )
    zero_df = pd.DataFrame({"y": [0.0]})
    zero_rule = (
        alt.Chart(zero_df)
        .mark_rule(color="rgba(255,255,255,0.18)", strokeDash=[4, 4])
        .encode(y="y:Q")
    )

    timeline = (area + line + zero_rule + points).properties(height=380).interactive()
    st.altair_chart(timeline, use_container_width=True)

    # Charts 2 & 3 — side by side
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="perf-section-label">MONTHLY BREAKDOWN</p>', unsafe_allow_html=True)
        if not monthly_df.empty:
            long_df = monthly_df.melt(
                id_vars="month",
                value_vars=["gains", "fees", "est_tax"],
                var_name="metric",
                value_name="amount",
            )
            color_scale = alt.Scale(
                domain=["gains", "fees", "est_tax"],
                range=["#00FF88", "#FFD700", "#FF4D6D"],
            )
            monthly_chart = (
                alt.Chart(long_df)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("month:O", title="Month"),
                    y=alt.Y("amount:Q", title="EUR"),
                    xOffset=alt.XOffset("metric:N"),
                    color=alt.Color("metric:N", scale=color_scale, title="Metric"),
                    tooltip=[
                        alt.Tooltip("month:O", title="Month"),
                        alt.Tooltip("metric:N", title="Metric"),
                        alt.Tooltip("amount:Q", title="EUR", format=".2f"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(monthly_chart, use_container_width=True)
        else:
            st.info("No monthly data available.")

    with col2:
        st.markdown('<p class="perf-section-label">TOP HOLDINGS BY P/L</p>', unsafe_allow_html=True)
        if not holdings_df.empty:
            holdings_chart = (
                alt.Chart(holdings_df)
                .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
                .encode(
                    x=alt.X("total_pnl:Q", title="Total P/L (EUR)"),
                    y=alt.Y("symbol:N", title=None, sort="-x"),
                    color=alt.condition(
                        alt.datum.total_pnl > 0,
                        alt.value("#00FF88"),
                        alt.value("#FF4D6D"),
                    ),
                    tooltip=[
                        alt.Tooltip("symbol:N", title="Symbol"),
                        alt.Tooltip("total_pnl:Q", title="Total P/L (EUR)", format=".2f"),
                        alt.Tooltip("total_fees:Q", title="Total Fees (EUR)", format=".2f"),
                        alt.Tooltip("trade_count:Q", title="Trades"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(holdings_chart, use_container_width=True)
        else:
            st.info("No holdings data available.")

    _footer()


def _perf_data(result) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = result.audit[result.audit["category"].isin(["STK", "OPT"])].copy()
    audit["_date"] = pd.to_datetime(audit["date"], format="%Y%m%d", errors="coerce")
    audit["realized_pnl_eur"] = pd.to_numeric(audit["realized_pnl_eur"], errors="coerce").fillna(0.0)
    audit["commission_eur"] = pd.to_numeric(audit["commission_eur"], errors="coerce").fillna(0.0)

    trades_df = audit[audit["realized_pnl_eur"] != 0].copy().sort_values("_date").reset_index(drop=True)
    if not trades_df.empty:
        trades_df["cumulative_pnl"] = trades_df["realized_pnl_eur"].cumsum()
        trades_df["month"] = trades_df["_date"].dt.to_period("M").astype(str)

    monthly_rows = []
    if not trades_df.empty:
        for month, grp in trades_df.groupby("month"):
            gains = float(grp.loc[grp["realized_pnl_eur"] > 0, "realized_pnl_eur"].sum())
            losses = float(grp.loc[grp["realized_pnl_eur"] < 0, "realized_pnl_eur"].sum())
            fees = float(grp["commission_eur"].sum())
            monthly_rows.append({
                "month": month,
                "gains": gains,
                "losses": abs(losses),
                "fees": fees,
                "est_tax": gains * 0.275,
            })
    monthly_df = pd.DataFrame(monthly_rows)

    holdings_df = pd.DataFrame()
    if not trades_df.empty:
        holdings_df = (
            trades_df.groupby("symbol")
            .agg(
                total_pnl=("realized_pnl_eur", "sum"),
                total_fees=("commission_eur", "sum"),
                trade_count=("symbol", "count"),
            )
            .reset_index()
            .sort_values("total_pnl")
        )

    return trades_df, monthly_df, holdings_df


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
