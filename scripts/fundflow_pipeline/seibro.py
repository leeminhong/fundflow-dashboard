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
    if not rows:
        return

    item = next((row for row in data["items"] if row["itemCode"] == SEIBRO_REPO_ITEM["itemCode"]), None)
    if item is None:
        item = dict(SEIBRO_REPO_ITEM)
        data["items"].append(item)

    data["records"] = [record for record in data["records"] if record["itemCode"] != item["itemCode"]]

    prev_balance = None
    for row in rows:
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

    data["meta"]["seibroRepoRows"] = len(rows)
    data["meta"]["seibroRepoLatestDate"] = rows[-1]["date"]


