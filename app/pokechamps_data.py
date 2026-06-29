"""
Load the pokechamps.com (DotGG) datasets and expose them keyed for the app:
Pokémon descriptions + official Champions artwork, held-item images, and move
metadata (type / power / damage class). Scraped by scrapers/pokechamps_scraper.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PC_DIR = Path(__file__).parent.parent / "data" / "pokechamps"

# Game8 roster name (lower) → DotGG `name` for forms spelled differently.
_NAME_OVERRIDES = {
    "heat rotom": "rotom (heat)",
    "wash rotom": "rotom (wash)",
    "frost rotom": "rotom (frost)",
    "mow rotom": "rotom (mow)",
    "aegislash": "aegislash (shield forme)",
    "alcremie": "alcremie (vanilla cream strawberry sweet)",
    "castform": "castform (normal)",
    "eternal flower floette": "eternal floette",
    "mega floette": "floette",
    "maushold": "maushold (family of four)",
    "mega meowstic (male)": "mega meowstic",
    "midday form lycanroc": "lycanroc (midday form)",
    "mimikyu": "mimikyu (disguised form)",
    "palafin": "palafin (zero form)",
    "sinistcha": "sinistcha (unremarkable form)",
    "vivillon": "vivillon (meadow pattern)",
}

_DAMAGE_CLASS = {"1": "Status", "2": "Physical", "3": "Special"}


def _load(name: str) -> list[dict]:
    path = PC_DIR / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def load_pokemon_index() -> dict[str, dict[str, Any]]:
    """Roster-name-lower → {description, art_url, types, base_stats} from pokechamps."""
    rows = _load("alt_pokemon.json")
    by_name = {r["name"].strip().lower(): r for r in rows if r.get("name")}

    def lookup(key: str) -> dict | None:
        target = _NAME_OVERRIDES.get(key, key)
        return by_name.get(target)

    index: dict[str, dict[str, Any]] = {}
    for key in {r["name"].strip().lower() for r in rows} | set(_NAME_OVERRIDES):
        row = lookup(key)
        if not row:
            continue
        types = [t for t in (row.get("type1"), row.get("type2")) if t]
        stats = {k: int(row[k]) for k in ("hp", "atk", "def", "spa", "spd", "spe") if row.get(k)}
        index[key] = {
            "description": row.get("description") or None,
            "art_url": row.get("art_url") or None,
            "types": types,
            "base_stats": stats,
        }
    return index


def load_item_images() -> dict[str, str]:
    """Item-name-lower → image URL."""
    return {
        r["name"].strip().lower(): r["image_url"]
        for r in _load("alt_items.json")
        if r.get("name") and r.get("image_url")
    }


def load_move_index() -> dict[str, dict[str, Any]]:
    """Move-name-lower → {type, power, accuracy, pp, category, priority}."""
    index: dict[str, dict[str, Any]] = {}
    for r in _load("alt_moves.json"):
        name = r.get("name")
        if not name:
            continue
        index[name.strip().lower()] = {
            "type": r.get("type") or "",
            "power": r.get("power"),
            "accuracy": r.get("accuracy"),
            "pp": r.get("pp"),
            "priority": r.get("priority"),
            "category": _DAMAGE_CLASS.get(str(r.get("damage_class_id")), ""),
        }
    return index
