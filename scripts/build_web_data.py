import json
from datetime import datetime
from pathlib import Path


SOURCE_JSON = Path("outputs/fundflow_mvp/source_data.json")
OUTPUT_JSON = Path("data/fundflow.json")

FREESIS_LINK = "https://freesis.kofia.or.kr"
REPO_LINK = "https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/repo/BIP_CNTS09001V.xml&menuNo=233"


ITEM_MASTER = [
    {
        "itemCode": "BANK_TOTAL_DEPOSIT",
        "sector": "은행",
        "groupName": "실세총예금",
        "itemName": "실세총예금",
        "parentCode": None,
        "level": 1,
        "itemType": "calculated",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": None,
        "rawChangeColumn": None,
        "link": "",
        "displayOrder": 10,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "BANK_SAVINGS_DEPOSIT",
        "sector": "은행",
        "groupName": "실세총예금",
        "itemName": "저축성예금",
        "parentCode": "BANK_TOTAL_DEPOSIT",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "저축성예금",
        "rawChangeColumn": "저축성예금증감",
        "link": "",
        "displayOrder": 11,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "BANK_DEMAND_DEPOSIT",
        "sector": "은행",
        "groupName": "실세총예금",
        "itemName": "요구불예금",
        "parentCode": "BANK_TOTAL_DEPOSIT",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "요구불예금",
        "rawChangeColumn": "요구불예금증감",
        "link": "",
        "displayOrder": 12,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "BANK_MONEY_TRUST",
        "sector": "은행",
        "groupName": "금전신탁",
        "itemName": "금전신탁",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "금전신탁",
        "rawChangeColumn": "금전신탁증감",
        "link": "",
        "displayOrder": 20,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "REPO_INTERDEALER",
        "sector": "Repo",
        "groupName": "기관간Repo",
        "itemName": "기관간Repo",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "RP잔고",
        "rawChangeColumn": "RP잔고증감",
        "link": REPO_LINK,
        "displayOrder": 30,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_MMF",
        "sector": "투신",
        "groupName": "MMF",
        "itemName": "MMF",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "MMF",
        "rawChangeColumn": "MMF증감",
        "link": FREESIS_LINK,
        "displayOrder": 40,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_BOND_TOTAL",
        "sector": "투신",
        "groupName": "채권형",
        "itemName": "채권형",
        "parentCode": None,
        "level": 1,
        "itemType": "calculated",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": None,
        "rawChangeColumn": None,
        "link": FREESIS_LINK,
        "displayOrder": 50,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_BOND_PUBLIC",
        "sector": "투신",
        "groupName": "채권형",
        "itemName": "채권형 공모",
        "parentCode": "FUND_BOND_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "채권 공모",
        "rawChangeColumn": "채권공모증감",
        "link": FREESIS_LINK,
        "displayOrder": 51,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_BOND_PRIVATE",
        "sector": "투신",
        "groupName": "채권형",
        "itemName": "채권형 사모",
        "parentCode": "FUND_BOND_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "채권 사모",
        "rawChangeColumn": "채권사모증감",
        "link": FREESIS_LINK,
        "displayOrder": 52,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_BOND_DISCRETIONARY",
        "sector": "투신",
        "groupName": "채권형",
        "itemName": "채권형 일임",
        "parentCode": "FUND_BOND_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "채권투자일임",
        "rawChangeColumn": "채권일임증감",
        "link": FREESIS_LINK,
        "displayOrder": 53,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_EQUITY_TOTAL",
        "sector": "투신",
        "groupName": "주식형",
        "itemName": "주식형",
        "parentCode": None,
        "level": 1,
        "itemType": "calculated",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": None,
        "rawChangeColumn": None,
        "link": FREESIS_LINK,
        "displayOrder": 60,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_EQUITY_PUBLIC",
        "sector": "투신",
        "groupName": "주식형",
        "itemName": "주식형 공모",
        "parentCode": "FUND_EQUITY_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "주식 공모",
        "rawChangeColumn": "주식공모증감",
        "link": FREESIS_LINK,
        "displayOrder": 61,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_EQUITY_PRIVATE",
        "sector": "투신",
        "groupName": "주식형",
        "itemName": "주식형 사모",
        "parentCode": "FUND_EQUITY_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "주식 사모",
        "rawChangeColumn": "주식사모증감",
        "link": FREESIS_LINK,
        "displayOrder": 62,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "FUND_EQUITY_DISCRETIONARY",
        "sector": "투신",
        "groupName": "주식형",
        "itemName": "주식형 일임",
        "parentCode": "FUND_EQUITY_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": True,
        "showInHeatmap": True,
        "rawBalanceColumn": "주식투자일임",
        "rawChangeColumn": "주식일임증감",
        "link": FREESIS_LINK,
        "displayOrder": 63,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "SEC_REPO_CUSTOMER",
        "sector": "증권",
        "groupName": "대고객Repo",
        "itemName": "대고객Repo",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "대고객Repo",
        "rawChangeColumn": "대고객Repo증감",
        "link": REPO_LINK,
        "displayOrder": 70,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "SEC_CMA_TOTAL",
        "sector": "증권",
        "groupName": "CMA",
        "itemName": "CMA",
        "parentCode": None,
        "level": 1,
        "itemType": "calculated",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": None,
        "rawChangeColumn": None,
        "link": "",
        "displayOrder": 80,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "SEC_CMA_RP",
        "sector": "증권",
        "groupName": "CMA",
        "itemName": "CMA(RP형)",
        "parentCode": "SEC_CMA_TOTAL",
        "level": 2,
        "itemType": "raw",
        "includeInTotal": False,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "CMA(RP형)",
        "rawChangeColumn": "CMA(RP형)증감",
        "link": "",
        "displayOrder": 81,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "SEC_NOTE",
        "sector": "증권",
        "groupName": "발행어음",
        "itemName": "발행어음",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "발행어음",
        "rawChangeColumn": "발행어음증감",
        "link": "",
        "displayOrder": 90,
        "isActive": True,
        "unit": "조원",
    },
    {
        "itemCode": "SEC_CUSTOMER_DEPOSIT",
        "sector": "증권",
        "groupName": "고객예탁금",
        "itemName": "고객예탁금",
        "parentCode": None,
        "level": 1,
        "itemType": "raw",
        "includeInTotal": True,
        "requiredForComplete": False,
        "showInHeatmap": True,
        "rawBalanceColumn": "고객예탁금",
        "rawChangeColumn": "고객예탁금증감",
        "link": "",
        "displayOrder": 100,
        "isActive": True,
        "unit": "조원",
    },
]

SECTOR_ORDER = {"은행": 1, "Repo": 2, "투신": 3, "증권": 4}


def value_for(raw_row, column_name):
    if not column_name:
        return None
    return raw_row.get(column_name)


def has_source_mapping(item, source_headers):
    return bool(
        item.get("rawBalanceColumn")
        and item.get("rawChangeColumn")
        and item["rawBalanceColumn"] in source_headers
        and item["rawChangeColumn"] in source_headers
    )


def build_raw_record(date_value, item, raw_row, source_headers):
    return {
        "date": date_value,
        "sector": item["sector"],
        "groupName": item["groupName"],
        "itemCode": item["itemCode"],
        "itemName": item["itemName"],
        "parentCode": item["parentCode"],
        "level": item["level"],
        "itemType": item["itemType"],
        "includeInTotal": item["includeInTotal"],
        "requiredForComplete": item["requiredForComplete"],
        "showInHeatmap": item["showInHeatmap"],
        "changeValue": value_for(raw_row, item["rawChangeColumn"]),
        "balanceValue": value_for(raw_row, item["rawBalanceColumn"]),
        "link": item["link"],
        "displayOrder": item["displayOrder"],
        "isActive": item["isActive"],
        "hasSourceMapping": has_source_mapping(item, source_headers),
    }


def sum_child_values(child_records, key):
    values = [record[key] for record in child_records if record[key] is not None]
    if not values:
        return None
    return sum(values)


def main():
    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    raw_rows = source["dataRows"]
    source_headers = set(source["headers"])
    dates = sorted(row["날짜"] for row in raw_rows)
    items = sorted(ITEM_MASTER, key=lambda item: item["displayOrder"])
    item_by_code = {item["itemCode"]: item for item in items}
    children_by_parent = {}
    for item in items:
        if item["parentCode"]:
            children_by_parent.setdefault(item["parentCode"], []).append(item)

    records = []
    for raw_row in raw_rows:
        date_value = raw_row["날짜"]
        day_records = {}

        for item in items:
            if item["itemType"] == "raw":
                record = build_raw_record(date_value, item, raw_row, source_headers)
                day_records[item["itemCode"]] = record

        for item in items:
            if item["itemType"] != "calculated":
                continue
            child_records = [
                day_records[child["itemCode"]]
                for child in children_by_parent.get(item["itemCode"], [])
                if child["itemCode"] in day_records
            ]
            day_records[item["itemCode"]] = {
                "date": date_value,
                "sector": item["sector"],
                "groupName": item["groupName"],
                "itemCode": item["itemCode"],
                "itemName": item["itemName"],
                "parentCode": item["parentCode"],
                "level": item["level"],
                "itemType": item["itemType"],
                "includeInTotal": item["includeInTotal"],
                "requiredForComplete": item["requiredForComplete"],
                "showInHeatmap": item["showInHeatmap"],
                "changeValue": sum_child_values(child_records, "changeValue"),
                "balanceValue": sum_child_values(child_records, "balanceValue"),
                "link": item["link"],
                "displayOrder": item["displayOrder"],
                "isActive": item["isActive"],
                "hasSourceMapping": False,
            }

        records.extend(day_records[item["itemCode"]] for item in items)

    sectors = sorted({item["sector"] for item in items}, key=lambda sector: SECTOR_ORDER.get(sector, 99))
    required_items = [
        item for item in items
        if item["isActive"] and item["requiredForComplete"] and has_source_mapping(item, source_headers)
    ]
    pending_items = [
        item["itemName"] for item in items
        if item["isActive"] and item["itemType"] == "raw" and not has_source_mapping(item, source_headers)
    ]
    records_by_date = {
        date_value: [record for record in records if record["date"] == date_value and record["isActive"]]
        for date_value in dates
    }

    date_status = []
    for date_value in dates:
        day_records = records_by_date[date_value]
        missing = []
        for item in required_items:
            record = next((candidate for candidate in day_records if candidate["itemCode"] == item["itemCode"]), None)
            if not record or record["changeValue"] is None or record["balanceValue"] is None:
                missing.append(item["itemName"])
        date_status.append(
            {
                "date": date_value,
                "isComplete": len(missing) == 0,
                "missingItems": missing,
                "pendingItems": pending_items,
                "filledItemCount": len(required_items) - len(missing),
                "totalItemCount": len(required_items),
            }
        )

    latest_date = dates[-1] if dates else None
    complete_dates = [row["date"] for row in date_status if row["isComplete"]]
    default_date = complete_dates[-1] if complete_dates else latest_date
    default_records = [
        record for record in records_by_date.get(default_date, [])
        if record["includeInTotal"] and record["changeValue"] is not None
    ]

    sector_summary = []
    for sector in sectors:
        sector_records = [record for record in default_records if record["sector"] == sector]
        sector_summary.append(
            {
                "sector": sector,
                "latestChange": sum((record["changeValue"] or 0) for record in sector_records),
                "latestBalance": sum((record["balanceValue"] or 0) for record in sector_records),
                "itemCount": len({record["itemCode"] for record in sector_records}),
            }
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "meta": {
                    "title": "Daily Fundflow Dashboard",
                    "sourceFile": source["source"],
                    "generatedAt": datetime.now().isoformat(timespec="seconds"),
                    "latestDate": latest_date,
                    "defaultDate": default_date,
                    "unit": "조원",
                    "version": 2,
                },
                "items": items,
                "dates": dates,
                "sectors": sectors,
                "dateStatus": date_status,
                "summary": {
                    "latestDate": latest_date,
                    "defaultDate": default_date,
                    "totalLatestChange": sum((record["changeValue"] or 0) for record in default_records),
                    "sectorSummary": sector_summary,
                },
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"saved {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
