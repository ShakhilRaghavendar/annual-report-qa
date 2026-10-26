import pytest

from arqa.units import find_amounts, format_crore, parse_amount, to_crore


def test_conversions_to_crore():
    assert to_crore(100, "lakh") == 1.0
    assert to_crore(10, "million") == 1.0
    assert to_crore(1, "billion") == 100.0
    assert to_crore(1234.5, "crore") == 1234.5


def test_parse_indian_and_western_grouping():
    assert parse_amount("₹ 1,23,456 lakh").crore == pytest.approx(1234.56)
    assert parse_amount("Rs. 1,234.56 crore").crore == pytest.approx(1234.56)
    assert parse_amount("INR 12,345.6 million").crore == pytest.approx(1234.56)
    assert parse_amount("₹ 1.2 billion").crore == pytest.approx(120.0)


def test_usd_is_not_converted():
    a = parse_amount("$ 500 million")
    assert a.currency == "USD" and a.crore is None


def test_bare_number_is_not_an_amount():
    assert parse_amount("The year 2025 began") is None
    assert parse_amount("growth of 6.5 per cent") is None


def test_find_all_amounts_in_sentence():
    s = "Revenue was ₹ 2,55,324 crore, up from ₹ 2,40,893 crore; capex of $1.5 billion."
    found = find_amounts(s)
    assert [round(a.crore) for a in found[:2]] == [255324, 240893]
    assert found[2].currency == "USD"


def test_format_crore_indian_grouping():
    assert format_crore(1234567.891) == "₹ 12,34,567.89 crore"
    assert format_crore(999.5) == "₹ 999.50 crore"
    assert format_crore(-1500) == "-₹ 1,500.00 crore"
