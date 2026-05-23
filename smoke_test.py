from parsers import get_parser
from tax_engine import TaxAggregator


def test_sample_runs():
    parsed = get_parser("IBKR Flex XML")("sample_flex.xml")
    result = TaxAggregator().run(parsed)
    assert "861" in result.e1kv_fields
    assert "775" in result.e1kv_fields
    assert len(result.manual_processing) == 1
    assert not result.audit.empty
    # Directional assertions — sample has a profitable stock SELL and an option SELL with premium
    assert result.e1kv_fields["861"] > 0, f"Stock SELL should produce positive realized gains, got {result.e1kv_fields['861']}"
    assert result.e1kv_fields["775"] > 0, f"Option SELL premium should be positive income, got {result.e1kv_fields['775']}"
    assert result.tax_due > 0, f"Positive income should produce tax due, got {result.tax_due}"
    # Regression for fifoPnlRealized open/close fix: audit must not contain non-zero P/L rows for openCloseIndicator=O + fifoPnlRealized=0 derivative trades
    open_opt_pnl = result.audit[(result.audit["category"] == "OPT") & (result.audit["buy_sell"] == "BUY")]["realized_pnl_eur"]
    assert (open_opt_pnl == 0.0).all(), f"Opening OPT BUY trades must have 0 realized P/L, got {open_opt_pnl.tolist()}"


if __name__ == "__main__":
    test_sample_runs()
    print("smoke test passed")
