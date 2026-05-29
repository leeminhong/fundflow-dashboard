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
# BOK는 날짜마다 엑셀 첨부를 내려받아 파싱하므로 페이지 수가 곧 소요시간이다.
# 누적 JSON에 머지하므로 최신 영업일 1건만 받으면 된다(과거치는 보존).
# SEIBro는 페이지를 1회만 로드해 테이블을 읽으므로 limit이 커도 느리지 않다.
# forward-fill로 갭을 메울 수 있도록 여유 있게 둔다.
python3 scripts/fetch_bok_market_indicator.py "$BOK_URL" \
  --write-web-data data/fundflow.json \
  --days 1 \
  --seibro-repo-limit 10

echo "Done: data/fundflow.json updated."
