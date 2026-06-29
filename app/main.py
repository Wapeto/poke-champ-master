"""Flask web app for Pokemon Champions advisor."""

from flask import Flask, jsonify, render_template, request
from .data_loader import load_roster, load_teams, load_moves, load_abilities, load_items
from .team_builder import build_best_team, explain_team
from .matchup import recommend

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# ── Load data at startup ──────────────────────────────────────────────────────
ROSTER = load_roster()          # {name_lower: pokemon_dict}
TEAMS  = load_teams()
MOVES  = load_moves()
ABILITIES = load_abilities()
ITEMS  = load_items()

POKEMON_LIST = sorted(ROSTER.values(), key=lambda p: (-p["tier_score"], p["name"]))


def _find(name: str) -> dict | None:
    return ROSTER.get(name.strip().lower())


def _resolve_names(names: list[str]) -> list[dict]:
    result = []
    for n in names:
        p = _find(n)
        if p:
            result.append(p)
    return result


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/pokemon")
def api_pokemon_list():
    """All Pokemon names + tier for autocomplete."""
    return jsonify([
        {"name": p["name"], "tier": p["tier"], "types": p["types"]}
        for p in POKEMON_LIST
    ])


@app.get("/api/pokemon/<name>")
def api_pokemon_detail(name: str):
    p = _find(name)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify(p)


@app.get("/api/tier-list")
def api_tier_list():
    """Grouped tier list for display."""
    tiers: dict[str, list] = {"S": [], "A+": [], "A": [], "B": [], "C": [], "D": []}
    for p in POKEMON_LIST:
        tier = p.get("tier", "")
        if tier in tiers:
            tiers[tier].append({
                "name": p["name"],
                "types": p["types"],
                "base_stats": p["base_stats"],
                "build_url": p.get("build_url", ""),
            })
    return jsonify(tiers)


@app.post("/api/team/build")
def api_team_build():
    """
    Body: {"pokemon": ["Garchomp", "Gyarados", ...]}
    Returns best team of 6 from the given pool.
    """
    body = request.get_json(silent=True) or {}
    names = body.get("pokemon", [])
    pool = _resolve_names(names)

    if not pool:
        return jsonify({"error": "No valid Pokemon found in the list"}), 400

    team = build_best_team(pool)
    explanation = explain_team(team)

    return jsonify({
        "team": [
            {
                "name": p["name"],
                "tier": p["tier"],
                "types": p["types"],
                "role": explanation["roles"].get(p["name"], ""),
                "best_build": p["builds"][0] if p.get("builds") else None,
                "build_url": p.get("build_url", ""),
            }
            for p in team
        ],
        "analysis": {
            "score": explanation["score"],
            "covered_types": explanation["covered_types"],
            "uncovered_types": explanation["uncovered_types"],
            "shared_weaknesses": explanation["shared_weaknesses"],
        },
    })


@app.post("/api/matchup")
def api_matchup():
    """
    Body: {
      "my_team": ["Garchomp", "Pelipper", ...],
      "opponent_team": ["Metagross", "Dragonite", ...]
    }
    Returns which 3 to bring and who to lead with.
    """
    body = request.get_json(silent=True) or {}
    my_team     = _resolve_names(body.get("my_team", []))
    opp_team    = _resolve_names(body.get("opponent_team", []))

    if not my_team:
        return jsonify({"error": "No valid Pokemon found in my_team"}), 400

    result = recommend(my_team, opp_team)

    return jsonify({
        "bring": [
            {
                "name": p["name"],
                "tier": p["tier"],
                "types": p["types"],
                "best_build": p["builds"][0] if p.get("builds") else None,
            }
            for p in result["bring"]
        ],
        "lead": {
            "name": result["lead"]["name"],
            "types": result["lead"].get("types", []),
        } if result["lead"] else None,
        "lead_reasoning": result.get("lead_reasoning", ""),
        "full_scores": [
            {
                "name": s["name"],
                "tier": s["tier"],
                "total_score": s["total_score"],
                "per_opponent": s["per_opponent"],
            }
            for s in result["scores"]
        ],
    })


@app.get("/api/teams")
def api_teams():
    """Pre-built teams from Game8."""
    return jsonify([
        {
            "name": t["name"],
            "members": [
                {
                    "pokemon": m["pokemon"],
                    "nature": m.get("nature"),
                    "ability": m.get("ability"),
                    "held_item": m.get("held_item"),
                    "moves": [mv["name"] for mv in m.get("moves", [])],
                    "ev_spread": m.get("ev_spread"),
                }
                for m in t.get("members", [])
            ],
        }
        for t in TEAMS
    ])
