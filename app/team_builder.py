"""
Team builder: given a pool of Pokemon the user owns, score and return the best 6.

Scoring per candidate team:
  - Tier score   : sum of tier_scores (S=6 … D=1)
  - Offense score: how many of the 18 types the team can hit super-effectively
  - Defense score: penalty for shared team weaknesses (4x weak = -4, 2x = -1)
  - Role score   : bonus for role diversity (attacker / wall / setter / support)

Uses a greedy build rather than brute-force to stay fast with large pools.
"""

from __future__ import annotations
from typing import Any

from .type_chart import TYPES, effectiveness, weaknesses

TIER_SCORE = {"S": 6, "A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}

# Simple role classification from a build's moves
SETUP_MOVES = {"swords dance", "nasty plot", "dragon dance", "calm mind", "quiver dance",
               "bulk up", "shell smash", "no retreat", "iron defense", "amnesia"}
SUPPORT_MOVES = {"tailwind", "trick room", "reflect", "light screen", "aurora veil",
                 "stealth rock", "spikes", "toxic spikes", "sticky web", "rain dance",
                 "sunny day", "sandstorm", "snowscape"}
RECOVERY_MOVES = {"recover", "roost", "slack off", "soft-boiled", "morning sun",
                  "moonlight", "synthesis", "wish", "life dew", "strength sap"}


def _role(pokemon: dict) -> str:
    move_names = {
        m["name"].lower()
        for b in pokemon.get("builds", [])
        for m in b.get("moves", [])
    }
    if move_names & SUPPORT_MOVES:
        return "support"
    if move_names & RECOVERY_MOVES:
        return "wall"
    if move_names & SETUP_MOVES:
        return "setup"
    # High speed + high atk/spa → attacker
    stats = pokemon.get("base_stats", {})
    if stats.get("spe", 0) >= 100 or stats.get("atk", 0) >= 110 or stats.get("spa", 0) >= 110:
        return "attacker"
    if stats.get("hp", 0) >= 100 or stats.get("def", 0) >= 100 or stats.get("spd", 0) >= 100:
        return "wall"
    return "attacker"


def _team_offense_score(team: list[dict]) -> int:
    """Count how many types the team can hit super-effectively."""
    coverable = set()
    for poke in team:
        move_types = {
            m.get("type", "")
            for b in poke.get("builds", [])
            for m in b.get("moves", [])
            if m.get("type")
        }
        # Also count the Pokemon's own STAB types
        move_types |= set(poke.get("types", []))
        for mtype in move_types:
            for dt in TYPES:
                if effectiveness(mtype, [dt]) >= 2:
                    coverable.add(dt)
    return len(coverable)


def _team_defense_score(team: list[dict]) -> float:
    """Penalty: sum of weaknesses across the team (double-counted = double penalty)."""
    weakness_counts: dict[str, int] = {t: 0 for t in TYPES}
    for poke in team:
        types = poke.get("types", [])
        if not types:
            continue
        for atk_type, mult in weaknesses(types):
            if mult >= 4:
                weakness_counts[atk_type] += 2
            else:
                weakness_counts[atk_type] += 1

    # Penalty: types where 3+ team members are weak
    penalty = sum(max(0, count - 2) for count in weakness_counts.values())
    return -penalty


def _team_role_score(team: list[dict]) -> int:
    roles = {_role(p) for p in team}
    # Reward having diverse roles
    return len(roles)


def score_team(team: list[dict]) -> float:
    tier_total = sum(TIER_SCORE.get(p.get("tier", ""), 0) for p in team)
    offense = _team_offense_score(team)
    defense = _team_defense_score(team)
    role_div = _team_role_score(team)

    # Weights tuned for competitive singles
    return tier_total * 2.0 + offense * 1.5 + defense * 1.0 + role_div * 2.0


def expand_forms(name: str, roster: dict[str, dict]) -> list[dict]:
    """
    Battle forms available from owning one Pokemon: the base form plus any Mega
    it can evolve into (the Mega is an equippable stone, not a separate owned mon).
    """
    base = roster.get(name.strip().lower())
    forms: list[dict] = [base] if base else []
    base_key = name.strip().lower()
    for poke in roster.values():
        if poke.get("is_mega") and poke.get("base_form") == base_key and poke is not base:
            forms.append(poke)
    return forms


def build_best_team(pool: list[dict], team_size: int = 6) -> list[dict]:
    """
    Greedy team builder: iteratively add the Pokemon that maximises
    the team score at each step.
    """
    if not pool:
        return []
    return build_best_team_from_groups([(i, [p]) for i, p in enumerate(pool)], team_size)


def build_best_team_from_groups(
    groups: list[tuple[Any, list[dict]]], team_size: int = 6
) -> list[dict]:
    """
    Greedy builder over groups of interchangeable forms. Each group is one owned
    Pokemon offering several battle forms (base / Mega); at most one form per group
    is chosen, so duplicates in the pool become independent groups.
    """
    team: list[dict] = []
    used: set[Any] = set()

    while len(team) < team_size:
        best_form = None
        best_gid = None
        best_score = -9999.0
        for gid, forms in groups:
            if gid in used:
                continue
            for form in forms:
                if not form:
                    continue
                s = score_team(team + [form])
                if s > best_score:
                    best_score = s
                    best_form = form
                    best_gid = gid
        if best_form is None:
            break
        team.append(best_form)
        used.add(best_gid)

    return team


def suggest_additions(
    current: list[dict], roster: list[dict], limit: int = 6
) -> dict[str, Any]:
    """
    Given the currently selected Pokemon, recommend which Pokemon to add next
    and which types would most help, based on marginal team-score gain.
    """
    chosen = {p["name"].lower() for p in current}
    # Forms already represented (so we don't suggest a Mega of something owned).
    families = {p.get("base_form") or p["name"].lower() for p in current}

    covered = _covered_types(current)
    attack_types_needed = [t for t in TYPES if t not in covered]

    weakness_counts: dict[str, int] = {t: 0 for t in TYPES}
    for poke in current:
        for atk_type, _ in weaknesses(poke.get("types", [])):
            weakness_counts[atk_type] += 1
    weak_spots = sorted(
        (t for t, c in weakness_counts.items() if c >= 2),
        key=lambda t: -weakness_counts[t],
    )

    # Rank candidates by how well they COMPLEMENT the current team:
    #   + new offensive types they unlock
    #   + how many of the team's stacked weaknesses they resist/are immune to
    # Tier is only a small tiebreak, so suggestions stop being "just the top Megas".
    scored: list[tuple[float, int, float, int, dict]] = []
    for cand in roster:
        if cand["name"].lower() in chosen or (cand.get("base_form") or cand["name"].lower()) in families:
            continue
        new_cover = len(_covered_types([cand]) & set(attack_types_needed))
        cand_types = cand.get("types", [])
        resist = sum(1 for spot in weak_spots if effectiveness(spot, cand_types) < 1)
        tier = TIER_SCORE.get(cand.get("tier", ""), 0)
        gain = new_cover * 2.0 + resist * 2.0 + tier * 0.4
        scored.append((gain, new_cover, float(resist), tier, cand))
    scored.sort(key=lambda t: (-t[0], -t[3]))

    suggestions = [
        {
            "name": c["name"],
            "tier": c.get("tier", ""),
            "types": c.get("types", []),
            "image_url": c.get("image_url"),
            "role": _role(c),
            "gain": round(gain, 1),
        }
        for gain, _nc, _r, _t, c in scored[:limit]
    ]
    # Defensive types worth adding: rank by how many of the team's weak spots
    # each candidate type resists.
    resist_scores = {
        d: sum(1 for spot in weak_spots if effectiveness(spot, [d]) < 1)
        for d in TYPES
    }
    resist_needed = [
        d for d, n in sorted(resist_scores.items(), key=lambda kv: -kv[1])
        if n > 0
    ][:6]

    return {
        "suggestions": suggestions,
        "attack_types_needed": attack_types_needed,
        "weak_spots": weak_spots,
        "defensive_types_needed": resist_needed,
    }


def _covered_types(team: list[dict]) -> set[str]:
    covered: set[str] = set()
    for poke in team:
        move_types = {
            m.get("type", "")
            for b in poke.get("builds", [])
            for m in b.get("moves", [])
            if m.get("type")
        }
        move_types |= set(poke.get("types", []))
        for mtype in move_types:
            for dt in TYPES:
                if effectiveness(mtype, [dt]) >= 2:
                    covered.add(dt)
    return covered


def explain_team(team: list[dict]) -> dict[str, Any]:
    """Return a human-readable breakdown of the team's strengths/weaknesses."""
    # Types the team is weak to
    weakness_map: dict[str, list[str]] = {t: [] for t in TYPES}
    for poke in team:
        types = poke.get("types", [])
        if not types:
            continue
        for atk_type, mult in weaknesses(types):
            weakness_map[atk_type].append(f"{poke['name']} ({mult}x)")

    shared_weaknesses = {t: members for t, members in weakness_map.items() if len(members) >= 2}

    # Type coverage
    covered_types = set()
    for poke in team:
        move_types = {
            m.get("type", "")
            for b in poke.get("builds", [])
            for m in b.get("moves", [])
            if m.get("type")
        }
        move_types |= set(poke.get("types", []))
        for mtype in move_types:
            for dt in TYPES:
                if effectiveness(mtype, [dt]) >= 2:
                    covered_types.add(dt)

    uncovered = [t for t in TYPES if t not in covered_types]

    return {
        "score": round(score_team(team), 1),
        "roles": {p["name"]: _role(p) for p in team},
        "shared_weaknesses": shared_weaknesses,
        "covered_types": sorted(covered_types),
        "uncovered_types": uncovered,
    }
