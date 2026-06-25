from research_agent.places_provider import GooglePlacesProvider, _place_id_from_name
from research_agent.verification import verify_record


def test_place_id_from_new_resource_name() -> None:
    assert _place_id_from_name("places/ChIJ123") == "ChIJ123"
    assert _place_id_from_name("ChIJ123") == "ChIJ123"


def test_record_from_places_api_new_response() -> None:
    provider = GooglePlacesProvider.__new__(GooglePlacesProvider)
    provider.settings = type("Settings", (), {"google_maps_api_key": "test-key"})()
    record = provider._record_from_new_place(
        {
            "id": "ChIJ123",
            "name": "places/ChIJ123",
            "displayName": {"text": "Example Hotel"},
            "formattedAddress": "Chennai, Tamil Nadu, India",
            "nationalPhoneNumber": "044 1234 5678",
            "websiteUri": "https://example-hotel.test",
            "googleMapsUri": "https://maps.google.com/?cid=123",
            "rating": 4.4,
            "userRatingCount": 321,
            "types": ["hotel", "lodging"],
            "regularOpeningHours": {"weekdayDescriptions": ["Monday: Open 24 hours"]},
        }
    )
    verified = verify_record(record)

    assert verified.business_name == "Example Hotel"
    assert verified.address == "Chennai, Tamil Nadu, India"
    assert verified.phone == "044 1234 5678"
    assert verified.website == "https://example-hotel.test"
    assert verified.rating == "4.4"
    assert verified.review_count == "321"
    assert "hotel" in verified.services
    assert verified.working_hours == "Monday: Open 24 hours"
