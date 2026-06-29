"""
Enrich the roster with authoritative types and official artwork from PokeAPI.

Game8 only exposes types for the S/A+/A explanation tables, so most of the
roster — and every Mega, which has no build page — ends up typeless. PokeAPI
(free, no key) has every form including megas and regionals, plus official
artwork sprites. We key off the Pokemon name, resolve it to a PokeAPI slug,
and cache the result so the web app can run fully offline afterwards.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

API = "https://pokeapi.co/api/v2/pokemon/"
HEADERS = {"User-Agent": "poke-champ-master/1.0 (data enrichment)"}
REQUEST_DELAY = 0.05  # PokeAPI has no hard rate limit but be polite

REGION_SUFFIX = {
    "alolan": "alola",
    "galarian": "galar",
    "hisuian": "hisui",
    "paldean": "paldea",
}

# Names PokeAPI spells differently from Game8, or that need a hand-picked slug.
SLUG_OVERRIDES = {
    "mr. mime": "mr-mime",
    "mr. rime": "mr-rime",
    "mime jr.": "mime-jr",
    "type: null": "type-null",
    "farfetch'd": "farfetchd",
    "sirfetch'd": "sirfetchd",
    "nidoran♀": "nidoran-f",
    "nidoran♂": "nidoran-m",
    "flabébé": "flabebe",
    "porygon-z": "porygon-z",
    "ho-oh": "ho-oh",
    "jangmo-o": "jangmo-o",
    "hakamo-o": "hakamo-o",
    "kommo-o": "kommo-o",
    "wo-chien": "wo-chien",
    "chien-pao": "chien-pao",
    "ting-lu": "ting-lu",
    "chi-yu": "chi-yu",
    # Alt forms PokeAPI names differently than Game8
    "aegislash": "aegislash-shield",
    "aegislash (shield forme)": "aegislash-shield",
    "basculegion (female)": "basculegion-female",
    "basculegion (male)": "basculegion-male",
    "eternal flower floette": "floette-eternal",
    "frost rotom": "rotom-frost",
    "heat rotom": "rotom-heat",
    "mow rotom": "rotom-mow",
    "wash rotom": "rotom-wash",
    "maushold": "maushold-family-of-four",
    "meowstic (female)": "meowstic-female",
    "mega meowstic (male)": "meowstic-male",
    "midday form lycanroc": "lycanroc-midday",
    "mimikyu": "mimikyu-disguised",
    "palafin": "palafin-zero",
    "paldean tauros (aqua breed)": "tauros-paldea-aqua-breed",
    "paldean tauros (blaze breed)": "tauros-paldea-blaze-breed",
    "pyroar": "pyroar-male",
}

# Roster entries that are scrape artifacts, not Pokemon. Skip enrichment.
JUNK_NAMES = frozenset({"pokemon champions best teams"})


def _base_slug(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace to hyphens."""
    s = name.lower().strip()
    s = s.replace("é", "e").replace("♀", "-f").replace("♂", "-m")
    s = re.sub(r"['.:]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def _dedupe(slugs: list[str]) -> list[str]:
    seen: set[str] = set()
    return [s for s in slugs if s and not (s in seen or seen.add(s))]


def candidate_slugs(name: str) -> list[str]:
    """Ordered, deduplicated PokeAPI slug candidates for a roster name."""
    key = name.lower().strip()
    if key in JUNK_NAMES:
        return []
    if key in SLUG_OVERRIDES:
        return [SLUG_OVERRIDES[key]]

    words = name.strip().split()
    if not words:
        return []

    lead = words[0].lower()

    # Mega <name> [X|Y] -> <name>-mega[-x|-y]
    if lead == "mega":
        rest = words[1:]
        variant = ""
        if rest and rest[-1].upper() in ("X", "Y"):
            variant = "-" + rest[-1].lower()
            rest = rest[:-1]
        base = _base_slug(" ".join(rest))
        return _dedupe([f"{base}-mega{variant}", f"{base}-mega"])

    # Regional prefix (Alolan / Galarian / Hisuian / Paldean) <name>
    if lead in REGION_SUFFIX:
        base = _base_slug(" ".join(words[1:]))
        return _dedupe([f"{base}-{REGION_SUFFIX[lead]}", base])

    # Plain name, plus a hyphen-joined fallback for multi-word forms
    return _dedupe([_base_slug(name), _base_slug(words[0])])


def _fetch(slug: str, session: requests.Session) -> Optional[dict]:
    try:
        resp = session.get(API + slug, headers=HEADERS, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("PokeAPI fetch failed for %s: %s", slug, exc)
        return None


def _extract(raw: dict) -> dict[str, Any]:
    types = [t["type"]["name"].capitalize() for t in raw.get("types", [])]
    sprites = raw.get("sprites", {})
    art = (
        sprites.get("other", {}).get("official-artwork", {}).get("front_default")
        or sprites.get("front_default")
    )
    return {"types": types, "image_url": art, "pokeapi_slug": raw.get("name")}


def enrich_name(name: str, session: requests.Session) -> Optional[dict[str, Any]]:
    """Resolve one roster name to {types, image_url, pokeapi_slug} or None."""
    for slug in candidate_slugs(name):
        time.sleep(REQUEST_DELAY)
        raw = _fetch(slug, session)
        if raw:
            return _extract(raw)
    return None


def run(data_dir: Path, names: list[str]) -> dict[str, dict]:
    """
    Enrich every roster name. Returns {name_lower: {types, image_url, pokeapi_slug}}
    and writes it to data/pokeapi/enrichment.json. Reuses cached entries on rerun.
    """
    out_dir = data_dir / "pokeapi"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / "enrichment.json"

    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    session = requests.Session()
    unmatched: list[str] = []

    for i, name in enumerate(names, 1):
        key = name.lower().strip()
        if key in cache and cache[key].get("types"):
            continue
        result = enrich_name(name, session)
        if result and result["types"]:
            cache[key] = result
            print(f"    [{i}/{len(names)}] ✓ {name} → {result['types']}")
        else:
            unmatched.append(name)
            print(f"    [{i}/{len(names)}] ✗ {name} (no PokeAPI match)")

    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Enriched {len(cache)} Pokemon, {len(unmatched)} unmatched.")
    if unmatched:
        print("  Unmatched:", ", ".join(unmatched))
    return cache
