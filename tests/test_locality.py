from research_agent.discovery import filter_result, result_relevance_score
from research_agent.locality import expanded_search_locations, has_location_signal, location_aliases, normalize_location, region_search_locations
from research_agent.models import SearchQuery, SearchResult


def test_location_typo_is_corrected() -> None:
    assert normalize_location("thamjavur") == "thanjavur"
    assert "tanjore" in location_aliases("thanjavur")
    assert "udhagamandalam" in location_aliases("ooty")
    assert normalize_location("karaikkudi") == "karaikudi"
    assert "sivaganga" in location_aliases("karaikudi")


def test_ooty_location_alias_matches_official_town_name() -> None:
    assert has_location_signal("Restaurant in Udhagamandalam, The Nilgiris", "ooty")


def test_karaikudi_location_alias_matches_district_name() -> None:
    assert has_location_signal("Electrical works in Sivaganga district, Tamil Nadu", "karaikudi")


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


def test_state_level_location_expands_to_major_city_searches() -> None:
    assert normalize_location("tamilnadu") == "tamil nadu"
    locations = region_search_locations("tamilnadu")

    assert "chennai" in locations
    assert "coimbatore" in locations
    assert "madurai" in locations
    assert "tiruchirappalli" in locations
    assert len(expanded_search_locations("tamil nadu")) >= 10
    assert has_location_signal("Dental clinic in Chennai", "tamil nadu")
