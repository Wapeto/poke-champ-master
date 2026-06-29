"""Load and merge scraped JSON data into a unified Pokemon roster."""

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data" / "game8"

TIER_ORDER = {"S": 6, "A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}


def _load(path: Path) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def load_roster() -> dict[str, dict]:
    """Return {name_lower: pokemon_dict} merged from tier list + build pages."""
    roster: dict[str, dict] = {}

    # ── Tier list: base data for all Pokemon ──
    tier_list = _load(DATA_DIR / "tier_list.json") or []
    for entry in tier_list:
        name = entry.get("name", "").strip()
        if not name:
            continue
        key = name.lower()
        roster[key] = {
            "name": name,
            "tier": entry.get("tier", ""),
            "tier_score": TIER_ORDER.get(entry.get("tier", ""), 0),
            "types": entry.get("types", []),
            "base_stats": entry.get("base_stats", {}),
            "abilities": entry.get("abilities", []),
            "build_url": entry.get("build_url", ""),
            "builds": [],
        }

    # ── Build pages: add detailed build info ──
    builds_dir = DATA_DIR / "builds"
    if builds_dir.exists():
        for build_file in builds_dir.glob("*.json"):
            data = _load(build_file)
            if not data or not data.get("name"):
                continue
            name = data["name"].strip()
            key = name.lower()

            if key not in roster:
                roster[key] = {
                    "name": name,
                    "tier": "",
                    "tier_score": 0,
                    "types": [],
                    "base_stats": {},
                    "abilities": [],
                    "build_url": data.get("source_url", ""),
                    "builds": [],
                }

            poke = roster[key]
            if data.get("types"):
                poke["types"] = data["types"]
            if data.get("base_stats"):
                poke["base_stats"] = data["base_stats"]
            if data.get("builds"):
                poke["builds"] = data["builds"]
            if not poke["build_url"] and data.get("source_url"):
                poke["build_url"] = data["source_url"]

    return roster


def load_teams() -> list[dict]:
    """Load all scraped team compositions."""
    all_teams = _load(DATA_DIR / "all_teams.json") or []
    # Filter to teams with actual members
    return [t for t in all_teams if t.get("members")]


def load_moves() -> dict[str, dict]:
    """Return {move_name_lower: move_dict}."""
    moves_raw = _load(DATA_DIR / "moves.json") or []
    return {m["name"].lower(): m for m in moves_raw if m.get("name")}


def load_abilities() -> dict[str, dict]:
    """Return {ability_name_lower: ability_dict}."""
    raw = _load(DATA_DIR / "abilities.json") or []
    return {a["name"].lower(): a for a in raw if a.get("name")}


def load_items() -> dict[str, dict]:
    """Return {item_name_lower: item_dict}."""
    raw = _load(DATA_DIR / "items.json") or []
    return {i["name"].lower(): i for i in raw if i.get("name")}
