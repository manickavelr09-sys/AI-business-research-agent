from research_agent.models import SearchQuery
from research_agent.serper_provider import SerperPlacesProvider


def test_serper_place_record_maps_core_business_fields() -> None:
    provider = SerperPlacesProvider.__new__(SerperPlacesProvider)
    record = provider._record_from_place(
        {
            "title": "Sri Balaji Dental Care",
            "address": "Thanjavur, Tamil Nadu",
            "phoneNumber": "098944 88736",
            "website": "https://example.com",
            "rating": 4.8,
            "ratingCount": 42,
            "category": "Dental clinic",
            "thumbnailUrl": "https://example.com/photo.jpg",
        }
    )

    assert record.business_name == ""
    assert record.evidence[0].field == "business_name"
    assert record.evidence[0].value == "Sri Balaji Dental Care"
    assert any(item.field == "phone" and item.value == "098944 88736" for item in record.evidence)
    assert any(item.field == "rating" and item.value == "4.8" for item in record.evidence)
    assert any(item.field == "review_count" and item.value == "42" for item in record.evidence)


def test_serper_query_expansion_is_general_business_friendly() -> None:
    provider = SerperPlacesProvider.__new__(SerperPlacesProvider)
    query = SearchQuery(raw="restaurants in trichy", category="restaurants", location="trichy")

    assert "restaurants in trichy" in provider._queries(query)


def test_serper_query_expands_state_level_location() -> None:
    provider = SerperPlacesProvider.__new__(SerperPlacesProvider)
    query = SearchQuery(raw="dentists in tamilnadu", category="dentists", location="tamil nadu")
    queries = provider._queries(query)

    assert "dentists in chennai" in queries
    assert "dentists in coimbatore" in queries
    assert "dentists in madurai" in queries
    assert len(queries) > 20
