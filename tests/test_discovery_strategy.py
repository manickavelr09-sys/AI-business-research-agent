from research_agent.discovery import build_discovery_queries, build_source_plan, result_relevance_score
from research_agent.locality import category_expansions
from research_agent.models import SearchQuery, SearchResult
from research_agent.query_parser import infer_industry


def test_universal_category_expansions_cover_common_businesses() -> None:
    assert "plumbing contractor" in category_expansions("plumbers")
    assert "cardiology clinic" in category_expansions("cardiologists")
    assert "heart specialist" in category_expansions("cardiologists")
    assert "coffee shop" in category_expansions("cafes")
    assert "showroom" in category_expansions("shopping")
    assert "beauty parlour" in category_expansions("salons")
    assert "electrical works" in category_expansions("electricians")
    assert "wiring service" in category_expansions("electricians")
    assert "medical store" in category_expansions("pharmacies")
    assert "property consultant" in category_expansions("real estate agents")


def test_industry_router_handles_non_medical_businesses() -> None:
    assert infer_industry("restaurants") == "food_hospitality"
    assert infer_industry("shopping stores") == "retail"
    assert infer_industry("gyms") == "wellness"
    assert infer_industry("schools") == "education"


def test_discovery_queries_include_contact_and_industry_sources() -> None:
    query = SearchQuery(raw="restaurants in trichy", category="restaurants", location="tiruchirappalli")
    queries = build_discovery_queries(query)

    assert any("official website" in item for item in queries)
    assert any("menu photos reviews" in item for item in queries)
    assert any("site:zomato.com" in item for item in queries)


def test_source_plan_balances_maps_directories_social_and_leads() -> None:
    query = SearchQuery(raw="restaurants in kanyakumari", category="restaurants", location="kanyakumari")
    plan = build_source_plan(query, budget=24)
    groups = {item.source_group for item in plan}

    assert len(plan) == 24
    assert {"places", "directory", "official", "review", "social", "lead_article"}.issubset(groups)
    assert any("site:facebook.com" in item.query for item in plan)
    assert any("site:quora.com" in item.query for item in plan)
    assert any("services" in item.query or "menu" in item.query for item in plan)


def test_relevance_uses_expanded_category_terms() -> None:
    query = SearchQuery(raw="cafes in trichy", category="cafes", location="tiruchirappalli")
    result = SearchResult(
        title="Best coffee shop in Trichy",
        url="https://example.com/coffee-shop-trichy",
        snippet="Cafe and coffee shop in Tiruchirappalli with phone number",
        provider="test",
        rank=1,
    )

    assert result_relevance_score(result, query) >= 0.9
