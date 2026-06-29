"""
Scraper for pokechamps.com — the DotGG-network Pokémon Champions database.

The site is a WordPress front-end whose data is served by the DotGG content API
(`api.dotgg.gg/cgfw/getgacha?game=pokechamps&type=...`), NOT a Next.js SPA. This
gives clean, authoritative JSON for every Pokémon form, item, move and ability —
no headless browser or DOM scraping needed.

Artwork (webp) lives at:
    https://static.dotgg.gg/pokechamps/alt-pokemon/art/<identifier>.webp
    https://static.dotgg.gg/pokechamps/alt-item/<identifier>.webp
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests

from .utils import save_json

logger = logging.getLogger(__name__)

API = "https://api.dotgg.gg/cgfw/getgacha"
ART_BASE = "https://static.dotgg.gg/pokechamps/alt-pokemon/art"
ITEM_IMG_BASE = "https://static.dotgg.gg/pokechamps/alt-item"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}

DATASETS = ("alt_pokemon", "alt_items", "alt_moves", "alt_abilities")


def pokemon_art_url(identifier: str) -> str:
    return f"{ART_BASE}/{identifier}.webp"


def item_image_url(identifier: str) -> str:
    return f"{ITEM_IMG_BASE}/{identifier}.webp"


def _fetch(dataset: str, session: requests.Session) -> list[dict[str, Any]]:
    resp = session.get(
        API, params={"game": "pokechamps", "type": dataset, "cache": "16"},
        headers=HEADERS, timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def run(data_dir: Path) -> None:
    pc_dir = data_dir / "pokechamps"
    pc_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    for dataset in DATASETS:
        try:
            rows = _fetch(dataset, session)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", dataset, exc)
            print(f"    ✗ {dataset}: {exc}")
            continue

        if dataset == "alt_pokemon":
            for row in rows:
                row["art_url"] = pokemon_art_url(row.get("identifier", ""))
        elif dataset == "alt_items":
            for row in rows:
                row["image_url"] = item_image_url(row.get("identifier", ""))

        save_json(rows, pc_dir / f"{dataset}.json")
        print(f"    ✓ {dataset}: {len(rows)} entries")

    print("  Pokechamps (DotGG API) scraping complete.")
