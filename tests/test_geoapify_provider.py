from research_agent.geoapify_provider import GeoapifyProvider


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
