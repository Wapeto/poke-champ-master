"""
Scraper for pokechamps.com.
Uses Playwright because the site is a JavaScript-rendered SPA.

Install dependencies before running:
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import Browser, Page, async_playwright

from .utils import empty_evs, normalize_stat, save_json, slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://pokechamps.com"
NAV_DELAY = 2.5  # seconds to wait after navigation for JS to settle

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"

STAT_LABELS = [
    ("HP", "hp"), ("Attack", "atk"), ("Defense", "def"),
    ("Sp. Atk", "spa"), ("Sp. Def", "spd"), ("Speed", "spe"),
    ("Sp.Atk", "spa"), ("Sp.Def", "spd"),
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _go(page: Page, url: str) -> None:
    await page.goto(url, wait_until="networkidle", timeout=30_000)
    await asyncio.sleep(NAV_DELAY)


def _extract_next_data(html: str) -> Optional[dict]:
    """Pull JSON embedded by Next.js as __NEXT_DATA__."""
    m = re.search(r"<script id=\"__NEXT_DATA__\"[^>]*>({.+?})</script>", html, re.DOTALL)
    if not m:
        m = re.search(r"__NEXT_DATA__\s*=\s*({.+?})</script>", html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _page_props(next_data: dict) -> dict:
    return next_data.get("props", {}).get("pageProps", {})


def _parse_stats_from_text(text: str) -> dict[str, int]:
    stats: dict[str, int] = {}
    for label, key in STAT_LABELS:
        m = re.search(rf"{re.escape(label)}\D*?(\d+)", text, re.IGNORECASE)
        if m and key not in stats:
            stats[key] = int(m.group(1))
    return stats


# ─── Tier list ───────────────────────────────────────────────────────────────

async def scrape_tier_list(page: Page) -> list[dict[str, Any]]:
    # Try common slugs
    for path in ("/tier-list", "/tierlist", "/meta"):
        await _go(page, BASE_URL + path)
        if page.url != BASE_URL + "/" and "404" not in await page.title():
            break

    html = await page.content()

    # Try Next.js embedded data first
    nd = _extract_next_data(html)
    if nd:
        props = _page_props(nd)
        for key in ("tierList", "tier_list", "pokemon", "rankings"):
            if key in props and isinstance(props[key], list):
                return props[key]

    # DOM fallback
    results: list[dict[str, Any]] = []
    tier_sections = await page.query_selector_all("[class*='tier']")
    current_tier: Optional[str] = None

    for el in tier_sections:
        text = (await el.inner_text()).strip()
        m = re.match(r"^([SABCD][+\-]?)", text, re.IGNORECASE)
        if m and len(text) < 8:
            current_tier = m.group(1).upper()
            continue

        if current_tier:
            links = await el.query_selector_all("a[href*='/pokemon/']")
            for link in links:
                href = await link.get_attribute("href") or ""
                name = (await link.inner_text()).strip()
                slug = href.rstrip("/").split("/")[-1]
                if name and slug:
                    results.append({
                        "name": name,
                        "slug": slug,
                        "tier": current_tier,
                        "url": BASE_URL + href if href.startswith("/") else href,
                    })

    return results


# ─── Pokemon list ─────────────────────────────────────────────────────────────

async def scrape_pokemon_list(page: Page) -> list[dict[str, str]]:
    for path in ("/pokemon", "/pokedex", "/pokemon/"):
        await _go(page, BASE_URL + path)
        if "404" not in await page.title():
            break

    html = await page.content()

    # Try embedded JSON
    nd = _extract_next_data(html)
    if nd:
        props = _page_props(nd)
        for key in ("pokemon", "pokedex", "allPokemon", "pokemonList"):
            if key in props and isinstance(props[key], list):
                raw = props[key]
                return [
                    {
                        "name": p.get("name", ""),
                        "slug": p.get("slug", slugify(p.get("name", ""))),
                        "url": BASE_URL + "/pokemon/" + p.get("slug", slugify(p.get("name", ""))),
                    }
                    for p in raw if isinstance(p, dict) and p.get("name")
                ]

    # DOM fallback: collect all /pokemon/<slug> links
    links = await page.query_selector_all("a[href*='/pokemon/']")
    seen: set[str] = set()
    pokemon_list: list[dict[str, str]] = []
    for link in links:
        href = await link.get_attribute("href") or ""
        slug = href.rstrip("/").split("/pokemon/")[-1]
        if not slug or slug in seen or "/" in slug:
            continue
        seen.add(slug)
        name = (await link.inner_text()).strip() or slug.replace("-", " ").title()
        pokemon_list.append({
            "name": name,
            "slug": slug,
            "url": BASE_URL + "/pokemon/" + slug,
        })

    return pokemon_list


# ─── Individual Pokemon page ──────────────────────────────────────────────────

async def scrape_pokemon_page(page: Page, slug: str) -> dict[str, Any]:
    url = f"{BASE_URL}/pokemon/{slug}"
    await _go(page, url)

    data: dict[str, Any] = {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "source_url": url,
        "types": [],
        "base_stats": {},
        "abilities": [],
        "builds": [],
        "tier": None,
    }

    html = await page.content()

    # ── Next.js data ──
    nd = _extract_next_data(html)
    if nd:
        props = _page_props(nd)
        p = props.get("pokemon") or props.get("data") or props
        if isinstance(p, dict):
            data["name"] = p.get("name", data["name"])
            data["types"] = p.get("types", [])
            data["tier"] = p.get("tier")

            # Stats may be a nested dict or flat
            raw_stats = p.get("stats", p.get("baseStats", p.get("base_stats", {})))
            if isinstance(raw_stats, dict):
                for k, v in raw_stats.items():
                    key = normalize_stat(k)
                    if key:
                        data["base_stats"][key] = v
            elif isinstance(raw_stats, list):
                for entry in raw_stats:
                    if isinstance(entry, dict):
                        name_ = entry.get("name", entry.get("stat", {}).get("name", ""))
                        val = entry.get("base_stat", entry.get("value", 0))
                        key = normalize_stat(name_)
                        if key:
                            data["base_stats"][key] = val

            # Abilities
            raw_abil = p.get("abilities", [])
            for a in raw_abil:
                if isinstance(a, str):
                    data["abilities"].append({"name": a})
                elif isinstance(a, dict):
                    data["abilities"].append({
                        "name": a.get("name", a.get("ability", {}).get("name", "")),
                        "effect": a.get("effect", a.get("description", "")),
                        "hidden": a.get("is_hidden", False),
                    })

            # Builds / movesets
            raw_builds = p.get("builds", p.get("movesets", []))
            if isinstance(raw_builds, list):
                data["builds"] = raw_builds

    # ── DOM fallback for any missing fields ──
    try:
        # Name
        h1 = await page.query_selector("h1")
        if h1 and not data["name"]:
            data["name"] = (await h1.inner_text()).strip()

        # Types — look for type badge elements
        if not data["types"]:
            for sel in ("[class*='type-badge']", "[class*='type_badge']", "[class*='TypeBadge']",
                        "[data-type]", "[class*=' type ']"):
                els = await page.query_selector_all(sel)
                for el in els:
                    t = (await el.inner_text()).strip()
                    if t and t.isalpha() and len(t) <= 10:
                        data["types"].append(t)
                if data["types"]:
                    break
            data["types"] = list(dict.fromkeys(data["types"]))[:2]

        # Base stats — scan all text for stat patterns
        if not data["base_stats"]:
            body_text = await page.inner_text("body")
            data["base_stats"] = _parse_stats_from_text(body_text)

        # Abilities — text scan
        if not data["abilities"]:
            for sel in ("[class*='ability']", "[class*='Ability']"):
                els = await page.query_selector_all(sel)
                for el in els:
                    name_ = (await el.inner_text()).strip()
                    if name_ and len(name_) < 40:
                        data["abilities"].append({"name": name_})
                if data["abilities"]:
                    break

    except Exception as exc:
        logger.warning("DOM fallback failed for %s: %s", slug, exc)

    return data


# ─── Teams ───────────────────────────────────────────────────────────────────

async def scrape_teams(page: Page) -> list[dict[str, Any]]:
    for path in ("/teams", "/team-comps", "/best-teams"):
        await _go(page, BASE_URL + path)
        if "404" not in await page.title():
            break

    html = await page.content()

    # Next.js data
    nd = _extract_next_data(html)
    if nd:
        props = _page_props(nd)
        for key in ("teams", "teamComps", "team_comps"):
            if key in props and isinstance(props[key], list):
                return props[key]

    # Collect individual team page links and scrape each
    team_links = await page.query_selector_all("a[href*='/teams/']")
    seen: set[str] = set()
    team_urls: list[str] = []
    for link in team_links:
        href = await link.get_attribute("href") or ""
        if href not in seen and "/teams/" in href:
            seen.add(href)
            team_urls.append(BASE_URL + href if href.startswith("/") else href)

    teams: list[dict[str, Any]] = []
    for team_url in team_urls[:30]:  # cap at 30 teams
        await _go(page, team_url)
        team: dict[str, Any] = {"source_url": team_url, "name": "", "members": [], "strategy": None}

        html = await page.content()
        nd = _extract_next_data(html)
        if nd:
            props = _page_props(nd)
            raw = props.get("team") or props
            if isinstance(raw, dict):
                team["name"] = raw.get("name", "")
                team["strategy"] = raw.get("description", raw.get("strategy"))
                team["members"] = raw.get("pokemon", raw.get("members", []))

        if not team["name"]:
            h1 = await page.query_selector("h1")
            if h1:
                team["name"] = (await h1.inner_text()).strip()

        if team["name"] or team["members"]:
            teams.append(team)

    return teams


# ─── Async runner ─────────────────────────────────────────────────────────────

async def _run_async(data_dir: Path) -> None:
    pc_dir = data_dir / "pokechamps"
    poke_dir = pc_dir / "pokemon"
    for d in (pc_dir, poke_dir):
        d.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA, locale="en-US")
        page = await ctx.new_page()

        try:
            # Tier list
            print("  Scraping Pokechamps tier list...")
            tier_list = await scrape_tier_list(page)
            save_json(tier_list, pc_dir / "tier_list.json")
            print(f"    → {len(tier_list)} entries")

            # Pokemon list
            print("  Scraping Pokechamps Pokemon list...")
            pokemon_list = await scrape_pokemon_list(page)
            save_json(pokemon_list, pc_dir / "pokemon_list.json")
            print(f"    → {len(pokemon_list)} Pokemon found")

            # Individual Pokemon pages
            print(f"  Scraping {len(pokemon_list)} individual Pokemon pages...")
            all_pokemon: list[dict] = []
            for i, poke in enumerate(pokemon_list):
                print(f"    [{i + 1}/{len(pokemon_list)}] {poke['name']}...")
                poke_data = await scrape_pokemon_page(page, poke["slug"])
                save_json(poke_data, poke_dir / (poke["slug"] + ".json"))
                all_pokemon.append(poke_data)
            save_json(all_pokemon, pc_dir / "all_pokemon.json")

            # Teams
            print("  Scraping Pokechamps teams...")
            teams = await scrape_teams(page)
            save_json(teams, pc_dir / "teams.json")
            print(f"    → {len(teams)} teams")

        finally:
            await browser.close()

    print("  Pokechamps scraping complete.")


def run(data_dir: Path) -> None:
    asyncio.run(_run_async(data_dir))
