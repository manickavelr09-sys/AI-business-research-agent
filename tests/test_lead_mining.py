from research_agent.extraction import extract_business_from_html, extract_business_leads_from_html, record_from_search_result
from research_agent.models import SearchResult


def test_extract_business_leads_from_generic_restaurant_article() -> None:
    html = """
    <html>
      <title>What are the must-try restaurants in Ooty?</title>
      <body>
        <h2>Place to Bee</h2>
        <h2>Ascot Multi Cuisine Restaurant</h2>
        <h2>Best places to eat in Ooty</h2>
        <ul>
          <li>Angaara Restaurant Ooty</li>
          <li>Pankaj Bhojanalaya is a well-regarded pure vegetarian restaurant in Ooty.</li>
          <li>Read more</li>
        </ul>
      </body>
    </html>
    """

    leads = extract_business_leads_from_html(
        "https://www.quora.com/What-are-the-must-try-restaurants-in-Ooty",
        html,
        "restaurants",
        "ooty",
    )

    names = [lead.evidence[0].value for lead in leads]
    assert "Place to Bee" in names
    assert "Ascot Multi Cuisine Restaurant" in names
    assert "Angaara Restaurant Ooty" in names
    assert "Pankaj Bhojanalaya" in names
    assert "Best places to eat in Ooty" not in names


def test_listicle_search_result_does_not_become_business_name() -> None:
    record = record_from_search_result(
        SearchResult(
            title="Famous 14 Restaurants in Kanyakumari for Culinary Delights",
            url="https://travelmax.in/india/tamil-nadu/kanyakumari/famous-14-restaurants-in-kanyakumari-for-culinary-delights/",
            snippet="A guide to restaurants in Kanyakumari.",
            provider="test",
            rank=1,
        )
    )

    assert record.business_name == ""


def test_extracts_business_names_from_json_ld_item_list() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "ItemList",
      "itemListElement": [
        {"@type": "ListItem", "item": {"@type": "Restaurant", "name": "Sea View Restaurant"}},
        {"@type": "ListItem", "item": {"@type": "Restaurant", "name": "The Curry"}}
      ]
    }
    </script>
    """

    leads = extract_business_leads_from_html("https://example.com/restaurants", html, "restaurants", "kanyakumari")
    names = [lead.evidence[0].value for lead in leads]

    assert "Sea View Restaurant" in names
    assert "The Curry" in names


def test_structured_data_services_are_extracted() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "Restaurant",
      "name": "Sea View Restaurant",
      "telephone": "+91 76959 59109",
      "servesCuisine": ["Seafood", "South Indian"],
      "menu": "https://example.com/menu"
    }
    </script>
    """

    record = extract_business_from_html("https://seaview.example", html)

    service_values = [item.value for item in record.evidence if item.field == "services"]
    assert ["Seafood", "South Indian"] in service_values
    assert "https://example.com/menu" in service_values
