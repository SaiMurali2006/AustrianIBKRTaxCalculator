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
        include_fees = st.toggle(
            "Include fees in tax basis",
            value=False,
            help=(
                "OFF (default) — Austrian private account rules (§ 20 Abs. 2 EStG): "
                "brokerage commissions are non-deductible and excluded from taxable gain calculations. "
                "ON — fees are included in cost basis and proceeds (use for business accounts or non-Austrian jurisdictions). "
                "Either way, the fee amount is always visible in the Detailed Audit Trail."
            ),
        )

    xml_payload = uploaded.getvalue() if uploaded else (BROKER_SAMPLES[broker] if use_sample and sample_available else None)

    st.markdown(
        """
        <div class="tax-hero">
            <div class="eyebrow">Austria E1kv Digital Tax Report</div>
            <div class="title">Capital Gains Tax Dashboard</div>
            <div class="subtitle">Stocks, options, dividends and interest mapped into the Austrian E1kv form with EUR conversion, gain/loss separation, and the 25% / 27.5% basket split required by §27a EStG.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if use_sample and sample_available and not uploaded:
        st.info("Showing embedded sample data — upload your own statement to calculate real results.", icon="ℹ️")

    if not xml_payload:
        st.info("Upload a statement file or enable the embedded sample.")
        return

    parse_key = "parse_" + hashlib.md5(
        xml_payload if isinstance(xml_payload, bytes) else xml_payload.encode()
    ).hexdigest() + broker
    if parse_key not in st.session_state:
        with st.spinner("Parsing statement…"):
            st.session_state[parse_key] = get_parser(broker)(xml_payload)
    parsed = st.session_state[parse_key]

    with st.sidebar:
        excluded_isins = _altbestand_selector(parsed)
        export_clicked = st.button(
            "Generate CSV Exports",
            help="Saves E1kv_Report_<year>.csv, transaction_audit.csv, and manual_processing_required.csv to the current directory.",
        )

    calc_key = (
        parse_key
        + ("F" if include_fees else "N")
        + "|".join(sorted(excluded_isins))
    )
    if calc_key not in st.session_state:
        with st.spinner("Calculating KeSt…"):
            st.session_state[calc_key] = TaxAggregator(
                ECBRateProvider(), include_fees=include_fees
            ).run(parsed, excluded_isins=excluded_isins)
    result = st.session_state[calc_key]

    if export_clicked:
        paths = TaxAggregator.export_reports(result)
        st.success(f"CSV exports generated: {paths['e1kv'].name}, {paths['audit'].name}, {paths['manual'].name}")

    if view == "Executive Summary":
        render_summary(result, parsed, include_fees)
    elif view == "Performance":
        render_performance(result)
    else:
        render_audit(result)


def _altbestand_selector(parsed) -> set[str]:
    """Pre-2011 Altbestand exclusion — §124b Z 185 EStG.

    Lets the user mark specific (symbol, ISIN) combinations as grandfathered. The engine
    will skip realized P/L for those ISINs entirely. IBKR Flex statements do not carry
    acquisition dates for transferred positions, so this must be a manual selection.
    """
    if parsed.stocks.empty:
        return set()

    pairs = (
        parsed.stocks[["symbol", "isin"]]
        .drop_duplicates()
        .sort_values("symbol")
        .to_dict("records")
    )
    options_map = {f"{p['symbol']} — {p['isin'] or '(no ISIN)'}": str(p["isin"] or "") for p in pairs}
    options_map = {label: isin for label, isin in options_map.items() if isin}
    if not options_map:
        return set()
    selected = st.multiselect(
        "Pre-2011 Altbestand (exempt)",
        options=list(options_map.keys()),
        default=[],
        help=(
            "Securities acquired before 1 January 2011 (derivatives / interest-bearing "
            "instruments: 31 March 2012) are tax-free under § 124b Z 185 EStG. "
            "IBKR statements do not include the original acquisition date for transferred "
            "positions — pick the symbols you know are Altbestand. Their realized P/L is "
            "excluded from KeSt and tagged 'PRE-2011 EXEMPT' in the audit trail."
        ),
    )
    return {options_map[label] for label in selected}


def render_summary(result, parsed, include_fees: bool = False) -> None:
    fields = result.e1kv_fields
    field_cards = [
        (
            "blue", "Field 994", "Stock realized gains", fields["994"],
            "Realized gains from foreign stock/ETF/bond sales. Moving-average cost basis "
            "(Gleitender Durchschnittspreis). Report on E1kv row 994 (27.5% basket). ◦ Source: bmf.gv.at",
        ),
        (
            "purple", "Field 981", "Derivative gains", fields["981"],
            "Net gains on non-securitised derivatives (options, futures). "
            "Securitised derivatives (warrants, certificates) belong in KZ 995/896 — out of scope here. "
            "Report on E1kv row 981 (27.5% basket). ◦ Source: bmf.gv.at / EStG §27",
        ),
        (
            "red", "Field 892", "Realized losses", fields["892"],
            "Combined realized losses on foreign securities and non-securitised derivatives. "
            "Offset against gains within the 27.5% basket only — no carry-forward to next year (§27a EStG). "
            "Report on E1kv row 892. ◦ Source: bmf.gv.at",
        ),
        (
            "green", "Field 863", "Foreign dividends + bond int.", fields["863"],
            "Gross foreign dividends and bond-coupon interest before any tax deduction. "
            "Foreign withholding tax is tracked separately in Field 998. Report on E1kv row 863. ◦ Source: bmf.gv.at",
        ),
        (
            "gold", "Field 998", "Creditable WHT (27.5%)", fields["998"],
            "Foreign withholding tax credited against Austrian KeSt, capped at 15% of gross 27.5%-basket "
            "income per DBA treaty (e.g. Austria–USA Art. 10). Excess is shown in the warning below. "
            "Report on E1kv row 998. ◦ Source: bmf.gv.at / DBA treaties",
        ),
        (
            "red", "KeSt Due", "Net liability after credits", result.tax_due,
            "Final Austrian KeSt: 27.5% on the securities basket plus 25% on bank interest, "
            "minus the foreign tax credit. This is what you owe via FinanzOnline. ◦ Source: bmf.gv.at",
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

    if result.excess_wht > 0:
        st.warning(
            f"⚠ {_eur(result.excess_wht)} of foreign withholding tax exceeds the 15% DBA cap "
            f"or the Austrian tax actually owed. Austria cannot credit this excess (§46 EStG) — "
            f"reclaim it from the source country (e.g. file IRS Form 1040-NR for US withholding above 15%).",
            icon="⚠",
        )

    if result.excluded_isins:
        st.info(
            "Pre-2011 Altbestand excluded from KeSt calculation: "
            + ", ".join(result.excluded_isins),
            icon="🛡",
        )

    with st.expander("E1kv Field References"):
        st.markdown(
            "- [Official BMF E1kv 2024 form (PDF)](https://formulare.bmf.gv.at/service/formulare/inter-Steuern/pdfs/2024/E1kv.pdf)\n"
            "- [KeSt overview — bmf.gv.at](https://www.bmf.gv.at/themen/steuern/sparen-veranlagen/besteuerung-kapitalertraege-inland.html)\n"
            "- [EStG §27 / §27a legal text — ris.bka.gv.at](https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10004570)\n"
            "- [DBA treaty credits — bmf.gv.at](https://www.bmf.gv.at/themen/steuern/internationales-steuerrecht/doppelbesteuerung.html)\n"
        )

    fee_pill_label = "Fees: included in basis" if include_fees else "Fees: excluded (§20 Abs. 2 EStG)"
    fee_pill_tip = (
        "Brokerage commissions are included in the cost basis and proceeds (business-account mode)."
        if include_fees
        else "Brokerage commissions are excluded from taxable gain calculations per Austrian private account rules (§ 20 Abs. 2 EStG). "
             "Fee amounts remain visible in the Detailed Audit Trail."
    )
    st.markdown(
        f"""
        <div class="status-strip">
            <div class="status-pill"
                 title="Sum of taxable income in the 27.5% basket: stock gains + derivative gains + dividends + bond interest, minus losses. Floored at zero (no year-to-year carry-forward).">
                27.5% basket: {_eur(result.taxable_27)}
            </div>
            <div class="status-pill"
                 title="Sum of taxable income in the 25% basket: bank/savings deposit interest only. Cannot be offset against securities losses (§27a Abs. 2 EStG).">
                25% basket: {_eur(result.taxable_25)}
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
                 title="ETF and fund rows flagged for manual OeKB review. Austrian fund taxation (incl. ausschüttungsgleiche Erträge KZ 937) requires per-fund reporting and is not calculated automatically.">
                Manual fund rows: {len(parsed.funds)}
            </div>
            <div class="status-pill" title="{fee_pill_tip}">
                {fee_pill_label}
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
                ["994", "Aktien/ETF/Anleihen realisierte Gewinne (27,5%)", fields["994"]],
                ["892", "Realisierte Verluste (27,5%)",                    fields["892"]],
                ["981", "Derivate Gewinne (27,5%)",                        fields["981"]],
                ["863", "Auslandsdividenden + Anleihezinsen (27,5%)",      fields["863"]],
                ["861", "Auslaendische Sparbuchzinsen (25%)",              fields["861"]],
                ["998", "Anrechenbare ausl. Quellensteuer (27,5%)",        fields["998"]],
                ["901", "Anrechenbare ausl. Quellensteuer (25%)",          fields["901"]],
            ],
            columns=["E1kv Field", "Meaning", "Amount EUR"],
        )
        st.dataframe(mapping, use_container_width=True, hide_index=True)
    with col2:
        st.caption("CATEGORY P/L")
        category_df = pd.DataFrame(
            [{"Category": name, "EUR": round(value, 2)} for name, value in result.category_totals.items()]
        )
        st.bar_chart(category_df.set_index("Category"), color="#00D4FF", height=240)

    year_label = str(result.tax_year) if result.tax_year else "unknown"
    st.download_button(
        "Download E1kv CSV",
        _csv_bytes(mapping),
        f"E1kv_Report_{year_label}.csv",
        "text/csv",
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    gross_kest_27 = round(result.taxable_27 * 0.275, 2)
    gross_kest_25 = round(result.taxable_25 * 0.25, 2)
    with st.expander(f"KeSt Calculation Breakdown — Tax Year {year_label}"):
        st.markdown("**27.5% basket** — stocks, derivatives, dividends, bond interest")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Taxable", _eur(result.taxable_27),
                  help="Gains − losses in the securities basket, floored at zero.")
        c2.metric("Gross KeSt (×27.5%)", _eur(gross_kest_27))
        c3.metric("WHT credit used", f"−{_eur(result.foreign_tax_credit_27)}",
                  help="Foreign WHT credited against the 27.5% liability, capped at 15% of gross (DBA).")
        c4.metric("Net 27.5%", _eur(max(0.0, gross_kest_27 - result.foreign_tax_credit_27)))

        st.markdown("**25% basket** — bank/savings deposit interest")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Taxable", _eur(result.taxable_25),
                  help="Bank deposit interest only. Securities losses cannot offset this basket (§27a Abs. 2 EStG).")
        d2.metric("Gross KeSt (×25%)", _eur(gross_kest_25))
        d3.metric("WHT credit used", f"−{_eur(result.foreign_tax_credit_25)}")
        d4.metric("Net 25%", _eur(max(0.0, gross_kest_25 - result.foreign_tax_credit_25)))

        st.markdown("**Total**")
        t1, t2 = st.columns(2)
        t1.metric("Total KeSt Due", _eur(result.tax_due),
                  help="Sum of net 27.5% and net 25% liability — declare in FinanzOnline.")
        t2.metric("Non-creditable WHT", _eur(result.excess_wht),
                  help="Foreign WHT Austria will not credit (DBA cap or basket-exhausted). Reclaim from source country.")

        st.caption(
            "⚠ Securities acquired before 1 January 2011 (derivatives / interest-bearing instruments: 31 March 2012) "
            "are grandfathered under § 124b Z 185 EStG. Use the Pre-2011 Altbestand selector in the sidebar to "
            "exclude them. ETF/Fund rows (incl. ausschüttungsgleiche Erträge, KZ 937) are not auto-calculated — "
            "see the Manual ETF/Fund Queue below."
        )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if not result.manual_processing.empty:
        st.warning(
            "ETF/FUND rows detected — Austrian fund taxation (incl. ausschüttungsgleiche Erträge KZ 937, "
            "Meldefonds vs. Schwarze Fonds) requires per-fund OeKB review and is NOT included in the "
            "automatic KeSt calculation above."
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
    st.caption("Trade-level EUR conversion, ECB FX source, cost-basis evolution, and realized P/L per line. "
               "Each row shows its assigned E1kv Kennzahl.")
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
    st.caption("Rows flagged for manual OeKB review — Austrian fund taxation requires per-fund reporting. "
               "Accumulating ETFs generate ausschüttungsgleiche Erträge (KZ 937, 27.5%) annually.")
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
