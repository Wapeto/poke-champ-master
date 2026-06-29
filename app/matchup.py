"""
Matchup advisor: given my team and the opponent's team, recommend which
3 Pokemon to bring and which one to lead with.

Scoring per Pokemon against the opponent's team:
  - Offensive pressure : for each opponent, how many of my STAB/move types
                         hit super-effectively (+2) or neutrally (+1)
  - Defensive resilience: for each opponent type combo, how much damage I
                          take on average (high damage = penalty)
  - Tier bonus         : higher-tier Pokemon get a small bump
"""

from __future__ import annotations
from typing import Any

from .type_chart import TYPES, effectiveness, weaknesses
from .team_builder import TIER_SCORE

BRING_SIZE = 3


def _offensive_score(my_poke: dict, opponent: dict) -> float:
    """How well can my_poke pressure this opponent?"""
    opp_types = opponent.get("types", []) or ["Normal"]

    # Move types available (STAB + moves)
    my_move_types = {
        m.get("type", "")
        for b in my_poke.get("builds", [])
        for m in b.get("moves", [])
        if m.get("type")
    }
    my_move_types |= set(my_poke.get("types", []))
    my_move_types.discard("")

    best_mult = max(
        (effectiveness(mt, opp_types) for mt in my_move_types),
        default=1.0,
    )
    return best_mult


def _defensive_score(my_poke: dict, opponent: dict) -> float:
    """How much pressure does the opponent put on me? (lower = opponent pressures me more)"""
    my_types = my_poke.get("types", []) or ["Normal"]

    opp_move_types = {
        m.get("type", "")
        for b in opponent.get("builds", [])
        for m in b.get("moves", [])
        if m.get("type")
    }
    opp_move_types |= set(opponent.get("types", []))
    opp_move_types.discard("")

    if not opp_move_types:
        return 1.0

    # Worst-case multiplier the opponent can land on me
    worst = max(
        (effectiveness(mt, my_types) for mt in opp_move_types),
        default=1.0,
    )
    return 1.0 / worst  # Invert: surviving = good


def matchup_score(my_poke: dict, opponent_team: list[dict]) -> dict[str, Any]:
    """Score how well my_poke handles the entire opponent team."""
    offense_total = 0.0
    defense_total = 0.0
    per_opponent: list[dict] = []

    for opp in opponent_team:
        off = _offensive_score(my_poke, opp)
        deff = _defensive_score(my_poke, opp)
        offense_total += off
        defense_total += deff
        per_opponent.append({
            "name": opp["name"],
            "offensive_mult": round(off, 2),
            "survives": deff >= 0.5,
        })

    tier_bonus = TIER_SCORE.get(my_poke.get("tier", ""), 0) * 0.5
    total = offense_total * 1.5 + defense_total + tier_bonus

    return {
        "name": my_poke["name"],
        "tier": my_poke.get("tier", ""),
        "total_score": round(total, 2),
        "per_opponent": per_opponent,
    }


def recommend(my_team: list[dict], opponent_team: list[dict]) -> dict[str, Any]:
    """
    Returns:
      - bring: list of 3 Pokemon dicts (best 3 to bring)
      - lead: the best lead from those 3
      - scores: full matchup breakdown for all my Pokemon
    """
    if not my_team:
        return {"bring": [], "lead": None, "scores": []}
    if not opponent_team:
        # No opponent info — return top 3 by tier
        by_tier = sorted(my_team, key=lambda p: TIER_SCORE.get(p.get("tier", ""), 0), reverse=True)
        return {"bring": by_tier[:BRING_SIZE], "lead": by_tier[0] if by_tier else None, "scores": []}

    # Score every member of my team
    scores = [matchup_score(p, opponent_team) for p in my_team]
    scores.sort(key=lambda s: -s["total_score"])

    bring_scores = scores[:BRING_SIZE]
    bring_pokemon = [p for p in my_team if p["name"] in {s["name"] for s in bring_scores}]

    # Lead: best matchup against the opponent's highest-tier / first Pokemon
    lead_target = sorted(
        opponent_team,
        key=lambda p: TIER_SCORE.get(p.get("tier", ""), 0),
        reverse=True,
    )[0]

    lead = max(
        bring_pokemon,
        key=lambda p: _offensive_score(p, lead_target) - (1 / _defensive_score(p, lead_target) if _defensive_score(p, lead_target) else 0),
    )

    return {
        "bring": bring_pokemon,
        "lead": lead,
        "scores": scores,
        "lead_reasoning": f"Best matchup vs {lead_target['name']} (opponent's strongest)",
    }
