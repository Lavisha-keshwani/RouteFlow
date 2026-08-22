"""Unit tests for zone detection text matching (pure domain logic)."""
from app.domain.zones import AreaAlias, match_area, normalize_text


AREAS = [
    AreaAlias(area_id=1, zone_id=10, name="T Nagar"),
    AreaAlias(area_id=2, zone_id=10, name="Anna Nagar"),
    AreaAlias(area_id=3, zone_id=20, name="Velachery"),
    AreaAlias(area_id=4, zone_id=20, name="Adyar"),
    AreaAlias(area_id=5, zone_id=10, name="Anna Nagar West"),
]


class TestNormalize:
    def test_lowercases_and_strips_punctuation(self):
        assert normalize_text("12, Gandhi Road!") == "12 gandhi road"

    def test_collapses_whitespace(self):
        assert normalize_text("  a   b  ") == "a b"


class TestMatchArea:
    def test_matches_area_within_address(self):
        match = match_area("12 Gandhi Road, Velachery", AREAS)
        assert match is not None
        assert match.area_id == 3
        assert match.zone_id == 20

    def test_unknown_area_returns_none(self):
        assert match_area("Somewhere Unknown, Mumbai", AREAS) is None

    def test_prefers_longer_specific_match(self):
        # "Anna Nagar West" should win over "Anna Nagar"
        match = match_area("5th Ave, Anna Nagar West", AREAS)
        assert match is not None
        assert match.area_id == 5

    def test_empty_address_returns_none(self):
        assert match_area("", AREAS) is None

    def test_word_boundary_prevents_false_substring(self):
        # "Adyar" should not match inside an unrelated token like "Adyarville"
        match = match_area("Adyarville Complex", AREAS)
        assert match is None
