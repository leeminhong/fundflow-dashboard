"""Unit tests for the pure helpers in fundflow_pipeline.

These cover the parsing/normalization functions and a couple of structural
invariants (sector order, item links). They run without network access.
"""

from datetime import date, datetime

from fundflow_pipeline.config import (
    BOK_MARKET_LIST_URL,
    FREESIS_LINK_URL,
    REPO_LINK_URL,
    SECTOR_ORDER,
)
from fundflow_pipeline.parsing import (
    excel_date,
    normalize_label,
    parse_ymd,
    to_number,
)
from fundflow_pipeline.webdata import item_link


def test_to_number_parses_and_rejects():
    assert to_number(1234) == 1234.0
    assert to_number("1,234.5") == 1234.5
    assert to_number("  -5.5 ") == -5.5
    for blank in ("-", "", "..", None, "abc"):
        assert to_number(blank) is None


def test_parse_ymd_supported_formats():
    assert parse_ymd("2026/05/22") == "2026-05-22"
    assert parse_ymd("2026-05-22") == "2026-05-22"
    assert parse_ymd("20260522") == "2026-05-22"
    assert parse_ymd(datetime(2026, 5, 22, 13, 0)) == "2026-05-22"
    assert parse_ymd(date(2026, 5, 22)) == "2026-05-22"
    # Dotted format and empties are intentionally unsupported.
    assert parse_ymd("2026.05.22") is None
    assert parse_ymd("") is None
    assert parse_ymd(None) is None


def test_excel_date_only_accepts_date_types():
    assert excel_date(datetime(2026, 5, 22)) == "2026-05-22"
    assert excel_date(date(2026, 5, 22)) == "2026-05-22"
    assert excel_date("2026-05-22") is None
    assert excel_date(None) is None


def test_normalize_label_strips_noise():
    assert normalize_label("실세 (총예금)") == "실세총예금"
    assert normalize_label("  실세 \n 총예금 ") == "실세총예금"
    assert normalize_label("주식형1)") == "주식형"
    assert normalize_label("CMA*") == "CMA"
    assert normalize_label(None) == ""


def test_item_link_routing():
    assert item_link("REPO_INTERBANK") == REPO_LINK_URL
    assert item_link("SEC_CUSTOMER_RP") == REPO_LINK_URL
    assert item_link("FUND_BOND") == FREESIS_LINK_URL
    # Unknown codes fall back to the BOK list page.
    assert item_link("SOMETHING_ELSE") == BOK_MARKET_LIST_URL


def test_sector_order_matches_frontend():
    # Must stay in sync with app.js `sectorOrder` (REPO→투신→증권→은행).
    assert SECTOR_ORDER == {"REPO": 1, "투신": 2, "증권": 3, "은행": 4}
