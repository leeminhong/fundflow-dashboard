"""Status recomputation and assembly of the web-ready fundflow JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import (
    BOK_MARKET_LIST_URL,
    ITEM_LINK_OVERRIDES,
    PageResult,
    SECTOR_ORDER,
    TARGET_ITEMS,
)
from .httpfetch import (
    choose_balance_attachment,
    extract_attachments,
    extract_ntt_id,
    extract_title,
    fetch_bytes,
    safe_filename,
)
from .parsing import parse_market_workbook

# 기준일은 메인 데이터인 FREESIS의 최종 영업일을 따른다.
# BOK·SEIBro는 갱신 시점이 FREESIS와 어긋날 수 있는데, 모든 소스가 채워진
# "완전한 날짜"를 기준일로 잡으면 FREESIS가 더 최신이어도 과거로 끌려간다.
# FREESIS record는 source가 "FREESIS"로 시작하므로 이를 식별자로 쓴다.
FREESIS_SOURCE_PREFIX = "FREESIS"


def freesis_default_date(records: list[dict]) -> str | None:
    """FREESIS 항목에 실제 잔액이 채워진 가장 최근 날짜를 반환(없으면 None)."""
    freesis_dates = {
        record["date"]
        for record in records
        if str(record.get("source", "")).startswith(FREESIS_SOURCE_PREFIX)
        and record.get("balanceValue") is not None
    }
    return max(freesis_dates) if freesis_dates else None


def recompute_status_summary(data: dict) -> None:
    items = sorted(data["items"], key=lambda item: item["displayOrder"])
    active_items = [item for item in items if item.get("isActive", True)]
    active_codes = [item["itemCode"] for item in active_items]
    data["items"] = items
    data["records"] = sorted(
        data["records"],
        key=lambda record: (record["date"], record["displayOrder"], record["itemCode"]),
    )
    data["dates"] = sorted({record["date"] for record in data["records"]})
    data["sectors"] = sorted({item["sector"] for item in active_items}, key=lambda sector: SECTOR_ORDER.get(sector, 99))

    date_status = []
    complete_dates = []
    records_by_date: dict[str, dict[str, dict]] = {}
    for record in data["records"]:
        if not record.get("isActive", True):
            continue
        records_by_date.setdefault(record["date"], {})[record["itemCode"]] = record

    for date_value in data["dates"]:
        per_code = records_by_date.get(date_value, {})
        missing = []
        for item in active_items:
            if item.get("itemType") == "calculated":
                continue
            row = per_code.get(item["itemCode"])
            if row is None or row.get("changeValue") is None or row.get("balanceValue") is None:
                missing.append(item["itemName"])
        is_complete = len(missing) == 0
        if is_complete:
            complete_dates.append(date_value)
        date_status.append(
            {
                "date": date_value,
                "isComplete": is_complete,
                "missingItems": missing,
                "pendingItems": missing,
                "filledItemCount": len(active_codes) - len(missing),
                "totalItemCount": len(active_codes),
            }
        )

    data["dateStatus"] = date_status
    latest_date = data["dates"][-1] if data["dates"] else None
    default_date = freesis_default_date(data["records"]) or (
        complete_dates[-1] if complete_dates else latest_date
    )

    default_records = [
        record
        for record in data["records"]
        if record["date"] == default_date and record.get("includeInTotal", True) and record.get("changeValue") is not None
    ]
    sector_summary = []
    for sector in data["sectors"]:
        sector_records = [record for record in default_records if record["sector"] == sector]
        sector_summary.append(
            {
                "sector": sector,
                "latestChange": sum(record["changeValue"] or 0 for record in sector_records),
                "latestBalance": sum(record["balanceValue"] or 0 for record in sector_records),
                "itemCount": len(sector_records),
            }
        )

    data["summary"] = {
        "latestDate": latest_date,
        "defaultDate": default_date,
        "totalLatestChange": sum(record["changeValue"] or 0 for record in default_records),
        "sectorSummary": sector_summary,
    }
    data["meta"]["latestDate"] = latest_date
    data["meta"]["defaultDate"] = default_date
    data["meta"]["historyWindow"] = len(data["dates"])


def item_link(item_code: str) -> str:
    return ITEM_LINK_OVERRIDES.get(item_code, BOK_MARKET_LIST_URL)


def parse_page_result(page_url: str, html: str, output_dir: Path) -> PageResult:
    title = extract_title(html)
    attachments = extract_attachments(page_url, html)
    selected = choose_balance_attachment(attachments)

    output_path = output_dir / safe_filename(selected.label)
    output_path.write_bytes(fetch_bytes(selected.url))
    parsed = parse_market_workbook(output_path)
    parsed_path = output_path.with_suffix(".json")
    parsed_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"page_title: {title}")
    print(f"page_url: {page_url}")
    print(f"attachments_found: {len(attachments)}")
    print(f"selected_attachment: {selected.label}")
    print(f"downloaded: {output_path}")
    print(f"bytes: {output_path.stat().st_size}")
    print(f"parsed_json: {parsed_path}")
    print(f"balance_date: {parsed['balanceDate']}")
    if parsed["missingItems"]:
        print("missing_items: " + ", ".join(parsed["missingItems"]))

    return PageResult(
        page_url=page_url,
        page_title=title,
        attachment=selected,
        parsed=parsed,
    )


def build_web_data(page_results: list[PageResult]) -> dict:
    if not page_results:
        raise RuntimeError("No page results to build web data.")

    latest_by_item: dict[str, dict] = {}
    records_by_key: dict[tuple[str, str], dict] = {}
    records = []
    item_map: dict[str, dict] = {}

    for source_key, source_meta in TARGET_ITEMS.items():
        item = {
            "itemCode": source_meta["itemCode"],
            "sector": source_meta["sector"],
            "groupName": source_meta["itemName"],
            "itemName": source_meta["itemName"],
            "parentCode": source_meta.get("parentCode"),
            "level": source_meta.get("level", 1),
            "itemType": "raw",
            "includeInTotal": source_meta.get("includeInTotal", True),
            "requiredForComplete": True,
            "showInHeatmap": True,
            "rawBalanceColumn": source_key,
            "rawChangeColumn": source_key,
            "link": item_link(source_meta["itemCode"]),
            "displayOrder": source_meta["displayOrder"],
            "isActive": True,
            "unit": "조원",
            "source": "한국은행 일일 금융시장 주요지표",
        }
        item_map[item["itemCode"]] = item

    for page_result in sorted(
        page_results,
        key=lambda row: extract_ntt_id(row.page_url) or 0,
        reverse=True,
    ):
        for record in page_result.parsed["records"]:
            item = item_map[record["itemCode"]]
            key = (record["balanceDate"], record["itemCode"])
            existing = records_by_key.get(key)
            # First (newest nttId) wins, EXCEPT when its balance is missing
            # ('..' → None, common for bank items at month-end): let a later
            # backfill post with a real value override the empty daily record.
            if existing is not None and (
                existing["balanceValue"] is not None
                or record["balanceValueTrillionKrw"] is None
            ):
                continue

            payload = {
                "date": record["balanceDate"],
                "sector": record["sector"],
                "groupName": record["itemName"],
                "itemCode": record["itemCode"],
                "itemName": record["itemName"],
                "parentCode": item["parentCode"],
                "level": item["level"],
                "itemType": "raw",
                "includeInTotal": item["includeInTotal"],
                "requiredForComplete": True,
                "showInHeatmap": True,
                "changeValue": record["changeValueTrillionKrw"],
                "balanceValue": record["balanceValueTrillionKrw"],
                "link": item["link"],
                "displayOrder": item["displayOrder"],
                "isActive": True,
                "hasSourceMapping": True,
                "source": "한국은행 일일 금융시장 주요지표",
                "sourceLabel": record["sourceLabel"],
                "sourceUnit": record["sourceUnit"],
                "changeDate": record["changeDate"],
                "balanceDate": record["balanceDate"],
                "sourcePageUrl": page_result.page_url,
                "sourcePageTitle": page_result.page_title,
                "sourceAttachment": page_result.attachment.label,
                "sourceAttachmentUrl": page_result.attachment.url,
            }
            records_by_key[key] = payload

            previous = latest_by_item.get(record["itemCode"])
            if previous is None or (previous["date"] < payload["date"]):
                latest_by_item[record["itemCode"]] = payload

    items = sorted(item_map.values(), key=lambda item: item["displayOrder"])
    records = sorted(records_by_key.values(), key=lambda record: (record["date"], record["displayOrder"]))
    sectors = sorted({item["sector"] for item in items}, key=lambda sector: SECTOR_ORDER.get(sector, 99))
    dates = sorted({record["date"] for record in records})
    if not dates:
        raise RuntimeError("No valid dates were parsed from market indicator files.")

    date_status = []
    default_date = dates[-1]
    complete_dates = []
    expected_codes = [item["itemCode"] for item in items if item["isActive"]]

    for date_value in dates:
        date_records = [record for record in records if record["date"] == date_value and record["isActive"]]
        by_code = {record["itemCode"]: record for record in date_records}
        missing_items = []
        for item in items:
            target = by_code.get(item["itemCode"])
            if target is None:
                missing_items.append(item["itemName"])
                continue
            if target["changeValue"] is None or target["balanceValue"] is None:
                missing_items.append(item["itemName"])

        is_complete = len(missing_items) == 0
        if is_complete:
            complete_dates.append(date_value)

        date_status.append(
            {
                "date": date_value,
                "isComplete": is_complete,
                "missingItems": missing_items,
                "pendingItems": missing_items,
                "filledItemCount": len(expected_codes) - len(missing_items),
                "totalItemCount": len(expected_codes),
            }
        )

    if complete_dates:
        default_date = complete_dates[-1]

    default_records = [
        record
        for record in records
        if record["date"] == default_date and record["changeValue"] is not None
        and record["includeInTotal"]
    ]
    sector_summary = []
    for sector in sectors:
        sector_records = [record for record in default_records if record["sector"] == sector]
        sector_summary.append(
            {
                "sector": sector,
                "latestChange": sum(record["changeValue"] or 0 for record in sector_records),
                "latestBalance": sum(record["balanceValue"] or 0 for record in sector_records),
                "itemCount": len(sector_records),
            }
        )

    return {
        "meta": {
            "title": "Daily Fundflow Dashboard",
            "sourceFile": ", ".join(sorted({row.parsed["sourceFile"] for row in page_results})),
            "sourcePageTitle": page_results[0].page_title,
            "sourcePageUrl": page_results[0].page_url,
            "sourceAttachment": page_results[0].attachment.label,
            "sourceAttachmentUrl": page_results[0].attachment.url,
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "latestDate": dates[-1],
            "defaultDate": default_date,
            "unit": "조원",
            "version": 3,
            "historyWindow": len(dates),
        },
        "items": items,
        "dates": dates,
        "sectors": sectors,
        "dateStatus": date_status,
        "summary": {
            "latestDate": dates[-1],
            "defaultDate": default_date,
            "totalLatestChange": sum(record["changeValue"] or 0 for record in default_records),
            "sectorSummary": sector_summary,
        },
        "records": records,
    }


def merge_web_data(existing: dict, new_data: dict) -> dict:
    """Merge new BOK data into existing JSON, keeping all old records and only adding new dates."""
    old_rec_map: dict[tuple[str, str], dict] = {}
    for r in existing.get("records", []):
        old_rec_map[(r["date"], r["itemCode"])] = r

    new_count = 0
    update_count = 0
    for r in new_data.get("records", []):
        key = (r["date"], r["itemCode"])
        if key in old_rec_map:
            old = old_rec_map[key]
            # Overwrite with new data (corrects stale change values), but never
            # let a now-empty value ('..' → None, e.g. bank items at month-end)
            # clobber a balance we already captured from an earlier backfill.
            if r.get("balanceValue") is None and old.get("balanceValue") is not None:
                continue
            old_rec_map[key] = r
            update_count += 1
        else:
            old_rec_map[key] = r
            new_count += 1

    # Merge items (keep unique by itemCode)
    item_map: dict[str, dict] = {i["itemCode"]: i for i in existing.get("items", [])}
    for i in new_data.get("items", []):
        if i["itemCode"] not in item_map:
            item_map[i["itemCode"]] = i

    records = sorted(old_rec_map.values(), key=lambda r: (r["date"], r.get("displayOrder", 0)))
    items = sorted(item_map.values(), key=lambda i: i.get("displayOrder", 0))
    dates = sorted({r["date"] for r in records})
    sectors = sorted(
        {i["sector"] for i in items if i.get("isActive", True)},
        key=lambda s: SECTOR_ORDER.get(s, 99),
    )

    # Rebuild dateStatus
    active_items = [i for i in items if i.get("isActive", True)]
    active_codes = [i["itemCode"] for i in active_items]
    recs_by_date: dict[str, dict[str, dict]] = {}
    for r in records:
        if r.get("isActive", True):
            recs_by_date.setdefault(r["date"], {})[r["itemCode"]] = r

    date_status = []
    complete_dates = []
    for d in dates:
        per_code = recs_by_date.get(d, {})
        missing = []
        for item in active_items:
            if item.get("itemType") == "calculated":
                continue
            row = per_code.get(item["itemCode"])
            if row is None or row.get("changeValue") is None or row.get("balanceValue") is None:
                missing.append(item["itemName"])
        is_complete = len(missing) == 0
        if is_complete:
            complete_dates.append(d)
        date_status.append({
            "date": d, "isComplete": is_complete,
            "missingItems": missing, "pendingItems": missing,
            "filledItemCount": len(active_codes) - len(missing),
            "totalItemCount": len(active_codes),
        })

    latest_date = dates[-1] if dates else None
    default_date = freesis_default_date(records) or (
        complete_dates[-1] if complete_dates else latest_date
    )

    default_records = [
        r for r in records
        if r["date"] == default_date
        and r.get("includeInTotal", True)
        and r.get("changeValue") is not None
    ]
    sector_summary = []
    for sector in sectors:
        sec_recs = [r for r in default_records if r["sector"] == sector]
        sector_summary.append({
            "sector": sector,
            "latestChange": sum(r["changeValue"] or 0 for r in sec_recs),
            "latestBalance": sum(r["balanceValue"] or 0 for r in sec_recs),
            "itemCount": len(sec_recs),
        })

    # Preserve FREESIS/SEIBro meta from existing
    meta = existing.get("meta", {})
    meta.update({
        "title": "Daily Fundflow Dashboard",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "latestDate": latest_date,
        "defaultDate": default_date,
        "unit": "조원",
        "version": 3,
        "historyWindow": len(dates),
    })

    print(f"merge: {new_count} new, {update_count} updated, {len(records)} total, {len(dates)} dates")

    return {
        "meta": meta,
        "items": items,
        "dates": dates,
        "sectors": sectors,
        "dateStatus": date_status,
        "summary": {
            "latestDate": latest_date,
            "defaultDate": default_date,
            "totalLatestChange": sum(r["changeValue"] or 0 for r in default_records),
            "sectorSummary": sector_summary,
        },
        "records": records,
    }


