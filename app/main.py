"""Flask web app for Pokemon Champions advisor."""

from flask import Flask, jsonify, render_template, request
from .data_loader import (
    load_roster, load_teams, load_moves, load_abilities, load_items, load_i18n,
)
from .team_builder import (
    build_best_team_from_groups,
    expand_forms,
    explain_team,
    suggest_additions,
)
from .matchup import recommend
from .pokemon_card import build_card, attach_item_images
from .meta_teams import build_meta_teams
from .pokechamps_data import load_item_images

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# ── Load data at startup ──────────────────────────────────────────────────────
ROSTER = load_roster()          # {name_lower: pokemon_dict}
TEAMS  = load_teams()
MOVES  = load_moves()
ABILITIES = load_abilities()
ITEMS  = load_items()
ITEM_IMAGES = load_item_images()
I18N = {"fr": load_i18n("fr")}   # data-label translations, loaded once at startup

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


@app.get("/api/i18n/<lang>")
def api_i18n(lang: str):
    """Data-label translation dictionaries (names, moves, items, etc.) for a language."""
    return jsonify(I18N.get(lang) or load_i18n(lang))


@app.get("/api/pokemon")
def api_pokemon_list():
    """All Pokemon names + tier for autocomplete."""
    return jsonify([
        {"name": p["name"], "tier": p["tier"], "types": p["types"],
         "image_url": p.get("image_url"), "is_mega": p.get("is_mega", False)}
        for p in POKEMON_LIST
    ])


@app.get("/api/pokemon/<name>")
def api_pokemon_detail(name: str):
    p = _find(name)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify(build_card(p, TEAMS, ITEM_IMAGES))


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
                "image_url": p.get("image_url"),
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

    # Each owned Pokemon is one group of interchangeable battle forms (base + Mega),
    # so duplicates stay independent and a Mega is picked only when it's the best form.
    groups = [(i, expand_forms(n, ROSTER)) for i, n in enumerate(names)]
    groups = [(i, forms) for i, forms in groups if forms]

    if not groups:
        return jsonify({"error": "No valid Pokemon found in the list"}), 400

    team = build_best_team_from_groups(groups)
    explanation = explain_team(team)

    return jsonify({
        "team": [
            {
                "name": p["name"],
                "tier": p["tier"],
                "types": p["types"],
                "image_url": p.get("image_url"),
                "role": explanation["roles"].get(p["name"], ""),
                "best_build": attach_item_images(p["builds"][0] if p.get("builds") else None, ITEM_IMAGES),
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


@app.post("/api/team/suggest")
def api_team_suggest():
    """
    Body: {"pokemon": ["Garchomp", ...]}
    Suggest which Pokemon to add next and which types would most help.
    """
    body = request.get_json(silent=True) or {}
    current = _resolve_names(body.get("pokemon", []))
    if not current:
        return jsonify({"suggestions": [], "attack_types_needed": [],
                        "weak_spots": [], "defensive_types_needed": []})
    return jsonify(suggest_additions(current, POKEMON_LIST))


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
                "image_url": p.get("image_url"),
                "best_build": attach_item_images(p["builds"][0] if p.get("builds") else None, ITEM_IMAGES),
            }
            for p in result["bring"]
        ],
        "lead": {
            "name": result["lead"]["name"],
            "types": result["lead"].get("types", []),
        } if result["lead"] else None,
        "lead_target": result.get("lead_target", ""),
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
    """Cleaned, enriched meta teams from Game8."""
    return jsonify(build_meta_teams(TEAMS, ROSTER, ITEM_IMAGES))
