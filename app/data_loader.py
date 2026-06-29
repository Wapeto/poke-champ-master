"""Load and merge scraped JSON data into a unified Pokemon roster."""

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data" / "game8"

TIER_ORDER = {"S": 6, "A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}

_REGION_PREFIXES = ("alolan ", "galarian ", "hisuian ", "paldean ")


def _base_form_key(name: str) -> str | None:
    """Roster key of a form's base Pokemon, e.g. 'Mega Charizard Y' -> 'charizard'."""
    low = name.lower().strip()
    if low.startswith("mega "):
        rest = low[5:]
        if rest.endswith((" x", " y")):
            rest = rest[:-2]
        return rest.strip() or None
    for prefix in _REGION_PREFIXES:
        if low.startswith(prefix):
            return low[len(prefix):].strip() or None
    return None


def _load(path: Path) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_enrichment() -> dict[str, dict]:
    """PokeAPI enrichment: {name_lower: {types, image_url, pokeapi_slug}}."""
    return _load(DATA_DIR.parent / "pokeapi" / "enrichment.json") or {}


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
            "counters": [],
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
                    "counters": [],
                }

            poke = roster[key]
            if data.get("types"):
                poke["types"] = data["types"]
            if data.get("base_stats"):
                poke["base_stats"] = data["base_stats"]
            if data.get("builds"):
                poke["builds"] = data["builds"]
            if data.get("counters"):
                poke["counters"] = data["counters"]
            if not poke["build_url"] and data.get("source_url"):
                poke["build_url"] = data["source_url"]

    # ── Form fallback: megas/regionals inherit the base form's builds ──
    # Game8 hosts builds under the base name, so forms have no build of their own.
    for key, poke in roster.items():
        if poke["builds"]:
            continue
        base_key = _base_form_key(poke["name"])
        base = roster.get(base_key) if base_key else None
        if base and base.get("builds"):
            poke["builds"] = base["builds"]
            if not poke["counters"]:
                poke["counters"] = base["counters"]
            if not poke["base_stats"]:
                poke["base_stats"] = base["base_stats"]

    # ── PokeAPI enrichment: fill missing types, attach official artwork ──
    enrichment = _load_enrichment()
    for key, poke in roster.items():
        extra = enrichment.get(key)
        if not extra:
            poke.setdefault("image_url", None)
            continue
        if not poke["types"] and extra.get("types"):
            poke["types"] = extra["types"]
        poke["image_url"] = extra.get("image_url")

    # Drop scrape artifacts that never resolved to a real Pokemon (no types).
    return {k: p for k, p in roster.items() if p["types"]}


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
