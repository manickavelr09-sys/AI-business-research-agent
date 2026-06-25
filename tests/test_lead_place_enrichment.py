import pytest

from research_agent.config import Settings
from research_agent.models import BusinessRecord, SearchQuery, SourceEvidence
from research_agent.orchestrator import ResearchAgent, _place_candidate_matches_lead


class FakePlacesProvider:
    enabled = True

    async def search(self, query: SearchQuery, limit: int = 4) -> list[BusinessRecord]:
        record = BusinessRecord()
        record.add_evidence(SourceEvidence("business_name", "Sea View Restaurant", "https://maps.example/sea", "serper_places", 0.86))
        record.add_evidence(SourceEvidence("address", "E Car St, Kanyakumari, Tamil Nadu", "https://maps.example/sea", "serper_places", 0.86))
        record.add_evidence(SourceEvidence("phone", "+91 76959 59109", "https://maps.example/sea", "serper_places", 0.86))
        record.add_evidence(SourceEvidence("rating", "4.4", "https://maps.example/sea", "serper_places", 0.86))
        return [record]


class DisabledPlacesProvider:
    enabled = False


@pytest.mark.anyio
async def test_mined_lead_is_enriched_with_exact_place_lookup(tmp_path) -> None:
    settings = Settings(cache_path=tmp_path / "cache.sqlite3", serper_api_key="test")
    agent = ResearchAgent(settings)
    agent.serper_places = FakePlacesProvider()
    agent.places = DisabledPlacesProvider()
    lead = BusinessRecord()
    lead.add_evidence(SourceEvidence("business_name", "Sea View Restaurant", "https://article.example/top-restaurants", "article_lead", 0.36))
    parsed = SearchQuery(raw="restaurants in kanyakumari", category="restaurants", location="kanyakumari")

    try:
        enriched = await agent._enrich_leads_with_places([lead], parsed, [])
    finally:
        await agent.close()

    assert len(enriched) == 1
    assert enriched[0].business_name == "Sea View Restaurant"
    assert enriched[0].phone == "+91 76959 59109"
    assert "Kanyakumari" in enriched[0].address
    assert enriched[0].rating == "4.4"


def test_place_candidate_match_rejects_generic_category_overlap() -> None:
    lead = BusinessRecord(business_name="Sea View Restaurant")
    wrong = BusinessRecord(business_name="Best Restaurant Directory")

    assert not _place_candidate_matches_lead(lead, wrong)
