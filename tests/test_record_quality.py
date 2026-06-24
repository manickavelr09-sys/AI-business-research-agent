from research_agent.models import BusinessRecord, SearchQuery
from research_agent.record_quality import should_stream_record


def test_generic_directory_page_is_rejected() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Best Dentists in Thanjavur",
        website="https://www.justdial.com/Thanjavur/Dentists/nct-10156331",
    )
    assert not should_stream_record(record, query, "web")


def test_generic_directory_with_support_email_is_rejected() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Dentists in Thanjavur",
        email="support@dentee.com",
        rating="5",
        website="https://www.dentee.com/dentists/thanjavur",
    )
    assert not should_stream_record(record, query, "web")


def test_singular_generic_business_title_is_rejected_even_with_phone() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Dentist in Thanjavur",
        phone="9894888736",
        website="https://lokadentalcentre.com/",
    )
    assert not should_stream_record(record, query, "web")


def test_generic_title_with_extra_directory_text_is_rejected() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Dentists in Thanjavur, India • Check Prices & Reviews",
        website="https://www.whatclinic.com/dentists/india/thanjavur",
    )
    assert not should_stream_record(record, query, "web")


def test_generic_alias_title_near_me_is_rejected() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Best Dental Clinics Near Me in Thanjavur",
        phone="1800102102",
        website="https://www.practo.com/thanjavur/dentist",
    )
    assert not should_stream_record(record, query, "web")


def test_named_alias_business_is_kept() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Diamond Dental Clinic in Thanjavur",
        phone="9894888736",
        website="https://example.com/diamond-dental-clinic-thanjavur",
    )
    assert should_stream_record(record, query, "web")


def test_geoapify_business_with_address_is_kept() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(
        business_name="Rhagam Dental Care Hospital",
        address="South Rampart Street, Thanjavur, Tamil Nadu",
        website="https://www.openstreetmap.org/",
    )
    assert should_stream_record(record, query, "geoapify")


def test_off_location_business_is_rejected() -> None:
    query = SearchQuery(raw="doctors in thanjavur", category="doctors", location="thanjavur")
    record = BusinessRecord(
        business_name="Gujarat Doctors Directory",
        address="Ahmedabad, Gujarat",
        website="https://example.com",
    )
    assert not should_stream_record(record, query, "web")
