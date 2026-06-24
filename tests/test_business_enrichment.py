from research_agent.business_enrichment import (
    _important_tokens,
    _is_generic_directory_page,
    _search_result_matches,
)
from research_agent.models import BusinessRecord, SearchQuery, SearchResult


def test_important_tokens_remove_generic_words() -> None:
    assert _important_tokens("Rhagam Dental Care Hospital") == ["rhagam"]


def test_exact_business_search_result_matches() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    record = BusinessRecord(business_name="Rhagam Dental Care Hospital")
    result = SearchResult(
        title="Rhagam Dental Care Hospital Thanjavur phone number",
        url="https://example.com/rhagam-dental-care-hospital-thanjavur",
        snippet="Contact address and phone number in Thanjavur",
        provider="test",
        rank=1,
    )
    assert _search_result_matches(result, record, query)


def test_generic_directory_page_does_not_match_business() -> None:
    query = SearchQuery(raw="dentists in thanjavur", category="dentists", location="thanjavur")
    assert _is_generic_directory_page("https://www.practo.com/thanjavur/dentist", query)
