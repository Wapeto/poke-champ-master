"""
Standard Gen 9 type effectiveness chart.
chart[attacking_type][defending_type] = multiplier (2, 1, 0.5, or 0)
"""

TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
]

# Raw table: rows = attacking type, cols = defending type (order matches TYPES list)
# Values: 2=super, 1=normal, 0.5=not very, 0=immune
_RAW: list[list[float]] = [
    # Nor  Fir  Wat  Ele  Gra  Ice  Fig  Poi  Gro  Fly  Psy  Bug  Roc  Gho  Dra  Dar  Ste  Fai
    [1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,  0.5,  0,   1,   1,  0.5,  1 ],  # Normal
    [1,  0.5, 0.5,  1,   2,   2,   1,   1,   1,   1,   1,   2,  0.5,  1,  0.5,  1,   2,   1 ],  # Fire
    [1,   2,  0.5,  1,  0.5,  1,   1,   1,   2,   1,   1,   1,   2,   1,  0.5,  1,   1,   1 ],  # Water
    [1,   1,   2,  0.5, 0.5,  1,   1,   1,   0,   2,   1,   1,   1,   1,  0.5,  1,   1,   1 ],  # Electric
    [1,  0.5,  2,   1,  0.5,  1,   1,  0.5,  2,  0.5,  1,  0.5,  2,   1,  0.5,  1,  0.5,  1 ],  # Grass
    [1,  0.5, 0.5,  1,   2,  0.5,  1,   1,   2,   2,   1,   1,   1,   1,   2,   1,  0.5,  1 ],  # Ice
    [2,   1,   1,   1,   1,   2,   1,  0.5,  1,  0.5, 0.5, 0.5,  2,   0,   1,   2,   2,  0.5],  # Fighting
    [1,   1,   1,   1,   2,   1,   1,  0.5, 0.5,  1,   1,   1,   1,  0.5,  1,   1,   0,   2 ],  # Poison
    [1,   2,   1,   2,  0.5,  1,   1,   2,   1,   0,   1,  0.5,  2,   1,   1,   1,   2,   1 ],  # Ground
    [1,   1,   1,  0.5,  2,   2,   2,   1,   1,   1,   1,   2,  0.5,  1,   1,   1,  0.5,  1 ],  # Flying
    [1,   1,   1,   1,   1,   1,   2,   2,   1,   1,  0.5,  1,   1,   1,   1,   0,  0.5,  1 ],  # Psychic
    [1,  0.5,  1,   1,   2,   1,  0.5,  0.5,  1,  0.5,  2,   1,   1,  0.5,  1,   2,  0.5, 0.5],  # Bug
    [1,   2,   1,   1,   1,   2,  0.5,  1,  0.5,  2,   1,   2,   1,   1,   1,   1,  0.5,  1 ],  # Rock
    [0,   1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   1,   1,   2,   1,  0.5,  1,   1 ],  # Ghost
    [1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   1,  0.5,  0 ],  # Dragon
    [1,   1,   1,   1,   1,   1,  0.5,  1,   1,   1,   2,   1,   1,   2,   1,  0.5,  1,  0.5],  # Dark
    [1,  0.5, 0.5, 0.5,  1,   2,   1,   1,   1,   1,   1,   1,   2,   1,   1,   1,  0.5,  2 ],  # Steel
    [1,  0.5,  1,   1,   1,   1,   2,  0.5,  1,   1,   1,   1,   1,   1,   2,   2,  0.5,  1 ],  # Fairy
]

_IDX = {t: i for i, t in enumerate(TYPES)}

# Pre-build lookup dict: chart[atk][def] = multiplier
CHART: dict[str, dict[str, float]] = {
    atk: {TYPES[j]: _RAW[i][j] for j in range(len(TYPES))}
    for i, atk in enumerate(TYPES)
}


def effectiveness(attacking_type: str, defending_types: list[str]) -> float:
    """Combined multiplier of an attacking type against a dual-type defender."""
    mult = 1.0
    row = CHART.get(attacking_type, {})
    for dt in defending_types:
        mult *= row.get(dt, 1.0)
    return mult


def best_attacking_types(defending_types: list[str]) -> list[tuple[str, float]]:
    """Return attacking types sorted by effectiveness against the given defending types."""
    results = [(t, effectiveness(t, defending_types)) for t in TYPES]
    return sorted(results, key=lambda x: -x[1])


def weaknesses(defending_types: list[str]) -> list[tuple[str, float]]:
    """Return types that deal super-effective damage to the given defender."""
    return [(t, m) for t, m in best_attacking_types(defending_types) if m > 1]


def resistances(defending_types: list[str]) -> list[tuple[str, float]]:
    """Return types that deal reduced damage to the given defender."""
    return [(t, m) for t, m in best_attacking_types(defending_types) if m < 1]
