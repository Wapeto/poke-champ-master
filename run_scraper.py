#!/usr/bin/env python3
"""
Pokemon Champions data scraper.

Usage:
    python run_scraper.py                    # scrape both sites
    python run_scraper.py --source game8     # Game8 only
    python run_scraper.py --source pokechamps  # Pokechamps only
    python run_scraper.py --data-dir ./out   # custom output directory

First-time setup:
    pip install -r requirements.txt
    playwright install chromium              # needed for pokechamps only
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Pokemon Champions data from Game8 and Pokechamps"
    )
    parser.add_argument(
        "--source",
        choices=["game8", "pokechamps", "all"],
        default="all",
        help="Which site to scrape (default: all)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help=f"Output directory for JSON files (default: {DATA_DIR})",
    )
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)

    if args.source in ("game8", "all"):
        print("\n" + "=" * 60)
        print("GAME8 — Pokemon Champions wiki")
        print("=" * 60)
        try:
            from scrapers.game8_scraper import run as run_game8
            run_game8(args.data_dir)
        except ImportError as e:
            print(f"  ERROR: {e}")
            print("  Install with: pip install requests beautifulsoup4 lxml")
            sys.exit(1)

    if args.source in ("pokechamps", "all"):
        print("\n" + "=" * 60)
        print("POKECHAMPS — pokechamps.com")
        print("=" * 60)
        try:
            from scrapers.pokechamps_scraper import run as run_pokechamps
            run_pokechamps(args.data_dir)
        except ImportError as e:
            print(f"  ERROR: {e}")
            print("  Install with: pip install playwright && playwright install chromium")
            sys.exit(1)

    # Enrich types + official artwork from PokeAPI (always — fixes typeless megas).
    print("\n" + "=" * 60)
    print("POKEAPI — types & official artwork enrichment")
    print("=" * 60)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from app.data_loader import build_roster, precompute_roster
        from scrapers.pokeapi_enrich import run as run_enrich
        names = sorted({p["name"] for p in build_roster().values()})
        run_enrich(args.data_dir, names)
        # Rebuild the precomputed roster now that enrichment is fresh.
        precompute_roster()
        print("  Rebuilt data/roster.json")
    except Exception as e:
        print(f"  ERROR: {e}")

    # French translation dictionaries (authoritative names from PokeAPI).
    print("\n" + "=" * 60)
    print("POKEAPI — French translations (data/i18n/fr.json)")
    print("=" * 60)
    try:
        from scrapers.translate_fr import run as run_translate
        run_translate(args.data_dir)
    except Exception as e:
        print(f"  ERROR: {e}")

    print(f"\nAll done. Data saved to: {args.data_dir.resolve()}")
    print("\nOutput structure:")
    for path in sorted(args.data_dir.rglob("*.json")):
        rel = path.relative_to(args.data_dir)
        size = path.stat().st_size
        print(f"  {rel}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
