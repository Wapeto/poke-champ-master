"""Tests for team-builder legality rules (item clause + Mega cap) and coverage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.team_builder import (
    MAX_MEGAS,
    build_best_team_from_groups,
    move_pool,
    team_coverage,
)


def _mon(name, item, types, is_mega=False, base=None):
    return {
        "name": name,
        "tier": "A",
        "types": types,
        "is_mega": is_mega,
        "base_form": base,
        "builds": [{"held_item": item, "nature": "Adamant", "ability": "X",
                    "moves": [{"name": f"{name} Move", "type": types[0], "category": "Physical"}]}],
    }


class TestItemClause:
    def test_no_duplicate_held_items(self):
        # Four mons whose top build all want Life Orb but each also offers an
        # alternative item, so the clause can be satisfied without dropping anyone.
        def mon(name):
            return {
                "name": name, "tier": "A", "types": ["Normal"], "is_mega": False,
                "base_form": None,
                "builds": [
                    {"held_item": "Life Orb", "moves": [{"name": "Tackle", "type": "Normal"}]},
                    {"held_item": f"{name} Berry", "moves": [{"name": "Tackle", "type": "Normal"}]},
                ],
            }
        groups = [(i, [mon(f"Mon{i}")]) for i in range(4)]
        pairs = build_best_team_from_groups(groups, team_size=4)
        items = [b.get("held_item") for _, b in pairs]
        assert len(items) == len(set(items)), f"duplicate items: {items}"


class TestMegaCap:
    def test_at_most_two_megas(self):
        # One base group offering many distinct Megas — only MAX_MEGAS may be fielded.
        base = _mon("Base", "Item0", ["Fire"])
        megas = [
            _mon(f"Mega{i}", f"Stone{i}", ["Fire"], is_mega=True, base="base")
            for i in range(5)
        ]
        # Each Mega is its own owned group so several could be picked at once.
        groups = [(i, [m]) for i, m in enumerate(megas)]
        groups.append((99, [base]))
        pairs = build_best_team_from_groups(groups, team_size=6)
        n_mega = sum(1 for f, _ in pairs if f.get("is_mega"))
        assert n_mega <= MAX_MEGAS


class TestCoverage:
    def test_coverage_from_move_types(self):
        members = [{"name": "X", "types": ["Fire"], "move_types": ["Ground"]}]
        cov = team_coverage(members)
        # Ground hits Fire/Electric/Poison/Rock/Steel super-effectively; Fire (STAB)
        # adds Grass/Ice/Bug/Steel. Steel must be covered, Dragon must not.
        assert "Steel" in cov["covered_types"]
        assert "Dragon" in cov["uncovered_types"]

    def test_move_pool_dedups(self):
        form = {
            "builds": [
                {"moves": [{"name": "A", "type": "Fire"}, {"name": "B", "type": "Ice"}]},
                {"moves": [{"name": "A", "type": "Fire"}, {"name": "C", "type": "Dark"}]},
            ]
        }
        names = [m["name"] for m in move_pool(form)]
        assert names == ["A", "B", "C"]
