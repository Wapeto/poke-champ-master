"""
Scraper for Game8's Pokemon Champions wiki.
Uses requests + BeautifulSoup (server-side rendered content).
"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup, Tag

from .utils import empty_evs, normalize_stat, save_json, slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://game8.co"
GAME_PATH = "/games/Pokemon-Champions"
GAME_URL = BASE_URL + GAME_PATH
REQUEST_DELAY = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TIER_ALT_MAP = {
    "S Tier": "S", "A+ Tier": "A+", "A Tier": "A",
    "B Tier": "B", "C Tier": "C", "D Tier": "D",
}

# H3 heading keywords → URL category
H3_CATEGORY: dict[str, str] = {
    "new and updated builds": "builds",
    "best builds for regulation": "builds",
    "best guides for team building": "teams",
    "recommended guides": "tier_lists",
    "all moves by category": "moves",
    "all abilities": "abilities",
    "held items by type": "items",
}

MOVE_CATEGORIES = frozenset({"Physical", "Special", "Status"})


# ─── HTTP ────────────────────────────────────────────────────────────────────

def _fetch(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    time.sleep(REQUEST_DELAY)
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


def _wrapper(soup: BeautifulSoup) -> Tag:
    return soup.find("div", class_="archive-style-wrapper") or soup.find("body") or soup


def _next_table(element: Tag) -> Optional[Tag]:
    sib = element.find_next_sibling()
    while sib and sib.name not in ("h2", "h3", "h4"):
        if sib.name == "table":
            return sib
        if hasattr(sib, "find"):
            t = sib.find("table")
            if t:
                return t
        sib = sib.find_next_sibling()
    return None


# ─── Hub page ────────────────────────────────────────────────────────────────

def scrape_hub(session: requests.Session) -> dict[str, list[str]]:
    soup = _fetch(GAME_URL, session)
    if not soup:
        return {}

    wrapper = _wrapper(soup)
    urls: dict[str, list[str]] = {k: [] for k in set(H3_CATEGORY.values())}
    current_cat: Optional[str] = None

    for el in wrapper.find_all(True):
        if el.name == "h3" and "a-header--3" in el.get("class", []):
            text = el.get_text(strip=True).lower()
            current_cat = next((cat for kw, cat in H3_CATEGORY.items() if kw in text), None)

        elif el.name == "a" and current_cat:
            href = el.get("href", "")
            archive_id = href.split("/archives/")[-1] if "/archives/" in href else ""
            if archive_id.isdigit():
                full = BASE_URL + href if href.startswith("/") else href
                if full not in urls[current_cat]:
                    urls[current_cat].append(full)

    # Ensure critical list pages are always included
    _add_default(urls, "tier_lists", f"{BASE_URL}{GAME_PATH}/archives/592465")  # singles
    _add_default(urls, "moves", f"{BASE_URL}{GAME_PATH}/archives/590397")
    _add_default(urls, "abilities", f"{BASE_URL}{GAME_PATH}/archives/590403")
    _add_default(urls, "items", f"{BASE_URL}{GAME_PATH}/archives/588871")
    return urls


def _add_default(d: dict[str, list[str]], key: str, url: str) -> None:
    if url not in d[key]:
        d[key].append(url)


# ─── Tier list ───────────────────────────────────────────────────────────────

def scrape_tier_list(url: str, session: requests.Session) -> list[dict[str, Any]]:
    soup = _fetch(url, session)
    if not soup:
        return []

    wrapper = _wrapper(soup)
    results: list[dict[str, Any]] = []
    detail_map: dict[str, dict] = {}   # name → enriched details from explanation tables

    # ── Visual tier tables (image-based, one row per tier) ──
    for table in wrapper.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        first_cells = rows[0].find_all(["td", "th"])
        if len(first_cells) < 2:
            continue

        # Identify as tier table: first cell has an img whose alt is in TIER_ALT_MAP
        first_imgs = first_cells[0].find_all("img")
        if not first_imgs or first_imgs[0].get("alt", "") not in TIER_ALT_MAP:
            continue

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            tier_imgs = cells[0].find_all("img")
            if not tier_imgs:
                continue
            tier = TIER_ALT_MAP.get(tier_imgs[0].get("alt", ""))
            if not tier:
                continue

            poke_cell = cells[1]
            poke_imgs = poke_cell.find_all("img")
            poke_links = poke_cell.find_all("a", href=True)

            for i, img in enumerate(poke_imgs):
                name = img.get("alt", "").strip()
                if not name:
                    continue
                entry: dict[str, Any] = {"name": name, "tier": tier, "types": [], "base_stats": {}, "abilities": []}
                if i < len(poke_links):
                    href = poke_links[i]["href"]
                    entry["build_url"] = href if href.startswith("http") else BASE_URL + href
                results.append(entry)

    # ── Detailed explanation tables (S/A+/A tiers only, text-based) ──
    for h2 in wrapper.find_all("h2", class_="a-header--2"):
        title = h2.get_text(strip=True)
        m = re.match(r"^([SABCD][+\-]?)\s+Rank", title)
        if not m:
            continue
        tier = m.group(1).upper()

        table = _next_table(h2)
        if not table:
            continue

        rows = table.find_all("tr")
        i = 1
        while i < len(rows):
            cells = rows[i].find_all(["td", "th"])
            if len(cells) == 2:
                name_cell, info_cell = cells
                imgs = name_cell.find_all("img")
                if not imgs:
                    i += 1
                    continue

                name = imgs[0].get("alt", "").strip()
                types = [
                    img.get("alt", "").replace("Pokemon ", "").replace(" Type Icon", "")
                    for img in imgs[1:]
                    if "Type Icon" in img.get("alt", "") and "Physical" not in img.get("alt", "")
                ]
                link = name_cell.find("a", href=True)
                build_url = None
                if link:
                    href = link["href"]
                    build_url = href if href.startswith("http") else BASE_URL + href

                info_text = info_cell.get_text(strip=True)
                stats_m = re.search(r"Base Stats[:\s]*(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)", info_text)
                base_stats = {}
                if stats_m:
                    vals = [int(x) for x in stats_m.groups()]
                    base_stats = {k: v for k, v in zip(["hp", "atk", "def", "spa", "spd", "spe"], vals)}

                abil_m = re.search(r"Ability:(.*?)(?:Base Stats|$)", info_text)
                abilities = [a.strip() for a in abil_m.group(1).split("/")] if abil_m else []

                detail_map[name] = {
                    "types": types, "base_stats": base_stats,
                    "abilities": abilities, "build_url": build_url,
                }
            i += 1

    # Merge details into results
    for entry in results:
        detail = detail_map.get(entry["name"], {})
        entry["types"] = detail.get("types") or entry["types"]
        entry["base_stats"] = detail.get("base_stats") or entry["base_stats"]
        entry["abilities"] = detail.get("abilities") or entry["abilities"]
        if detail.get("build_url") and not entry.get("build_url"):
            entry["build_url"] = detail["build_url"]

    return results


# ─── Build page ──────────────────────────────────────────────────────────────

def _parse_move_cell(cell: Tag) -> Optional[dict[str, str]]:
    name = cell.get_text(strip=True)
    if not name:
        return None
    move_type = ""
    move_cat = ""
    for img in cell.find_all("img"):
        alt = img.get("alt", "")
        if "Type Icon" not in alt:
            continue
        label = alt.replace("Pokemon ", "").replace(" Type Icon", "")
        if label in MOVE_CATEGORIES:
            move_cat = label
        else:
            move_type = label
    return {"name": name, "type": move_type, "category": move_cat}


def _is_build_table(table: Tag) -> bool:
    rows = table.find_all("tr")
    if len(rows) < 7:
        return False
    r0 = rows[0].find_all(["td", "th"])
    if len(r0) < 3:
        return False
    if r0[1].get_text(strip=True) != "Nature":
        return False
    r1 = rows[1].find_all(["td", "th"])
    return bool(r1) and "Ability" in r1[0].get_text(strip=True)


def _parse_build_table(table: Tag) -> dict[str, Any]:
    rows = table.find_all("tr")

    # Row 0: Pokemon name + Nature
    r0 = rows[0].find_all(["td", "th"])
    name_imgs = r0[0].find_all("img") if r0 else []
    pokemon_name = name_imgs[0].get("alt", "") if name_imgs else r0[0].get_text(strip=True) if r0 else ""

    nature_raw = r0[2].get_text(strip=True) if len(r0) > 2 else ""
    nature = re.match(r"(\w+)\(", nature_raw)
    nature = nature.group(1) if nature else nature_raw

    # Row 1: Ability
    r1 = rows[1].find_all(["td", "th"])
    ability = r1[1].get_text(strip=True) if len(r1) > 1 else ""

    # Row 2: Held Item
    r2 = rows[2].find_all(["td", "th"])
    held_item = r2[1].get_text(strip=True) if len(r2) > 1 else ""

    # Row 3/4/5: Stats & EVs
    r3 = rows[3].find_all(["td", "th"])
    stat_headers = [c.get_text(strip=True) for c in r3]

    r4 = rows[4].find_all(["td", "th"]) if len(rows) > 4 else []
    r5 = rows[5].find_all(["td", "th"]) if len(rows) > 5 else []

    final_stats: dict[str, int] = {}
    ev_spread = empty_evs()
    for i, h in enumerate(stat_headers):
        key = normalize_stat(h)
        if not key:
            continue
        if i < len(r4):
            v = r4[i].get_text(strip=True)
            if v.isdigit():
                final_stats[key] = int(v)
        if i < len(r5):
            v = r5[i].get_text(strip=True)
            ev_spread[key] = int(v) if v.isdigit() else 0

    # Rows 7 and 14: moves (2 per row, at cell positions 0 and 11)
    moves: list[dict[str, str]] = []
    for row_idx in (7, 14):
        if row_idx >= len(rows):
            break
        cells = rows[row_idx].find_all(["td", "th"])
        for pos in (0, 11):
            if pos < len(cells):
                move = _parse_move_cell(cells[pos])
                if move:
                    moves.append(move)

    return {
        "pokemon": pokemon_name,
        "nature": nature,
        "ability": ability,
        "held_item": held_item,
        "final_stats": final_stats,
        "ev_spread": ev_spread,
        "moves": moves,
    }


def scrape_build_page(url: str, session: requests.Session) -> dict[str, Any]:
    soup = _fetch(url, session)
    if not soup:
        return {}

    wrapper = _wrapper(soup)

    h1 = soup.find("h1", class_="p-archiveHeader__title") or soup.find("h1")
    page_title = h1.get_text(strip=True) if h1 else ""
    pokemon_name = re.sub(
        r"\s*(Moveset|Best Build|Build Guide|and Best Builds).*", "", page_title, flags=re.IGNORECASE
    ).strip()

    # Base stats from the first non-build stat table (Stat | Value rows)
    base_stats: dict[str, int] = {}
    types: list[str] = []
    for table in wrapper.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        r0 = rows[0].find_all(["td", "th"])
        r1 = rows[1].find_all(["td", "th"])
        if not r1 or r1[0].get_text(strip=True) != "Stat":
            continue
        # This is the Stat|Value table
        for row in rows[2:]:
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = normalize_stat(cells[0].get_text(strip=True))
                val = cells[1].get_text(strip=True)
                if key and val.isdigit():
                    base_stats[key] = int(val)
        # Types from header row of this table
        name_cell_imgs = r0[0].find_all("img") if r0 else []
        types = [
            img.get("alt", "").replace("Pokemon ", "").replace(" Type Icon", "")
            for img in name_cell_imgs
            if "Type Icon" in img.get("alt", "") and "Physical" not in img.get("alt", "")
        ]
        break

    # All build tables
    builds: list[dict] = []
    for table in wrapper.find_all("table"):
        if _is_build_table(table):
            builds.append(_parse_build_table(table))

    # Counters table
    counters: list[dict] = []
    for h in wrapper.find_all(["h2", "h3"]):
        if "counter" in h.get_text(strip=True).lower():
            t = _next_table(h)
            if t:
                for row in t.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        poke_imgs = cells[1].find_all("img")
                        counters = [img.get("alt", "") for img in poke_imgs if img.get("alt", "")]
            break

    # Last-resort name from the build table itself
    if not pokemon_name and builds:
        pokemon_name = builds[0].get("pokemon", "")

    return {
        "source_url": url,
        "name": pokemon_name,
        "types": types,
        "base_stats": base_stats,
        "builds": builds,
        "counters": counters,
    }


# ─── Team page ───────────────────────────────────────────────────────────────

def scrape_team_page(url: str, session: requests.Session) -> dict[str, Any]:
    soup = _fetch(url, session)
    if not soup:
        return {}

    wrapper = _wrapper(soup)
    h1 = soup.find("h1", class_="p-archiveHeader__title") or soup.find("h1")
    name = (h1.get_text(strip=True) if h1 else "") or url.split("/")[-1]

    # Strategy: first paragraph with >80 chars
    strategy = None
    for p in wrapper.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 80:
            strategy = text
            break

    members: list[dict] = []
    for table in wrapper.find_all("table"):
        if _is_build_table(table):
            members.append(_parse_build_table(table))

    return {
        "source_url": url,
        "name": name,
        "strategy": strategy,
        "members": members,
    }


# ─── Moves list ──────────────────────────────────────────────────────────────

def scrape_moves_list(url: str, session: requests.Session) -> list[dict[str, str]]:
    soup = _fetch(url, session)
    if not soup:
        return []

    wrapper = _wrapper(soup)
    moves: list[dict[str, str]] = []
    seen: set[str] = set()

    for table in wrapper.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
        if "Move" not in headers:
            continue

        i = 1
        while i < len(rows):
            cells = rows[i].find_all(["td", "th"])
            if not cells:
                i += 1
                continue

            move_name = cells[0].get_text(strip=True)
            if not move_name or move_name in seen:
                i += 1
                continue

            move: dict[str, str] = {"name": move_name}

            if len(cells) >= 2:
                type_imgs = cells[1].find_all("img")
                move["type"] = type_imgs[0].get("alt", "").replace(" Type Moves", "") if type_imgs else ""
            if len(cells) >= 3:
                cat_imgs = cells[2].find_all("img")
                move["category"] = cat_imgs[0].get("alt", "").replace(" Type Moves", "") if cat_imgs else ""
            if len(cells) >= 4:
                move["power"] = cells[3].get_text(strip=True)
            if len(cells) >= 5:
                move["accuracy"] = cells[4].get_text(strip=True)
            if len(cells) >= 6:
                move["pp"] = cells[5].get_text(strip=True)

            # Effect is in the NEXT row as a single spanning cell
            if i + 1 < len(rows):
                next_cells = rows[i + 1].find_all(["td", "th"])
                if len(next_cells) == 1:
                    move["effect"] = next_cells[0].get_text(strip=True)
                    i += 2
                    seen.add(move_name)
                    moves.append(move)
                    continue

            seen.add(move_name)
            moves.append(move)
            i += 1

    return moves


# ─── Abilities list ───────────────────────────────────────────────────────────

def scrape_abilities_list(url: str, session: requests.Session) -> list[dict[str, str]]:
    soup = _fetch(url, session)
    if not soup:
        return []

    wrapper = _wrapper(soup)
    abilities: list[dict[str, str]] = []
    seen: set[str] = set()

    for table in wrapper.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
        if "Ability" not in headers:
            continue
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            name = cells[0].get_text(strip=True)
            effect = cells[1].get_text(strip=True)
            if name and name not in seen:
                abilities.append({"name": name, "effect": effect})
                seen.add(name)

    return abilities


# ─── Items list ──────────────────────────────────────────────────────────────

def scrape_items_list(url: str, session: requests.Session) -> list[dict[str, str]]:
    soup = _fetch(url, session)
    if not soup:
        return []

    wrapper = _wrapper(soup)
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for table in wrapper.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
        if "Item" not in headers:
            continue
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            name = cells[0].get_text(strip=True)
            if not name or name in seen:
                continue
            item: dict[str, str] = {"name": name}
            if len(cells) >= 2:
                item["type"] = cells[1].get_text(strip=True)
            if len(cells) >= 3:
                item["effect"] = cells[2].get_text(strip=True)
            items.append(item)
            seen.add(name)

    return items


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def run(data_dir: Path) -> None:
    game8_dir = data_dir / "game8"
    builds_dir = game8_dir / "builds"
    teams_dir = game8_dir / "teams"
    for d in (game8_dir, builds_dir, teams_dir):
        d.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    print("  Discovering URLs...")
    hub = scrape_hub(session)
    save_json(hub, game8_dir / "hub_urls.json")
    for cat, lst in hub.items():
        print(f"    {cat}: {len(lst)} URLs")

    # Tier list (singles only — archive 592465)
    tier_url = next((u for u in hub.get("tier_lists", []) if "592465" in u), hub.get("tier_lists", [None])[0])
    if tier_url:
        print(f"  Scraping singles tier list...")
        tier = scrape_tier_list(tier_url, session)
        save_json(tier, game8_dir / "tier_list.json")
        print(f"    → {len(tier)} Pokemon across all tiers")

    # Builds
    build_urls = hub.get("builds", [])
    print(f"  Scraping {len(build_urls)} build pages...")
    all_builds: list[dict] = []
    for url in build_urls:
        data = scrape_build_page(url, session)
        if data.get("name"):
            fname = slugify(data["name"]) + ".json"
            save_json(data, builds_dir / fname)
            all_builds.append(data)
            print(f"    ✓ {data['name']} ({len(data.get('builds', []))} builds, {sum(len(b.get('moves',[])) for b in data.get('builds',[]))} moves)")
        else:
            print(f"    ✗ parse failed: {url}")
    save_json(all_builds, game8_dir / "all_builds.json")

    # Teams
    team_urls = hub.get("teams", [])
    print(f"  Scraping {len(team_urls)} team pages...")
    all_teams: list[dict] = []
    for url in team_urls:
        data = scrape_team_page(url, session)
        if data.get("name"):
            fname = slugify(data["name"]) + ".json"
            save_json(data, teams_dir / fname)
            all_teams.append(data)
            print(f"    ✓ {data['name']} ({len(data.get('members', []))} members)")
        else:
            print(f"    ✗ parse failed: {url}")
    save_json(all_teams, game8_dir / "all_teams.json")

    # Moves
    move_urls = hub.get("moves", [])
    if move_urls:
        print("  Scraping moves list...")
        moves = scrape_moves_list(move_urls[0], session)
        save_json(moves, game8_dir / "moves.json")
        print(f"    → {len(moves)} moves")

    # Abilities
    abil_urls = hub.get("abilities", [])
    if abil_urls:
        print("  Scraping abilities list...")
        abilities = scrape_abilities_list(abil_urls[0], session)
        save_json(abilities, game8_dir / "abilities.json")
        print(f"    → {len(abilities)} abilities")

    # Items
    item_urls = hub.get("items", [])
    if item_urls:
        print("  Scraping items list...")
        items = scrape_items_list(item_urls[0], session)
        save_json(items, game8_dir / "items.json")
        print(f"    → {len(items)} items")

    print("  Game8 scraping complete.")
