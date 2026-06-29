"""
Build the full detail payload for a single Pokemon — everything the UI card
needs: image, types, best moves, tier, defensive type matchups, best
teammates (from meta teams), and counters.
"""

from __future__ import annotations

from typing import Any

from .type_chart import resistances, weaknesses


def _best_moves(pokemon: dict) -> list[dict[str, str]]:
    """Deduplicated moves across all builds, preserving first-seen order."""
    seen: set[str] = set()
    moves: list[dict[str, str]] = []
    for build in pokemon.get("builds", []):
        for move in build.get("moves", []):
            name = move.get("name", "")
            if name and name not in seen:
                seen.add(name)
                moves.append({
                    "name": name,
                    "type": move.get("type", ""),
                    "category": move.get("category", ""),
                })
    return moves


def _best_teammates(pokemon: dict, teams: list[dict], limit: int = 6) -> list[str]:
    """Pokemon that share a meta team with this one, by co-occurrence count."""
    name = pokemon["name"].lower()
    counts: dict[str, int] = {}
    for team in teams:
        members = [m.get("pokemon", "") for m in team.get("members", [])]
        if any(m.lower() == name for m in members):
            for m in members:
                if m and m.lower() != name:
                    counts[m] = counts.get(m, 0) + 1
    return [m for m, _ in sorted(counts.items(), key=lambda kv: -kv[1])][:limit]


def _matchups(types: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Defensive weak/resist breakdown for the Pokemon's typing."""
    if not types:
        return {"weak_to": [], "resists": [], "immune_to": []}
    weak = [{"type": t, "mult": m} for t, m in weaknesses(types)]
    resist = [{"type": t, "mult": m} for t, m in resistances(types) if m > 0]
    immune = [{"type": t, "mult": 0} for t, m in resistances(types) if m == 0]
    return {"weak_to": weak, "resists": resist, "immune_to": immune}


def build_card(pokemon: dict, teams: list[dict]) -> dict[str, Any]:
    """Full detail payload for the Pokemon card / page."""
    types = pokemon.get("types", [])
    matchups = _matchups(types)
    return {
        "name": pokemon["name"],
        "tier": pokemon.get("tier", ""),
        "types": types,
        "image_url": pokemon.get("image_url"),
        "base_stats": pokemon.get("base_stats", {}),
        "abilities": pokemon.get("abilities", []),
        "build_url": pokemon.get("build_url", ""),
        "builds": pokemon.get("builds", []),
        "best_moves": _best_moves(pokemon),
        "best_teammates": _best_teammates(pokemon, teams),
        "counters": pokemon.get("counters", []),
        "weak_to": matchups["weak_to"],
        "resists": matchups["resists"],
        "immune_to": matchups["immune_to"],
    }
