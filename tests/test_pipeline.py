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
from fundflow_pipeline.seibro import apply_seibro_repo
from fundflow_pipeline.webdata import item_link


def _repo_records(data):
    return sorted(
        (r for r in data["records"] if r["itemCode"] == "REPO_INTERBANK"),
        key=lambda r: r["date"],
    )


def _seibro_row(date_iso, balance_billion):
    return {"date": date_iso, "balanceAmountBillion": balance_billion, "tradeAmountBillion": 0}


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


def test_seibro_fresh_fill_computes_changes():
    # No prior REPO history: SEIBro fills all rows, change carried day over day.
    data = {"items": [], "records": [], "meta": {}}
    apply_seibro_repo(data, [_seibro_row("2026-05-20", 275000), _seibro_row("2026-05-21", 276000)])
    repo = _repo_records(data)
    assert [r["balanceValue"] for r in repo] == [275.0, 276.0]
    assert [r["changeValue"] for r in repo] == [0.0, 1.0]


def test_seibro_preserves_manual_history_and_forward_fills():
    # Manually backfilled 5/22 must survive; SEIBro only adds the newer 5/23,
    # and the overlapping 5/22 row from SEIBro is ignored.
    data = {
        "items": [],
        "records": [
            {"itemCode": "REPO_INTERBANK", "date": "2026-05-22", "balanceValue": 272.0, "changeValue": 1.2},
        ],
        "meta": {},
    }
    apply_seibro_repo(data, [_seibro_row("2026-05-22", 999000), _seibro_row("2026-05-23", 273000)])
    repo = _repo_records(data)
    assert len(repo) == 2
    assert repo[0] == {"itemCode": "REPO_INTERBANK", "date": "2026-05-22", "balanceValue": 272.0, "changeValue": 1.2}
    assert repo[1]["date"] == "2026-05-23"
    assert repo[1]["balanceValue"] == 273.0
    assert repo[1]["changeValue"] == 1.0  # 273.0 - 272.0, carried across the boundary


def test_seibro_noop_when_nothing_newer():
    data = {
        "items": [],
        "records": [
            {"itemCode": "REPO_INTERBANK", "date": "2026-05-25", "balanceValue": 275.0, "changeValue": 0.0},
        ],
        "meta": {},
    }
    apply_seibro_repo(data, [_seibro_row("2026-05-20", 270000)])  # older than existing
    repo = _repo_records(data)
    assert len(repo) == 1 and repo[0]["balanceValue"] == 275.0


def test_seibro_empty_rows_is_noop():
    data = {"items": [], "records": [], "meta": {}}
    apply_seibro_repo(data, [])
    assert _repo_records(data) == []
