#!/usr/bin/env python3
"""
Precompute the fully-merged roster into data/roster.json.

Run after any change to the raw data under data/ (run_scraper.py does this
automatically at the end of a scrape). Committing the result lets the web app —
and every serverless cold start — load one JSON instead of merging the tree.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.data_loader import ROSTER_CACHE, precompute_roster


def main() -> None:
    roster = precompute_roster()
    print(f"Wrote {len(roster)} Pokemon to {ROSTER_CACHE} "
          f"({ROSTER_CACHE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
