"""Command-line entry point for the BOK + FREESIS + SEIBro fundflow pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .freesis import apply_freesis_db, apply_freesis_summary
from .httpfetch import (
    discover_recent_page_urls,
    extract_ntt_id,
    extract_rss_page_urls,
    fetch_text,
)
from .seibro import apply_seibro_repo, fetch_seibro_repo_rows
from .webdata import (
    build_web_data,
    merge_web_data,
    parse_page_result,
    recompute_status_summary,
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url",
        help="BOK detail page URL, e.g. https://www.bok.or.kr/portal/bbs/P0002018/view.do?nttId=...&menuNo=200366",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/bok_market_indicator",
        help="Directory to save the downloaded attachment.",
    )
    parser.add_argument(
        "--write-web-data",
        default=None,
        help="Optional path to write dashboard data JSON, e.g. data/fundflow.json.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many recent market-indicator pages to aggregate (default: 7).",
    )
    parser.add_argument(
        "--freesis-summary-xlsx",
        default=None,
        help="Optional FREESIS summary xlsx path (요약 sheet) to replace fund items with 11 detailed rows.",
    )
    parser.add_argument(
        "--freesis-db-json",
        default=None,
        help="Path to freesis_db.json for cumulative fund/deposit data. "
             "Auto-detected at data/freesis_db.json if --freesis-summary-xlsx is not set.",
    )
    parser.add_argument(
        "--skip-seibro-repo",
        action="store_true",
        help="Skip SEIBro Repo 잔고금액 merge for SEC_CUSTOMER_RP.",
    )
    parser.add_argument(
        "--seibro-repo-limit",
        type=int,
        default=7,
        help="How many recent SEIBro daily rows to merge (default: 7).",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_urls, html_cache = discover_recent_page_urls(args.url, args.days)
    rss_urls = extract_rss_page_urls(limit=max(args.days * 6, 20))
    candidate_urls = sorted(
        set(page_urls + rss_urls),
        key=lambda url: extract_ntt_id(url) or 0,
        reverse=True,
    )

    print(f"seed_url: {args.url}")
    print(f"discovered_pages_from_related: {len(page_urls)}")
    print(f"discovered_pages_from_rss: {len(rss_urls)}")
    print(f"candidate_pages: {len(candidate_urls)}")
    for idx, page_url in enumerate(candidate_urls[:20], start=1):
        print(f"[{idx}] {page_url}")

    page_results = []
    seen_balance_dates = set()
    for page_url in candidate_urls:
        if len(page_results) >= args.days:
            break
        html = html_cache.get(page_url) or fetch_text(page_url)
        try:
            page_result = parse_page_result(page_url, html, output_dir)
        except Exception as exc:
            print(f"skip_page: {page_url} ({exc})")
            continue

        balance_date = page_result.parsed["balanceDate"]
        if balance_date in seen_balance_dates:
            print(f"skip_duplicate_date: {page_url} ({balance_date})")
            continue
        seen_balance_dates.add(balance_date)

        page_results.append(page_result)
        print("parsed_records:")
        for record in page_result.parsed["records"]:
            change = record["changeValueTrillionKrw"]
            balance = record["balanceValueTrillionKrw"]
            change_text = "-" if change is None else f"{change:,.4f}"
            balance_text = "-" if balance is None else f"{balance:,.4f}"
            print(
                f"- {record['sector']} / {record['itemName']}: "
                f"증감 {change_text}조원, 잔액 {balance_text}조원"
            )
    print(f"selected_pages: {len(page_results)}")
    if len(page_results) < args.days:
        print(f"warning: requested {args.days} pages but only {len(page_results)} valid pages were found.")

    if args.write_web_data:
        web_data = build_web_data(page_results)
        if args.freesis_summary_xlsx:
            freesis_path = Path(args.freesis_summary_xlsx)
            if not freesis_path.exists():
                raise FileNotFoundError(f"FREESIS summary file not found: {freesis_path}")
            apply_freesis_summary(web_data, freesis_path)
            print(f"freesis_summary_applied: {freesis_path}")
        elif args.freesis_db_json:
            db_path = Path(args.freesis_db_json)
            if not db_path.exists():
                raise FileNotFoundError(f"FREESIS DB file not found: {db_path}")
            apply_freesis_db(web_data, db_path)
        else:
            auto_db = Path(__file__).resolve().parent.parent.parent / "data" / "freesis_db.json"
            if auto_db.exists():
                apply_freesis_db(web_data, auto_db)
        if not args.skip_seibro_repo:
            # Skip SEIBro fetch if REPO data already came from freesis_db
            has_repo_from_db = any(r["source"] == "SEIBro Repo 시장현황" for r in web_data["records"] if r["itemCode"] == "REPO_INTERBANK")
            if not has_repo_from_db:
                try:
                    seibro_rows = fetch_seibro_repo_rows(args.seibro_repo_limit)
                    apply_seibro_repo(web_data, seibro_rows)
                    recompute_status_summary(web_data)
                    if seibro_rows:
                        print(f"seibro_repo_applied: {len(seibro_rows)} rows (latest {seibro_rows[-1]['date']})")
                    else:
                        print("seibro_repo_applied: 0 rows")
                except Exception as exc:
                    print(f"warning: seibro_repo_merge_failed: {exc}")
            else:
                print("seibro_repo_skipped: REPO data from freesis_db")
        web_data_path = Path(args.write_web_data)
        web_data_path.parent.mkdir(parents=True, exist_ok=True)

        # Merge with existing JSON (incremental: only add new dates)
        if web_data_path.exists():
            try:
                existing = json.loads(web_data_path.read_text(encoding="utf-8"))
                web_data = merge_web_data(existing, web_data)
            except Exception as exc:
                print(f"warning: could not merge with existing data, overwriting: {exc}")

        web_data_path.write_text(json.dumps(web_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"web_data: {web_data_path}")
