# Pokémon Champions — Game Knowledge Reference

> **Purpose:** Ground truth on how *Pokémon Champions* works so anyone (human or AI)
> extending this app makes decisions that fit the actual game. Keep this current.
>
> **Last updated:** 2026-06-29 · **Primary sources:** [pokechamps.com](https://pokechamps.com)
> (DotGG network, current as of June 2026) and [Game8](https://game8.co/games/Pokemon-Champions).
> Items marked *(unverified)* are inferred and should be confirmed before relying on them.

---

## 1. What the game is

*Pokémon Champions* is a dedicated **competitive Pokémon battling game** by The Pokémon
Company — battles only, no overworld/story. You assemble teams and climb a ranked ladder /
play tournaments. It is **cross-platform** (Nintendo Switch family + mobile iOS/Android), with
a mobile release tracked as imminent in mid-2026.

You do **not** catch Pokémon in the world. You **recruit** them (see §4), or import them from
**Pokémon HOME** — specifically from **Pokémon Legends: Z-A** and **Pokémon GO**. Transfer into
Champions is **one-way**: a Pokémon recruited inside Champions cannot be sent back to HOME.

---

## 2. Battle formats & Regulations

- **Single Battles** (1v1 on field, "Singles") and **Double Battles** ("Doubles"). The app's
  primary tier list is **Singles**.
- **Regulations** gate which Pokémon/rules are legal for a competitive season, rotating over
  time (VGC-style). Known: **Regulation M-A**, **Regulation M-B**. Each regulation publishes a
  roster and schedule. Team guides are often tagged by regulation (e.g. "Best Rain Team
  Regulation M-B").
- At a match you bring a team and (in Singles) **select 3 to bring** from your 6 — this is the
  basis of the app's Matchup Advisor.

---

## 3. Tier structure

Community tier lists rank the legal roster into **S, A+, A, B, C, D** (highest → lowest).
This app's internal `tier_score`: `S=6, A+=5, A=4, B=3, C=2, D=1`. The current Singles list is
~151 ranked Pokémon and is **mega-heavy** (74 of 151 entries are Mega Evolutions).

---

## 4. Roster Ranch & Recruiting  *(core mechanic — drives the "My Box" feature)*

Pokémon come from the **Roster Ranch**, run by a character named **Kitt**. The Ranch shows a
lineup of **10 Pokémon** and **refreshes every 22 hours**. You can inspect a Pokémon's moves
and current stats before deciding. Three recruit paths:

| Path | Cost | Editable? | Duration |
|------|------|-----------|----------|
| **Trial Recruitment** (free) | Free, **1 per day** | ❌ No (locked moves/stats) | **Borrow for 7 days**, then it's gone |
| **Convert Trial → Permanent** | **2,500 VP** (before the 7 days expire) | ✅ Yes | Permanent |
| **Permanent Recruitment** | **1,000 VP** or **1 Quick Ticket** | ✅ Yes | Permanent |

**Implications for the app's "My Box":**
- A box entry is either **Permanent** (owned, editable) or **Temporary/Trial** (7-day timer).
- Temporary entries have **days remaining** (1–7) and can be **promoted to Permanent** before
  expiry. After expiry they should be flagged/removed.
- Only Permanent Pokémon are fully editable (nature/EVs/moves) in Training mode — relevant if
  the box ever models editable builds.

---

## 5. Currencies & tickets

| Currency | Source | Use |
|----------|--------|-----|
| **VP (Victory Points)** | Battles / progression | Permanent recruit (1,000), Trial→Permanent (2,500) |
| **Quick Ticket** | Missions | Permanent recruit without VP |
| **Teammate Ticket** | Missions | Permanently recruit a Pokémon without spending VP |
| **Quick Coupon** | — | Cuts recruitment wait time by 1 hour each |
| **Affinity Tickets** | "Move Fiend" Trainer Achievements (use a move type 50× → 2 tickets; 250× → 5 more) | **18 type-specific** tickets; bias the next Ranch lineup toward a chosen type. Does **not** guarantee a specific Pokémon, only raises that type's odds. |

---

## 6. Pokémon building blocks

Standard modern-Pokémon (Gen 9) mechanics apply:

- **6 base stats:** HP, Attack (atk), Defense (def), Sp. Atk (spa), Sp. Def (spd), Speed (spe).
  Internally stored as minutes-free integers in `base_stats`.
- **EVs** (Effort Values, 0–252 per stat, 510 total) and **IVs** shape final stats. Builds in
  the data carry an `ev_spread`.
- **Natures** boost one stat / lower another (e.g. Adamant, Modest, Timid).
- **Abilities** — passive effects (e.g. Drought, Defiant, Rough Skin).
- **Held items** — one per Pokémon (Choice items, berries like Chople/Babiri, Leftovers, etc.).
- **Moves** — 4 per Pokémon; each has a **type** and a **category** (Physical/Special/Status).
- **Mega Evolution is present and central** (huge chunk of the meta). Mega forms often change
  typing and stats vs. the base form. ⚠️ Game8 hosts Mega builds under the **base** Pokémon's
  page, so Mega entries have no build of their own — this app inherits the base form's build
  for Megas (see `app/data_loader.py::_base_form_key`).
- **Regional forms** (Alolan / Galarian / Hisuian / Paldean) and other alt forms exist.

---

## 7. Type chart (Gen 9, 18 types)

Standard 18-type effectiveness chart, implemented in `app/type_chart.py` (`effectiveness`,
`weaknesses`, `resistances`, `best_attacking_types`). Multipliers: `0 / 0.5 / 1 / 2`, stacked
across dual types (so 4× and 0.25× exist). No Champions-specific deviations are known
*(unverified — confirm if a custom type interaction ever appears)*.

---

## 8. Meta archetypes

The Singles/Doubles meta revolves around recognizable archetypes (all present in the app's meta
teams):

- **Weather:** Rain, Sun, Sand, Snow (each built around a weather setter + abusers).
- **Trick Room** (slow teams that invert speed order).
- **Hyper Offense** (HO), **Balance**, **Stall**, **Perish Trap**.

Speed tiers matter a lot (there are dedicated "Speed Tiers" guides ranking every Pokémon's
Speed). Worth modelling if the app ever adds speed-control advice.

---

## 9. Data sources for this app

### Game8 — `https://game8.co/games/Pokemon-Champions`
Server-rendered HTML (BeautifulSoup). Source for tier list, builds, teams, moves, abilities,
items. Scraper: `scrapers/game8_scraper.py`. **Gaps:** only S/A+/A explanation tables carry
types; everything below A is typeless in the raw scrape, and Megas have no build page.

### PokeAPI — `https://pokeapi.co`
Free, no key. Used to **backfill types for every form (incl. all Megas)** and attach **official
artwork sprites**. Resolver: `scrapers/pokeapi_enrich.py` (name → slug, with overrides for alt
forms). Cache: `data/pokeapi/enrichment.json`. **Requires a User-Agent header** (Cloudflare 403s
the default urllib UA).

### pokechamps.com — `https://pokechamps.com`  *(DotGG network)*
Dedicated Champions fan site, **current and well-maintained**. **Server-rendered HTML for
article/info pages** (NOT a Next.js SPA — the old `pokechamps_scraper.py` assumed Next.js +
`__NEXT_DATA__` and is wrong). **Real routes:**

| Route | Content | Notes |
|-------|---------|-------|
| `/pokemon/` | Pokédex (≈202 mons) | **Grid is JS-rendered** → needs Playwright, or find the backing API |
| `/pokemon/<slug>/` | Per-Pokémon page | structured stats/moves/tier |
| `/pokemon-champions-tier-list/` | Tier list | **prose** (one `<h3>` per Pokémon), not a table |
| `/teams/` | Teams (≈33) | |
| `/metagame/`, `/moves/`, `/abilities/`, `/items/`, `/types/`, `/builder/`, `/tournaments/`, `/guides/` | info | mostly static HTML |

The static info pages scrape cleanly with `requests`+BeautifulSoup; only the Pokédex/builder
interactive widgets need a headless browser. Backed by DotGG infrastructure — check for a JSON
API (e.g. `api.dotgg.gg`) before scraping rendered DOM.

---

## 10. How game mechanics map to app features

- **Tier List / Team Builder / Matchup** → §2, §3, §7. Bring-3-of-6 is a Singles rule (§2).
- **Meta Teams** → §8 archetypes.
- **My Box** (planned) → §4 recruiting. Model: `Permanent` vs `Temporary(Trial, days_left 1–7)`,
  with promote-to-permanent. Optionally surface VP/Ticket costs (§5) as guidance.
- **Affinity Tickets** (§5) could power a future "what to chase in the Ranch" recommender:
  given a box + target archetype, suggest which type ticket to spend.
