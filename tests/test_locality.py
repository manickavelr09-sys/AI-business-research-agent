from research_agent.discovery import filter_result, result_relevance_score
from research_agent.locality import has_location_signal, location_aliases, normalize_location
from research_agent.models import SearchQuery, SearchResult


def test_location_typo_is_corrected() -> None:
    assert normalize_location("thamjavur") == "thanjavur"
    assert "tanjore" in location_aliases("thanjavur")
    assert "udhagamandalam" in location_aliases("ooty")


def test_ooty_location_alias_matches_official_town_name() -> None:
    assert has_location_signal("Restaurant in Udhagamandalam, The Nilgiris", "ooty")


def test_off_location_result_is_filtered() -> None:
    query = SearchQuery(raw="doctors in thanjavur", category="doctors", location="thanjavur")
    result = SearchResult(
        title="Best Doctors in Gujarat",
        url="https://example.com/gujarat-doctors",
        snippet="Top physicians in Ahmedabad Gujarat",
        provider="test",
        rank=1,
    )
    assert result_relevance_score(result, query) < 0.35
    assert not filter_result(result, query)


def test_local_result_is_kept() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    result = SearchResult(
        title="Mahatma Gandhi Dental Clinic Thanjavur",
        url="https://example.com/mahatma-gandhi-dental-clinic-thanjavur",
        snippet="Dental clinic in Thanjavur Tamil Nadu with phone number and address",
        provider="test",
        rank=1,
    )
    assert filter_result(result, query)
