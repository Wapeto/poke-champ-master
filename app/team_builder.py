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


def build_best_team(pool: list[dict], team_size: int = 6) -> list[dict]:
    """
    Greedy team builder: iteratively add the Pokemon that maximises
    the team score at each step.
    """
    if not pool:
        return []

    # Sort pool by tier descending as a starting heuristic
    sorted_pool = sorted(pool, key=lambda p: TIER_SCORE.get(p.get("tier", ""), 0), reverse=True)

    team: list[dict] = [sorted_pool[0]]
    remaining = sorted_pool[1:]

    while len(team) < team_size and remaining:
        best_candidate = None
        best_score = -9999.0
        for candidate in remaining:
            candidate_team = team + [candidate]
            s = score_team(candidate_team)
            if s > best_score:
                best_score = s
                best_candidate = candidate
        if best_candidate:
            team.append(best_candidate)
            remaining = [p for p in remaining if p is not best_candidate]
        else:
            break

    return team


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
