"""SEIBro Repo (기관RP) daily balance fetching and injection."""

from __future__ import annotations

import json
import subprocess

from .config import REPO_LINK_URL, SEIBRO_REPO_FETCH_SCRIPT, SEIBRO_REPO_ITEM
from .parsing import parse_ymd, to_number

def fetch_seibro_repo_rows(limit: int) -> list[dict]:
    if not SEIBRO_REPO_FETCH_SCRIPT.exists():
        raise FileNotFoundError(f"SEIBro fetch script not found: {SEIBRO_REPO_FETCH_SCRIPT}")

    cmd = ["node", str(SEIBRO_REPO_FETCH_SCRIPT), "--limit", str(limit)]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    raw = proc.stdout.strip()
    if not raw:
        return []
    rows = json.loads(raw)
    parsed = []
    for row in rows:
        date_iso = parse_ymd(row.get("date"))
        balance_billion = to_number(row.get("balanceAmountBillion"))
        trade_billion = to_number(row.get("tradeAmountBillion"))
        if not date_iso or balance_billion is None:
            continue
        parsed.append(
            {
                "date": date_iso,
                "tradeAmountBillion": trade_billion,
                "balanceAmountBillion": balance_billion,
            }
        )
    parsed.sort(key=lambda row: row["date"])
    return parsed


def apply_seibro_repo(data: dict, rows: list[dict]) -> None:
    """Forward-merge SEIBro daily Repo balances into the dashboard records.

    SEIBro only serves recent dates (no history), so any existing REPO_INTERBANK
    records — e.g. the manually backfilled history injected from freesis_db.json —
    are preserved. SEIBro fills only dates *newer* than the latest existing
    record, with the day-over-day change carried across the boundary. This lets
    daily runs pick up fresh dates automatically without clobbering verified
    history, and is a no-op when nothing newer is available.
    """
    if not rows:
        return

    item = next((row for row in data["items"] if row["itemCode"] == SEIBRO_REPO_ITEM["itemCode"]), None)
    if item is None:
        item = dict(SEIBRO_REPO_ITEM)
        data["items"].append(item)

    existing = sorted(
        (r for r in data["records"] if r["itemCode"] == item["itemCode"]),
        key=lambda r: r["date"],
    )
    latest_existing_date = existing[-1]["date"] if existing else None
    prev_balance = existing[-1]["balanceValue"] if existing else None

    new_rows = [
        row for row in rows
        if latest_existing_date is None or row["date"] > latest_existing_date
    ]
    new_rows.sort(key=lambda row: row["date"])
    if not new_rows:
        return

    for row in new_rows:
        balance = round(row["balanceAmountBillion"] / 1000, 4)
        change = 0.0 if prev_balance is None else round(balance - prev_balance, 4)
        prev_balance = balance
        data["records"].append(
            {
                "date": row["date"],
                "sector": item["sector"],
                "groupName": item["itemName"],
                "itemCode": item["itemCode"],
                "itemName": item["itemName"],
                "parentCode": item.get("parentCode"),
                "level": item.get("level", 1),
                "itemType": item.get("itemType", "raw"),
                "includeInTotal": item.get("includeInTotal", True),
                "requiredForComplete": item.get("requiredForComplete", True),
                "showInHeatmap": item.get("showInHeatmap", True),
                "changeValue": change,
                "balanceValue": balance,
                "link": REPO_LINK_URL,
                "displayOrder": item["displayOrder"],
                "isActive": item.get("isActive", True),
                "hasSourceMapping": True,
                "source": "SEIBro 일별거래현황",
                "sourceLabel": "잔고금액",
                "sourceUnit": "십억원",
                "changeDate": row["date"],
                "balanceDate": row["date"],
                "sourcePageUrl": REPO_LINK_URL,
                "sourcePageTitle": "SEIBro Repo 시장현황",
                "sourceAttachment": "",
                "sourceAttachmentUrl": "",
            }
        )

    data["meta"]["seibroRepoRows"] = len(new_rows)
    data["meta"]["seibroRepoLatestDate"] = new_rows[-1]["date"]


