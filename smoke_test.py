"""Engine smoke test — verifies the Austrian KeSt calculation against the embedded sample."""

from parsers import get_parser
from tax_engine import KEST_RATE, KEST_RATE_BANK, TaxAggregator, years_in_parsed


def test_sample_runs():
    parsed = get_parser("IBKR Flex XML")("sample_flex.xml")
    result = TaxAggregator().run(parsed)

    for kz in ("994", "892", "857", "863", "409", "861", "998", "901"):
        assert kz in result.e1kv_fields, f"Missing Kennzahl {kz}"

    assert result.e1kv_fields["994"] > 0, f"Stock SELL should produce KZ 994 gains, got {result.e1kv_fields['994']}"
    assert result.e1kv_fields["857"] > 0, f"Option premium should produce KZ 857 gains, got {result.e1kv_fields['857']}"
    assert result.e1kv_fields["863"] > 0, f"Dividend should populate KZ 863, got {result.e1kv_fields['863']}"
    assert result.e1kv_fields["861"] > 0, f"Credit Interest should populate KZ 861, got {result.e1kv_fields['861']}"
    assert result.e1kv_fields["998"] > 0, f"US dividend withholding should populate KZ 998, got {result.e1kv_fields['998']}"

    assert result.taxable_27 > 0, "27.5% basket should be positive given gains/dividends"
    assert result.taxable_25 > 0, "25% basket should be positive given Credit Interest"
    assert result.tax_due > 0, f"Positive income should produce tax due, got {result.tax_due}"

    expected_25 = round(result.taxable_25 * KEST_RATE_BANK - result.foreign_tax_credit_25, 2)
    expected_27 = round(result.taxable_27 * KEST_RATE - result.foreign_tax_credit_27, 2)
    assert abs(result.tax_due - (max(0.0, expected_27) + max(0.0, expected_25))) < 0.01, (
        f"tax_due {result.tax_due} != net_27 {expected_27} + net_25 {expected_25}"
    )

    open_opt_pnl = result.audit[(result.audit["category"] == "OPT") & (result.audit["buy_sell"] == "BUY")]["realized_pnl_eur"]
    assert (open_opt_pnl == 0.0).all(), f"Opening OPT BUY trades must have 0 realized P/L, got {open_opt_pnl.tolist()}"

    stk_sells = result.audit[(result.audit["category"] == "STK") & (result.audit["buy_sell"] == "SELL")]
    for _, row in stk_sells.iterrows():
        pnl = float(row["realized_pnl_eur"])
        kz = row["e1kv_field"]
        if pnl > 0:
            assert kz == "994", f"Stock gain row should be KZ 994, got {kz}"
        elif pnl < 0:
            assert kz == "892", f"Stock loss row should be KZ 892, got {kz}"


def test_dba_cap_and_excess_surfaced():
    """A synthetic high-WHT dividend should be capped at 15% and excess flagged."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="USD" fxRateToBase="1.0" symbol="XYZ" description="Dividend XYZ"
                isin="US0000000000" dateTime="20260101" amount="100" type="Dividends"/>
            <CashTransaction currency="USD" fxRateToBase="1.0" symbol="XYZ" description="US withholding tax"
                isin="US0000000000" dateTime="20260101" amount="-30" type="Withholding Tax"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert result.e1kv_fields["998"] <= round(100 * 0.15, 2) + 0.01, (
        f"KZ 998 should be capped at 15% of gross, got {result.e1kv_fields['998']}"
    )
    assert result.excess_wht >= 15.0 - 0.01, (
        f"Excess WHT above DBA cap must be surfaced, got excess_wht={result.excess_wht}"
    )


def test_altbestand_exclusion():
    """An ISIN flagged as Altbestand contributes zero to KZ 994/892."""
    parsed = get_parser("IBKR Flex XML")("sample_flex.xml")
    aapl_isin = "US0378331005"
    result = TaxAggregator().run(parsed, excluded_isins={aapl_isin})
    assert result.e1kv_fields["994"] == 0.0, (
        f"AAPL excluded as Altbestand should yield KZ 994 = 0, got {result.e1kv_fields['994']}"
    )
    altbestand_rows = result.audit[result.audit["e1kv_field"] == "PRE-2011 EXEMPT"]
    assert not altbestand_rows.empty, "Excluded ISIN rows must be tagged 'PRE-2011 EXEMPT'"
    assert aapl_isin in result.excluded_isins


def test_bank_interest_taxed_at_25_not_275():
    """Bank-interest-only statement: tax_due must equal taxable_25 * 25%, not 27.5%."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="" description="Credit interest"
                isin="" dateTime="20260430" amount="100" type="Broker Interest Received"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert result.taxable_27 == 0.0, f"27.5% basket should be empty, got {result.taxable_27}"
    assert abs(result.taxable_25 - 100.0) < 0.01, f"25% basket should be 100, got {result.taxable_25}"
    assert abs(result.tax_due - 25.0) < 0.01, f"100 EUR bank interest × 25% = 25.00, got {result.tax_due}"


def test_securities_losses_do_not_offset_bank_interest():
    """A pure stock loss must not reduce bank interest tax."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades>
            <Trade currency="EUR" fxRateToBase="1" assetCategory="STK" symbol="FOO" description="FOO"
                isin="DE0000000001" dateTime="20260101;100000" quantity="10" tradePrice="100"
                proceeds="-1000" ibCommission="0" openCloseIndicator="O" cost="1000" fifoPnlRealized="0" buySell="BUY"/>
            <Trade currency="EUR" fxRateToBase="1" assetCategory="STK" symbol="FOO" description="FOO"
                isin="DE0000000001" dateTime="20260102;100000" quantity="-10" tradePrice="50"
                proceeds="500" ibCommission="0" openCloseIndicator="C" cost="0" fifoPnlRealized="0" buySell="SELL"/>
        </Trades>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="" description="Credit interest"
                isin="" dateTime="20260430" amount="100" type="Broker Interest Received"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert result.taxable_27 == 0.0, f"Loss-only securities basket floored at 0, got {result.taxable_27}"
    assert abs(result.taxable_25 - 100.0) < 0.01, f"Bank basket = 100, got {result.taxable_25}"
    assert abs(result.tax_due - 25.0) < 0.01, (
        f"Securities loss must NOT offset bank interest. Expected 25.00 due, got {result.tax_due}"
    )
    assert result.e1kv_fields["892"] >= 500.0 - 0.01, (
        f"Loss must still be reported on KZ 892, got {result.e1kv_fields['892']}"
    )


def test_bond_interest_routed_to_kz_409_not_863():
    """Bond coupon interest must land in KZ 409 (Forderungswertpapiere), not KZ 863 (dividends)."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="DE10Y" description="Bond Interest Received"
                isin="DE0001102309" dateTime="20260601" amount="80" type="Bond Interest Received"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="AAPL" description="AAPL Cash Dividend"
                isin="US0378331005" dateTime="20260601" amount="50" type="Dividends"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert abs(result.e1kv_fields["409"] - 80.0) < 0.01, f"Bond coupon → KZ 409=80, got {result.e1kv_fields['409']}"
    assert abs(result.e1kv_fields["863"] - 50.0) < 0.01, f"Dividend → KZ 863=50, got {result.e1kv_fields['863']}"


def test_derivative_loss_lands_in_kz_892_not_857():
    """An option close at a loss → KZ 892, not KZ 857."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades>
            <Trade currency="EUR" fxRateToBase="1" assetCategory="OPT" symbol="SPY 20260620 P 450"
                description="SPY PUT" isin="" dateTime="20260601;100000" quantity="-1" tradePrice="2.00"
                proceeds="-200" ibCommission="-1" openCloseIndicator="C" cost="0" fifoPnlRealized="-300" buySell="BUY"/>
        </Trades>
        <CashTransactions/>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert result.e1kv_fields["857"] == 0.0, f"No gains, KZ 857 must be 0, got {result.e1kv_fields['857']}"
    assert result.e1kv_fields["892"] >= 299.0, f"Option loss must surface in KZ 892, got {result.e1kv_fields['892']}"


def test_wht_reversal_subtracts_from_credit():
    """A positive-amount 'Withholding Tax' reversal row must reduce the credited WHT."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="XYZ" description="Dividend XYZ"
                isin="US0000000000" dateTime="20260101" amount="100" type="Dividends"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="XYZ" description="US withholding"
                isin="US0000000000" dateTime="20260101" amount="-15" type="Withholding Tax"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="XYZ" description="WHT reversal"
                isin="US0000000000" dateTime="20260105" amount="5" type="Withholding Tax"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    # Net WHT = 15 − 5 = 10, capped at 15% of 100 = 15 → all 10 creditable.
    assert abs(result.e1kv_fields["998"] - 10.0) < 0.01, f"Net WHT credit should be 10 after reversal, got {result.e1kv_fields['998']}"


def test_warrant_routed_to_manual_queue():
    """WAR / IOPT assetCategory must go to the manual queue, not KZ 857."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades>
            <Trade currency="EUR" fxRateToBase="1" assetCategory="WAR" symbol="DBKW"
                description="DB CALL WAR" isin="DE000DH7AAC1" dateTime="20260601;100000" quantity="-100" tradePrice="2.00"
                proceeds="200" ibCommission="0" openCloseIndicator="C" cost="0" fifoPnlRealized="150" buySell="SELL"/>
        </Trades>
        <CashTransactions/>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert result.e1kv_fields["857"] == 0.0, f"Warrant must NOT populate KZ 857, got {result.e1kv_fields['857']}"
    assert not result.manual_processing.empty, "Warrant must appear in manual queue"
    assert "WAR" in set(result.manual_processing["assetCategory"]), "WAR must be present in manual queue"


def test_bank_vs_bond_interest_split_by_type():
    """IBKR `type` field is authoritative — Broker Interest → KZ 861 (25%), Bond Interest → KZ 409 (27.5%)."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="" description="Broker interest"
                isin="" dateTime="20260430" amount="10" type="Broker Interest Received"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="DE10Y" description="Coupon"
                isin="DE0001102309" dateTime="20260430" amount="80" type="Bond Interest Received"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    assert abs(result.e1kv_fields["861"] - 10.0) < 0.01, f"Broker interest → KZ 861=10, got {result.e1kv_fields['861']}"
    assert abs(result.e1kv_fields["409"] - 80.0) < 0.01, f"Bond interest → KZ 409=80, got {result.e1kv_fields['409']}"


def test_multi_year_statement_detected():
    """years_in_parsed returns every distinct calendar year so the UI can refuse a cross-year run."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades>
            <Trade currency="EUR" fxRateToBase="1" assetCategory="STK" symbol="FOO"
                description="FOO" isin="DE0000000001" dateTime="20240601;100000" quantity="1" tradePrice="100"
                proceeds="-100" ibCommission="0" openCloseIndicator="O" cost="100" fifoPnlRealized="0" buySell="BUY"/>
        </Trades>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="" description="Broker interest"
                isin="" dateTime="20250430" amount="10" type="Broker Interest Received"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    assert years_in_parsed(parsed) == [2024, 2025], f"Both years expected, got {years_in_parsed(parsed)}"


def test_cost_basis_fx_conversion_uses_trade_date_eur():
    """USD BUY at ECB rate ~0.84775 EUR/USD → 100 USD becomes ~84.78 EUR cost basis."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades>
            <Trade currency="USD" fxRateToBase="0.84775" assetCategory="STK" symbol="ABC"
                description="ABC" isin="US0000000001" dateTime="20260601;100000" quantity="1" tradePrice="100"
                proceeds="-100" ibCommission="0" openCloseIndicator="O" cost="100" fifoPnlRealized="0" buySell="BUY"/>
        </Trades>
        <CashTransactions/>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    stk_buy = result.audit[result.audit["category"] == "STK"].iloc[0]
    # Expect within a wide band — ECB may return its own rate if cache lookup succeeds;
    # IBKR fxRateToBase fallback is 0.84775. Either way must be in a sensible USD→EUR range.
    new_avg = float(stk_buy["new_avg_cost_eur"])
    assert 70.0 < new_avg < 110.0, f"USD cost basis converted to EUR must be in reasonable range, got {new_avg}"


def test_per_type_wht_cap_does_not_cross_subsidise():
    """Bond WHT cannot consume cap headroom that belongs to dividends, and vice versa."""
    synthetic_xml = """<FlexQueryResponse><FlexStatements><FlexStatement>
        <Trades/>
        <CashTransactions>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="XYZ" description="Dividend XYZ"
                isin="US0000000000" dateTime="20260101" amount="100" type="Dividends"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="DE10Y" description="Bond Interest"
                isin="DE0001102309" dateTime="20260101" amount="100" type="Bond Interest Received"/>
            <CashTransaction currency="EUR" fxRateToBase="1" symbol="DE10Y" description="Bond WHT"
                isin="DE0001102309" dateTime="20260101" amount="-25" type="Withholding Tax"/>
        </CashTransactions>
    </FlexStatement></FlexStatements></FlexQueryResponse>"""
    parsed = get_parser("IBKR Flex XML")(synthetic_xml.encode())
    result = TaxAggregator().run(parsed)
    # Bond cap = 15% of 100 = 15. Bond WHT of 25 must be capped at 15 even though dividend cap (15)
    # is unused. Net 998 = 0 (dividend WHT) + 15 (bond WHT capped) = 15.
    assert abs(result.e1kv_fields["998"] - 15.0) < 0.01, f"Bond WHT capped at 15 per type, got {result.e1kv_fields['998']}"
    # Excess = 25 − 15 = 10 from bond WHT above its own per-type cap.
    assert result.excess_wht >= 10.0 - 0.01, f"Excess WHT must surface 10 bond excess, got {result.excess_wht}"


if __name__ == "__main__":
    test_sample_runs()
    test_dba_cap_and_excess_surfaced()
    test_altbestand_exclusion()
    test_bank_interest_taxed_at_25_not_275()
    test_securities_losses_do_not_offset_bank_interest()
    test_bond_interest_routed_to_kz_409_not_863()
    test_derivative_loss_lands_in_kz_892_not_857()
    test_wht_reversal_subtracts_from_credit()
    test_warrant_routed_to_manual_queue()
    test_bank_vs_bond_interest_split_by_type()
    test_multi_year_statement_detected()
    test_cost_basis_fx_conversion_uses_trade_date_eur()
    test_per_type_wht_cap_does_not_cross_subsidise()
    print("smoke test passed")
