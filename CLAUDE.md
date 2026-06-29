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
pip install -r requirements.txt
python serve.py                       # http://localhost:5000
python run_scraper.py --source game8  # refresh Game8 data + PokeAPI enrichment
python -m pytest tests/ -q            # tests
```

## Architecture
- `app/main.py` — Flask routes (thin handlers).
- `app/data_loader.py` — merges Game8 tier/builds + PokeAPI enrichment into the roster; Megas
  inherit base-form builds (`_base_form_key`).
- `app/team_builder.py`, `app/matchup.py`, `app/type_chart.py` — domain logic.
- `app/pokemon_card.py` — detail-card payload. `app/meta_teams.py` — cleaned meta teams.
- `scrapers/` — `game8_scraper.py`, `pokeapi_enrich.py`, `pokechamps_scraper.py` (⚠️ needs
  rewrite — see `GAME_KNOWLEDGE.md` §9; pokechamps is server-rendered HTML, not a Next.js SPA).
- `templates/index.html`, `static/app.js`, `static/style.css` — single-page UI.

## Conventions
- Type annotations on function signatures; small focused modules; no comments unless asked.
- Data files under `data/` are committed so the app runs without scraping.
- PokeAPI/pokechamps requests need a real `User-Agent` header (Cloudflare 403s default urllib).
