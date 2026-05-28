#!/usr/bin/env bash
# Lint + unit tests for the fundflow pipeline.
# Run manually (`scripts/check.sh`) or automatically via the git pre-commit hook.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/2] pyflakes (undefined names / unused imports)"
python3 -m pyflakes \
  scripts/fundflow_pipeline/*.py \
  scripts/fetch_bok_market_indicator.py \
  scripts/freesis_final_4.py \
  tests/*.py

echo "[2/2] pytest"
python3 -m pytest tests/ -q

echo "All checks passed."
