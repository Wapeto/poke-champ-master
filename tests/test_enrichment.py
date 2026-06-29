"""Tests for the data-enrichment and card-building logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_loader import _base_form_key, load_roster
from app.meta_teams import _clean_name
from app.pokemon_card import _matchups
from app.team_builder import suggest_additions
from scrapers.pokeapi_enrich import candidate_slugs


class TestSlugResolution:
    def test_mega_with_variant(self):
        assert candidate_slugs("Mega Charizard Y")[0] == "charizard-mega-y"
        assert candidate_slugs("Mega Charizard X")[0] == "charizard-mega-x"

    def test_mega_without_variant(self):
        assert candidate_slugs("Mega Mawile") == ["mawile-mega"]

    def test_regional_forms(self):
        assert candidate_slugs("Alolan Ninetales")[0] == "ninetales-alola"
        assert candidate_slugs("Hisuian Samurott")[0] == "samurott-hisui"

    def test_override(self):
        assert candidate_slugs("Mimikyu") == ["mimikyu-disguised"]

    def test_junk_returns_empty(self):
        assert candidate_slugs("Pokemon Champions Best Teams") == []

    def test_plain_name(self):
        assert candidate_slugs("Garchomp") == ["garchomp"]


class TestBaseFormKey:
    def test_mega(self):
        assert _base_form_key("Mega Charizard Y") == "charizard"
        assert _base_form_key("Mega Mawile") == "mawile"

    def test_regional(self):
        assert _base_form_key("Alolan Ninetales") == "ninetales"

    def test_plain_has_no_base(self):
        assert _base_form_key("Garchomp") is None


class TestTeamNameCleaning:
    def test_strips_boilerplate_and_regulation(self):
        raw = "Best Rain Team Regulation M-B: Builds and How to Play Guide"
        assert _clean_name(raw) == "Rain"

    def test_multi_word_archetype(self):
        raw = "Best Doubles Hyper Offense Teams: Builds and How to Play Guide"
        assert _clean_name(raw) == "Doubles Hyper Offense"


class TestMatchups:
    def test_charizard_y_weak_to_rock_4x(self):
        m = _matchups(["Fire", "Flying"])
        rock = next(w for w in m["weak_to"] if w["type"] == "Rock")
        assert rock["mult"] == 4.0

    def test_immunity_split_out(self):
        m = _matchups(["Ghost"])
        immune_types = {i["type"] for i in m["immune_to"]}
        assert "Normal" in immune_types and "Fighting" in immune_types


class TestRosterIntegration:
    def test_every_pokemon_has_types(self):
        roster = load_roster()
        typeless = [p["name"] for p in roster.values() if not p["types"]]
        assert typeless == []

    def test_megas_get_types_from_enrichment(self):
        roster = load_roster()
        assert roster["mega charizard y"]["types"] == ["Fire", "Flying"]

    def test_junk_entry_dropped(self):
        roster = load_roster()
        assert "pokemon champions best teams" not in roster


class TestTeamSuggestions:
    def _roster_list(self):
        return list(load_roster().values())

    def test_suggests_pokemon_not_already_in_team(self):
        roster = self._roster_list()
        current = [roster[0], roster[1]]
        out = suggest_additions(current, roster, limit=5)
        names = {s["name"] for s in out["suggestions"]}
        assert current[0]["name"] not in names
        assert current[1]["name"] not in names
        assert 0 < len(out["suggestions"]) <= 5

    def test_flags_stacked_weakness_and_resist_types(self):
        roster = {p["name"].lower(): p for p in self._roster_list()}
        team = [roster[n] for n in ("garchomp", "hippowdon", "archaludon") if n in roster]
        out = suggest_additions(team, list(roster.values()))
        # Garchomp + Hippowdon + Archaludon all take super-effective Ice damage.
        assert "Ice" in out["weak_spots"]
        # Steel resists Ice, so it should be recommended defensively.
        assert "Steel" in out["defensive_types_needed"]
