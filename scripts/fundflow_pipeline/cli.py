"""Command-line entry point for the BOK + FREESIS + SEIBro fundflow pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .freesis import apply_freesis_db, apply_freesis_summary
from .httpfetch import (
    discover_recent_page_urls,
    extract_ntt_id,
    extract_rss_entries,
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
    parser.add_argument(
        "--backfill-scan",
        type=int,
        default=60,
        help="How many recent RSS posts to scan (by title) for month-end '잔액' "
             "backfill posts (range workbooks) beyond the daily --days window. "
             "Title-only classification, so this adds no extra downloads "
             "(default: 60, ~1 month of posts).",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_urls, html_cache = discover_recent_page_urls(args.url, args.days)
    # Widen the RSS window so a month-end backfill post (published ~weeks after
    # the dates it covers) still appears, and keep titles so we can classify
    # posts without fetching each page's HTML.
    rss_entries = extract_rss_entries(limit=max(args.days * 6, args.backfill_scan, 20))
    rss_titles = {url: title for url, title in rss_entries}
    rss_urls = [url for url, _ in rss_entries]
    candidate_urls = sorted(
        set(page_urls + rss_urls),
        key=lambda url: extract_ntt_id(url) or 0,
        reverse=True,
    )

    def is_backfill_title(title: str) -> bool:
        # Backfill post titles carry a date range like "4.30~5.13잔액 포함".
        return bool(title) and "~" in title and "잔액" in title

    print(f"seed_url: {args.url}")
    print(f"discovered_pages_from_related: {len(page_urls)}")
    print(f"discovered_pages_from_rss: {len(rss_urls)}")
    print(f"candidate_pages: {len(candidate_urls)}")
    for idx, page_url in enumerate(candidate_urls[:20], start=1):
        print(f"[{idx}] {page_url}")

    page_results = []
    seen_balance_dates = set()
    daily_count = 0  # non-backfill (single-date) pages collected for daily data
    for idx, page_url in enumerate(candidate_urls):
        daily_done = daily_count >= args.days
        scan_done = idx >= args.backfill_scan
        # Stop once the daily window is filled AND we've scanned the title
        # window for backfill posts.
        if daily_done and scan_done:
            break

        # Classify cheaply via the RSS title; only fetch/parse pages we'll use.
        is_backfill = is_backfill_title(rss_titles.get(page_url, ""))
        if daily_done and not is_backfill:
            continue

        html = html_cache.get(page_url) or fetch_text(page_url)
        try:
            page_result = parse_page_result(page_url, html, output_dir)
        except Exception as exc:
            print(f"skip_page: {page_url} ({exc})")
            continue

        if is_backfill:
            backfill_dates = page_result.parsed.get(
                "balanceDates", [page_result.parsed["balanceDate"]]
            )
            print(
                f"backfill_page: {page_url} "
                f"dates={backfill_dates[0]}..{backfill_dates[-1]} ({len(backfill_dates)})"
            )
            seen_balance_dates.update(backfill_dates)
            page_results.append(page_result)
        else:
            balance_date = page_result.parsed["balanceDate"]
            if balance_date in seen_balance_dates:
                print(f"skip_duplicate_date: {page_url} ({balance_date})")
                continue
            seen_balance_dates.add(balance_date)
            page_results.append(page_result)
            daily_count += 1

        print("parsed_records:")
        for record in page_result.parsed["records"]:
            change = record["changeValueTrillionKrw"]
            balance = record["balanceValueTrillionKrw"]
            change_text = "-" if change is None else f"{change:,.4f}"
            balance_text = "-" if balance is None else f"{balance:,.4f}"
            print(
                f"- {record['sector']} / {record['itemName']} ({record['balanceDate']}): "
                f"증감 {change_text}조원, 잔액 {balance_text}조원"
            )
    print(f"selected_pages: {len(page_results)} (daily {daily_count})")
    if daily_count < args.days:
        print(f"warning: requested {args.days} daily pages but only {daily_count} valid pages were found.")

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
            # SEIBro serves only recent dates (no history). apply_seibro_repo
            # forward-fills dates newer than the manually backfilled history in
            # freesis_db, so daily runs pick up fresh dates without clobbering it.
            def _repo_count():
                return sum(1 for r in web_data["records"] if r["itemCode"] == "REPO_INTERBANK")

            try:
                before = _repo_count()
                seibro_rows = fetch_seibro_repo_rows(args.seibro_repo_limit)
                apply_seibro_repo(web_data, seibro_rows)
                recompute_status_summary(web_data)
                added = _repo_count() - before
                if added > 0:
                    print(f"seibro_repo_applied: +{added} new dates (latest {web_data['meta'].get('seibroRepoLatestDate')})")
                else:
                    print("seibro_repo_applied: 0 new dates (history already current)")
            except Exception as exc:
                print(f"warning: seibro_repo_merge_failed: {exc} (existing REPO history kept)")
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
