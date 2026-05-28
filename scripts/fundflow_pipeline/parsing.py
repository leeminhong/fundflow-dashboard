"""Value/date normalization and BOK workbook parsing."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import openpyxl

from .config import TARGET_ITEMS

def normalize_label(value: object) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\d+\)", "", text)
    text = re.sub(r"[\s()]+", "", text)
    return text.replace("*", "")


def excel_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def to_number(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", ".."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_ymd(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_market_workbook(path: Path) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet_name = "일일동향" if "일일동향" in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    section_row = None
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == "2. 금융권별 여수신 동향":
                section_row = cell.row
                break
        if section_row:
            break
    if section_row is None:
        raise RuntimeError("Could not find '2. 금융권별 여수신 동향' section.")

    header_row = section_row + 3
    latest_change_col = None
    latest_change_date = None
    balance_col = None
    balance_date = None

    for col in range(1, ws.max_column + 1):
        value = ws.cell(header_row, col).value
        parsed_date = excel_date(value)
        header_label = normalize_label(ws.cell(header_row - 1, col).value)
        if parsed_date and header_label == "잔액":
            balance_col = col
            balance_date = parsed_date
            break

    if balance_col is not None:
        for col in range(1, balance_col):
            parsed_date = excel_date(ws.cell(header_row, col).value)
            if parsed_date:
                latest_change_col = col
                latest_change_date = parsed_date

    if latest_change_col is None or balance_col is None:
        raise RuntimeError("Could not locate latest change and balance date columns.")

    found: dict[str, dict] = {}
    for row_idx in range(section_row + 1, ws.max_row + 1):
        raw_label = ws.cell(row_idx, 3).value
        normalized = normalize_label(raw_label)
        if normalized not in TARGET_ITEMS:
            continue

        meta = TARGET_ITEMS[normalized]
        change_okrw = to_number(ws.cell(row_idx, latest_change_col).value)
        balance_okrw = to_number(ws.cell(row_idx, balance_col).value)
        found[normalized] = {
            **meta,
            "sourceLabel": str(raw_label).strip(),
            "date": balance_date,
            "changeDate": latest_change_date,
            "balanceDate": balance_date,
            "changeValueOkrw": change_okrw,
            "balanceValueOkrw": balance_okrw,
            "changeValueTrillionKrw": None if change_okrw is None else change_okrw / 10000,
            "balanceValueTrillionKrw": None if balance_okrw is None else balance_okrw / 10000,
            "unit": "조원",
            "sourceUnit": "억원",
        }

    missing = [
        TARGET_ITEMS[key]["itemName"]
        for key in TARGET_ITEMS
        if key not in found
    ]
    records = [found[key] for key in TARGET_ITEMS if key in found]
    return {
        "sourceFile": str(path),
        "sheetName": sheet_name,
        "latestChangeDate": latest_change_date,
        "balanceDate": balance_date,
        "records": records,
        "missingItems": missing,
    }


