#!/usr/bin/env bash
# Daily data update: refresh FREESIS DB, then rebuild data/fundflow.json.
# Used both for local scheduling (cron/launchd) and GitHub Actions.
#
# Usage:
#   scripts/update.sh [BOK_SEED_URL]
# The seed URL defaults to the stable BOK list page; recent posts are then
# discovered via the BOK RSS feed, so no per-post nttId is required.
set -euo pipefail
cd "$(dirname "$0")/.."

BOK_URL="${1:-https://www.bok.or.kr/portal/bbs/P0002018/list.do?menuNo=200366}"

echo "[1/2] FREESIS 누적 수집 -> data/freesis_db.json"
# Non-fatal: if FREESIS is unreachable, keep the last good DB and still rebuild.
python3 scripts/freesis_final_4.py || echo "warning: FREESIS step failed; using existing data/freesis_db.json"

echo "[2/2] BOK + freesis_db + SEIBro -> data/fundflow.json"
python3 scripts/fetch_bok_market_indicator.py "$BOK_URL" --write-web-data data/fundflow.json

echo "Done: data/fundflow.json updated."
