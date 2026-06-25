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


def test_category_location_title_without_in_is_rejected() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Restaurants Ooty",
        website="https://example.com/restaurants-ooty",
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


def test_quora_question_is_not_a_business_record() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="What are the must-try restaurants in Ooty?",
        website="https://www.quora.com/What-are-the-must-try-restaurants-in-Ooty",
    )
    assert not should_stream_record(record, query, "web")


def test_travel_article_is_not_a_business_record_even_with_phone() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="The Best Places To Eat In Ooty",
        phone="8754835965",
        website="https://www.youtube.com/watch?v=xSZNwGSKWA0",
    )
    assert not should_stream_record(record, query, "web")


def test_generic_dining_page_is_not_a_restaurant_name() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Dining",
        address="137F100, Blue Mountain School Road, Ooty, Tamil Nadu",
        phone="+91 85 8585 4615",
        website="https://www.mangohillhotels.com/central-ooty/dining.html",
    )
    assert not should_stream_record(record, query, "web")


def test_named_restaurant_is_kept() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Place to Bee",
        address="Ooty-Coonoor Road, Ooty, Tamil Nadu",
        phone="+91 423 2449464",
        website="https://www.facebook.com/placet0bee",
    )
    assert should_stream_record(record, query, "serper_places")


def test_access_denied_page_is_not_business_record() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Access Denied",
        website="https://example.com/restaurants/ooty",
    )
    assert not should_stream_record(record, query, "web")


def test_marketing_restaurant_article_title_is_not_business_record() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Luxury Diner and Multi-Cuisine Restaurant Experience in Ooty",
        address="4/278, Kotagiri Road, Ooty",
        phone="+91 423 245 0021",
        website="https://www.theaccordhotels.com/highland-ooty/dining",
    )
    assert not should_stream_record(record, query, "web")


def test_sentence_style_article_lead_is_not_business_record() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="If you're travelling to the serene hills of Ooty and Coonoor, here are ...",
        website="https://example.com/ooty-food-guide",
    )
    assert not should_stream_record(record, query, "web")
