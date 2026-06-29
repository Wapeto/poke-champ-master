"""
Build French translation dictionaries for every data label in the roster.

Pulls authoritative French names from PokeAPI (free, no key) for types, Pokémon,
moves, items, abilities and natures actually present in data/roster.json, and
writes them to data/i18n/fr.json as:

    {"pokemon": {en: fr}, "types": {}, "moves": {}, "items": {}, "abilities": {},
     "natures": {}}

Display-only: the app's canonical keys, logic and API payloads stay English; the
frontend just looks up these maps. Raw PokeAPI name lookups are cached under
data/i18n/_fr_cache.json so reruns are cheap. Unmatched labels are reported and
fall back to English at render time.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests

from .pokeapi_enrich import candidate_slugs

logger = logging.getLogger(__name__)

API = "https://pokeapi.co/api/v2/"
HEADERS = {"User-Agent": "poke-champ-master/1.0 (fr translations)"}
REQUEST_DELAY = 0.04

REGION_FR = {
    "alolan": "d'Alola",
    "galarian": "de Galar",
    "hisuian": "de Hisui",
    "paldean": "de Paldea",
}

# Hand-picked PokeAPI slugs where our slugify misses (extend as reported).
MOVE_SLUG_OVERRIDES: dict[str, str] = {}
ITEM_SLUG_OVERRIDES: dict[str, str] = {}
ABILITY_SLUG_OVERRIDES: dict[str, str] = {}


def _slug(name: str) -> str:
    s = name.lower().strip()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"[.:%]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def _fr_from_names(payload: dict) -> Optional[str]:
    for entry in payload.get("names", []):
        if entry.get("language", {}).get("name") == "fr":
            return entry.get("name")
    return None


class Translator:
    def __init__(self, session: requests.Session, cache: dict):
        self.s = session
        self.cache = cache  # {f"{kind}:{slug}": fr_name or None}

    def _get(self, url: str) -> Optional[dict]:
        try:
            time.sleep(REQUEST_DELAY)
            r = self.s.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.warning("PokeAPI fetch failed for %s: %s", url, exc)
            return None

    def fr_for(self, kind: str, slug: str) -> Optional[str]:
        key = f"{kind}:{slug}"
        if key in self.cache:
            return self.cache[key]
        payload = self._get(f"{API}{kind}/{slug}")
        fr = _fr_from_names(payload) if payload else None
        self.cache[key] = fr
        return fr

    def species_fr(self, en_name: str, slug_hint: Optional[str]) -> Optional[str]:
        """French base-species name for a roster Pokémon (any form)."""
        slugs = ([slug_hint] if slug_hint else []) + candidate_slugs(en_name)
        for slug in slugs:
            if not slug:
                continue
            key = f"species:{slug}"
            if key in self.cache:
                if self.cache[key]:
                    return self.cache[key]
                continue
            poke = self._get(f"{API}pokemon/{slug}")
            species_url = (poke or {}).get("species", {}).get("url")
            if not species_url:
                self.cache[key] = None
                continue
            species = self._get(species_url)
            fr = _fr_from_names(species) if species else None
            self.cache[key] = fr
            if fr:
                return fr
        return None


def _decorate(en_name: str, species_fr: str) -> str:
    """Build the French display name for a form from its base-species French name."""
    low = en_name.lower().strip()
    if low.startswith("mega "):
        variant = ""
        if low.endswith((" x", " y")):
            variant = " " + low[-1].upper()
        return f"Méga-{species_fr}{variant}"
    for prefix, fr_suffix in REGION_FR.items():
        if low.startswith(prefix + "n ") or low.startswith(prefix + " "):
            return f"{species_fr} {fr_suffix}"
    return species_fr


def _collect(roster: dict) -> dict[str, set]:
    names: set[str] = set()
    types: set[str] = set()
    moves: set[str] = set()
    items: set[str] = set()
    abilities: set[str] = set()
    natures: set[str] = set()
    for p in roster.values():
        names.add(p["name"])
        types.update(p.get("types", []))
        abilities.update(p.get("abilities", []))
        for b in p.get("builds", []):
            if b.get("held_item"):
                items.add(b["held_item"])
            if b.get("nature"):
                natures.add(b["nature"])
            if b.get("ability"):
                abilities.add(b["ability"])
            for m in b.get("moves", []):
                if m.get("name"):
                    moves.add(m["name"])
                if m.get("type"):
                    types.add(m["type"])
    return {"names": names, "types": types, "moves": moves,
            "items": items, "abilities": abilities, "natures": natures}


def run(data_dir: Path) -> dict:
    roster_path = data_dir / "roster.json"
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    enrichment = json.loads(
        (data_dir / "pokeapi" / "enrichment.json").read_text(encoding="utf-8")
    ) if (data_dir / "pokeapi" / "enrichment.json").exists() else {}

    out_dir = data_dir / "i18n"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / "_fr_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    labels = _collect(roster)
    session = requests.Session()
    tr = Translator(session, cache)

    result = {k: {} for k in ("pokemon", "types", "moves", "items", "abilities", "natures")}
    unmatched: dict[str, list[str]] = {}

    def translate(category: str, kind: str, en_values, overrides):
        miss = []
        for en in sorted(en_values):
            slug = overrides.get(en.lower(), _slug(en))
            fr = tr.fr_for(kind, slug)
            if fr:
                result[category][en] = fr
            else:
                miss.append(en)
        if miss:
            unmatched[category] = miss

    print("  types…");     translate("types", "type", labels["types"], {})
    print("  moves…");     translate("moves", "move", labels["moves"], MOVE_SLUG_OVERRIDES)
    print("  items…");     translate("items", "item", labels["items"], ITEM_SLUG_OVERRIDES)
    print("  abilities…"); translate("abilities", "ability", labels["abilities"], ABILITY_SLUG_OVERRIDES)
    print("  natures…");   translate("natures", "nature", labels["natures"], {})

    print("  pokemon…")
    miss = []
    for en in sorted(labels["names"]):
        slug_hint = enrichment.get(en.lower(), {}).get("pokeapi_slug")
        species_fr = tr.species_fr(en, slug_hint)
        if species_fr:
            result["pokemon"][en] = _decorate(en, species_fr)
        else:
            miss.append(en)
    if miss:
        unmatched["pokemon"] = miss

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "fr.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for cat in result:
        print(f"  {cat}: {len(result[cat])} translated"
              + (f", {len(unmatched.get(cat, []))} unmatched" if unmatched.get(cat) else ""))
    for cat, miss in unmatched.items():
        print(f"    [{cat}] unmatched: {', '.join(miss)}")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run(Path(__file__).parent.parent / "data")
