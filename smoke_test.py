from parsers import get_parser
from tax_engine import TaxAggregator


def test_sample_runs():
    parsed = get_parser("IBKR Flex XML")("sample_flex.xml")
    result = TaxAggregator().run(parsed)
    assert "861" in result.e1kv_fields
    assert "775" in result.e1kv_fields
    assert len(result.manual_processing) == 1
    assert not result.audit.empty


if __name__ == "__main__":
    test_sample_runs()
    print("smoke test passed")
