from research_agent.models import BusinessRecord, SearchQuery
from research_agent.record_quality import should_stream_record


def test_restaurant_article_title_is_rejected_cross_category() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Where to eat in Ooty: best restaurants, cafes and local food guide",
        website="https://example.com/ooty-food-guide",
    )
    assert not should_stream_record(record, query, "web")


def test_shopping_supplier_directory_title_is_rejected_cross_category() -> None:
    query = SearchQuery(raw="shops in karaikudi", category="shops", location="karaikudi")
    record = BusinessRecord(
        business_name="Top Suppliers in Karaikudi - Check Prices and Reviews",
        phone="+91 99999 99999",
        website="https://example.com/suppliers-karaikudi",
    )
    assert not should_stream_record(record, query, "web")


def test_salon_booking_category_page_is_rejected_cross_category() -> None:
    query = SearchQuery(raw="salons in trichy", category="salons", location="trichy")
    record = BusinessRecord(
        business_name="Beauty Salons Near You in Trichy - Book Online",
        website="https://example.com/salons-trichy",
    )
    assert not should_stream_record(record, query, "web")


def test_named_business_with_fields_is_kept_cross_category() -> None:
    query = SearchQuery(raw="salons in trichy", category="salons", location="trichy")
    record = BusinessRecord(
        business_name="Green Trends Salon",
        address="Trichy, Tamil Nadu",
        phone="+91 99999 99999",
        website="https://example.com/green-trends-trichy",
    )
    assert should_stream_record(record, query, "web")


def test_phone_numbers_directory_title_is_rejected_cross_category() -> None:
    query = SearchQuery(raw="electricians in karaikudi", category="electricians", location="karaikudi")
    record = BusinessRecord(
        business_name="Electricians Phone Numbers in Karaikudi",
        phone="+91 99999 99999",
        website="https://example.com/electricians-phone-numbers-karaikudi",
    )
    assert not should_stream_record(record, query, "web")


def test_at_site_directory_name_is_rejected_cross_category() -> None:
    query = SearchQuery(raw="restaurants in ooty", category="restaurants", location="ooty")
    record = BusinessRecord(
        business_name="Ooty @Bharpet.com",
        website="https://example.com/ooty-restaurants",
    )
    assert not should_stream_record(record, query, "web")
