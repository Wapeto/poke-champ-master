# Pokémon Champions Advisor

A web app for **Pokémon Champions** (mobile) that scrapes Game8's wiki and gives you:

- **Tier list** — all 151 ranked Pokémon with types and stats
- **Team Builder** — pick Pokémon you own, get the optimal team of 6 (tier + type coverage + role balance)
- **Matchup Advisor** — enter your team and the opponent's, get which 3 to bring and who to lead
- **Meta Teams** — 10 curated competitive team compositions (Rain, Sun, Sand, Trick Room, HO, etc.)

---

## Requirements

- Python 3.11+
- pip

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:Wapeto/poke-champ-master.git
cd poke-champ-master
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> If your system blocks pip installs (PEP 668), add `--break-system-packages` or use a virtual environment:
> ```bash
> python -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> ```

### 3. Install Playwright browser (only needed if you scrape Pokechamps)

```bash
playwright install chromium
```

---

## Running the app

The scraped data is already committed in `data/`. You can run the web app immediately:

```bash
python serve.py
```

Then open **http://localhost:5000** in your browser.

---

## Refreshing data (after game updates)

```bash
# Scrape Game8 only (fast, ~5 min)
python run_scraper.py --source game8

# Scrape both sites
python run_scraper.py --source all

# Custom output directory
python run_scraper.py --source game8 --data-dir ./my_data
```

The scraper respects a 1.5 s delay between requests to avoid hammering Game8's servers.

---

## Project structure

```
poke-champ-master/
│
├── serve.py                  # Start the web app (python serve.py)
├── run_scraper.py            # CLI to refresh scraped data
├── requirements.txt
│
├── app/
│   ├── main.py               # Flask routes + API endpoints
│   ├── data_loader.py        # Loads JSON data into memory at startup
│   ├── team_builder.py       # Greedy team optimisation algorithm
│   ├── matchup.py            # Per-opponent scoring + lead recommendation
│   └── type_chart.py         # Full Gen 9 type effectiveness matrix
│
├── scrapers/
│   ├── game8_scraper.py      # Game8 wiki scraper (BeautifulSoup)
│   ├── pokechamps_scraper.py # Pokechamps scraper (Playwright, JS-rendered)
│   └── utils.py              # Shared helpers (slugify, parse EVs, save JSON)
│
├── templates/
│   └── index.html            # Single-page UI
│
├── static/
│   ├── style.css             # Dark theme, type colours
│   └── app.js                # Tab navigation, search, API calls
│
└── data/
    └── game8/
        ├── tier_list.json        # 151 Pokémon with tier, types, base stats
        ├── all_builds.json       # 162 Pokémon builds (nature, item, EVs, moves)
        ├── all_teams.json        # 10 meta team compositions
        ├── moves.json            # 204 moves
        ├── abilities.json        # 200 abilities
        ├── items.json            # Held items
        ├── builds/               # One JSON file per Pokémon
        └── teams/                # One JSON file per team guide
```

---

## API endpoints

All endpoints are served at `http://localhost:5000`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/pokemon` | All Pokémon names, tiers, types (for autocomplete) |
| `GET`  | `/api/pokemon/<name>` | Full data for one Pokémon |
| `GET`  | `/api/tier-list` | Pokémon grouped by tier |
| `GET`  | `/api/teams` | All meta teams |
| `POST` | `/api/team/build` | Build best team from a pool |
| `POST` | `/api/matchup` | Matchup analysis: bring 3 + lead |

### Team builder request

```bash
curl -X POST http://localhost:5000/api/team/build \
  -H "Content-Type: application/json" \
  -d '{"pokemon": ["Garchomp", "Gyarados", "Corviknight", "Mimikyu", "Aegislash", "Pelipper"]}'
```

### Matchup advisor request

```bash
curl -X POST http://localhost:5000/api/matchup \
  -H "Content-Type: application/json" \
  -d '{
    "my_team": ["Garchomp", "Corviknight", "Mimikyu", "Pelipper", "Aegislash", "Gyarados"],
    "opponent_team": ["Metagross", "Alolan Ninetales", "Hippowdon", "Grimmsnarl"]
  }'
```

---

## Team builder algorithm

Given a pool of Pokémon the user owns, the builder greedily picks 6 by maximising a composite score:

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Tier score | 2.0× | S=6, A+=5, A=4, B=3, C=2, D=1 |
| Offensive coverage | 1.5× | How many of the 18 types the team hits super-effectively |
| Defensive penalty | 1.0× | Penalty for shared weaknesses (3+ members weak to same type) |
| Role diversity | 2.0× | Bonus for having attacker / wall / support / setup roles |

---

## Matchup advisor algorithm

For each Pokémon in your team, a score is computed against the full opponent team:

- **Offensive pressure**: best type multiplier your moves/STAB achieve against each opponent
- **Defensive resilience**: inverse of the worst hit you take from opponent moves
- **Tier bonus**: small weight for Pokémon tier

Top 3 by score = your bring. Lead = the one with the best matchup vs. the opponent's highest-tier Pokémon.

---

## Data sources

- **Game8** — `https://game8.co/games/Pokemon-Champions` (tier lists, builds, teams, moves, abilities, items)
- **Pokechamps** — `https://pokechamps.com` (scraper included but data not yet committed; run `--source pokechamps`)
