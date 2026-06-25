from research_agent.geoapify_provider import GeoapifyProvider, _detail_enrichment_limit, _geocode_aliases
from research_agent.verification import verify_record


def test_geoapify_category_mapping_for_dentists() -> None:
    provider = GeoapifyProvider.__new__(GeoapifyProvider)
    assert provider._categories("dentists") == ["healthcare.dentist"]


def test_geoapify_category_mapping_for_doctors() -> None:
    provider = GeoapifyProvider.__new__(GeoapifyProvider)
    categories = provider._categories("doctors")
    assert "healthcare.clinic_or_praxis.general" in categories
    assert "healthcare.hospital" in categories


def test_geoapify_category_mapping_for_restaurants() -> None:
    provider = GeoapifyProvider.__new__(GeoapifyProvider)
    assert provider._categories("restaurants") == ["catering.restaurant"]


def test_geoapify_electricians_do_not_map_to_hardware_only() -> None:
    provider = GeoapifyProvider.__new__(GeoapifyProvider)
    categories = provider._categories("electricians")
    assert "commercial.houseware_and_hardware.hardware_and_tools" not in categories
    assert "service" in categories


def test_geoapify_geocoding_uses_parent_region_for_ambiguous_city() -> None:
    aliases = _geocode_aliases("kochi", "kerala")

    assert aliases[0] == "kochi, kerala"
    assert aliases[1] == "kochi, kerala, India"
    assert "kochi" in aliases


def test_geoapify_does_not_turn_address_line_into_business_name() -> None:
    provider = GeoapifyProvider.__new__(GeoapifyProvider)
    record = provider._record_from_feature(
        {
            "properties": {
                "address_line1": "Vypin - Pallippuram Road",
                "formatted": "Vypin - Pallippuram Road, Fort Kochi, Kerala, India",
                "lat": 9.9,
                "lon": 76.2,
            }
        }
    )

    verified = verify_record(record)

    assert verified.business_name == ""
    assert verified.address == "Vypin - Pallippuram Road, Fort Kochi, Kerala, India"


def test_geoapify_detail_enrichment_is_capped_for_broad_searches() -> None:
    assert _detail_enrichment_limit(10) == 10
    assert _detail_enrichment_limit(100) == 40
    assert _detail_enrichment_limit(250) == 50
