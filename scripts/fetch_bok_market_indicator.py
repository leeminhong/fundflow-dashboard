#!/usr/bin/env python3
"""Fetch and parse a Bank of Korea daily market-indicator attachment.

Thin entry point. The implementation lives in the ``fundflow_pipeline`` package
(see scripts/fundflow_pipeline/). This file is kept so existing run commands and
docs (``python3 scripts/fetch_bok_market_indicator.py ...``) keep working.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fundflow_pipeline.cli import main

if __name__ == "__main__":
    main()
