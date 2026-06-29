# CLAUDE.md — poke-champ-master

Guidance for Claude Code working in this repo.

## Read first
- **`GAME_KNOWLEDGE.md`** — how *Pokémon Champions* actually works (formats, recruiting,
  Megas, currencies, meta, data-source notes). Read it before building features or suggesting
  improvements so decisions fit the real game.
- **`README.md`** — setup & usage.

## What this is
Flask web app for *Pokémon Champions*: tier list, team builder, matchup advisor, meta teams,
Pokémon detail cards. Data is scraped (Game8) and enriched (PokeAPI), committed under `data/`.

## Commands
```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11+ (3.14 ok)
pip install -r requirements.txt       # runtime only (Flask) — also what Vercel installs
pip install -r requirements-dev.txt   # + scraping deps (requests, bs4, lxml, playwright)
python serve.py                       # http://localhost:5000
python run_scraper.py --source game8  # refresh Game8 data + PokeAPI enrichment
python -m pytest tests/ -q            # tests
```

Deploy on Vercel: `vercel.json` + `api/index.py` serve the Flask app via `@vercel/python`.
Live at `poke-champ-master.vercel.app` (project `wapetos-projects/poke-champ-master`); Git is
connected, so every push to `master` auto-deploys. `requirements.txt` is runtime-only (Flask) so
the serverless bundle stays small; scraping deps live in `requirements-dev.txt`.

## Architecture
- `app/main.py` — Flask routes (thin handlers).
- `app/data_loader.py` — `build_roster()` merges Game8 tier/builds + PokeAPI/Pokechamps
  enrichment; `load_roster()` returns the precomputed `data/roster.json` when present (the prod
  fast path, avoids re-merging on every cold start), else builds on the fly. Regenerate the cache
  with `python build_data.py` (run_scraper.py does it automatically). Megas inherit base-form
  builds; base forms are synthesized for Megas that lack one. Each entry carries `is_mega` /
  `base_form`.
- `app/team_builder.py` — `expand_forms()` turns one owned base into its battle forms (base +
  Mega; a Mega is an equippable stone, not an owned mon); `build_best_team_from_groups()` picks
  one best form per owned slot and returns `(form, chosen_build)` pairs, enforcing two
  Champions legality rules: the **item clause** (no two members hold the same item — the build is
  chosen to avoid collisions) and a **Mega cap** (`MAX_MEGAS = 2`; only one Mega can activate per
  battle). `move_pool(form)` lists a form's known moves; `team_coverage(members)` recomputes
  offensive coverage from an edited moveset (served at `POST /api/team/coverage`) so the UI can
  let users swap moves — the four source-recommended moves keep a gold outline. Suggestions rank
  by complementarity (offensive gaps + stacked-weakness resists), not raw tier.
- `app/matchup.py`, `app/type_chart.py` — domain logic.
- **i18n (EN/FR):** `data_loader.load_i18n(lang)` reads `data/i18n/<lang>.json` (committed,
  built by `scrapers/translate_fr.py` from authoritative PokeAPI French names — Pokémon, types,
  moves, items, abilities, natures). Served at `/api/i18n/<lang>`. `static/i18n.js` holds the
  UI-string tables + `LANG` state (localStorage `pokeLang`) + helpers (`t`, `tName`, `tType`,
  `tMove`, `tItem`, `tAbility`, `tNature`, `searchMatch`). Translation is **display-only**:
  canonical data keys, `data-poke` refs, the box (localStorage) and all API payloads stay
  English; `static/app.js` re-renders via `rerenderAll()` on language switch. Scraped prose
  (Pokémon descriptions, meta-team names/strategy) is intentionally left English — no official
  French exists. Champions-invented Mega Stones / abilities fall back to English too. Regenerate
  `fr.json` with `python build_data.py` or `run_scraper.py` (needs network).
- `app/pokemon_card.py` — detail-card payload (`best_moves` capped at top 4).
  `app/meta_teams.py` — cleaned meta teams.
- `scrapers/` — `game8_scraper.py`, `pokeapi_enrich.py`, `pokechamps_scraper.py` (⚠️ needs
  rewrite — see `GAME_KNOWLEDGE.md` §9; pokechamps is server-rendered HTML, not a Next.js SPA).
- `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/style.css` — single-page UI.

## Conventions
- Type annotations on function signatures; small focused modules; no comments unless asked.
- Data files under `data/` are committed so the app runs without scraping — including the
  precomputed `data/roster.json`. Regenerate it (`python build_data.py`) after editing raw data.
- The frontend `My Box` (localStorage) holds only base forms (Megas are battle forms, hidden from
  box search) and allows duplicates (id-keyed entries). The Team Builder can "Load My Box".
- PokeAPI/pokechamps requests need a real `User-Agent` header (Cloudflare 403s default urllib).
