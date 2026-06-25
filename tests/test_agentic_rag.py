import pytest

from research_agent.agentic_rag import build_research_summary, retrieve_evidence_chunks
from research_agent.config import Settings
from research_agent.models import BusinessRecord, SourceEvidence
from research_agent.verification import verify_record


def test_retrieve_evidence_chunks_prefers_important_fields() -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("business_name", "ABC Electricals", "https://example.com", "official_website", 0.95))
    record.add_evidence(SourceEvidence("phone", "+91 99999 99999", "https://example.com", "official_website", 0.95))
    record.add_evidence(SourceEvidence("images_urls", ["https://example.com/a.jpg"], "https://example.com", "official_website", 0.95))

    chunks = retrieve_evidence_chunks([record])

    assert [chunk["field"] for chunk in chunks] == ["business_name", "phone"]


@pytest.mark.anyio
async def test_build_research_summary_without_llm_uses_evidence_only(tmp_path) -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("business_name", "ABC Electricals", "https://example.com", "official_website", 0.95))
    record.add_evidence(SourceEvidence("phone", "+91 99999 99999", "https://example.com", "official_website", 0.95))
    verified = verify_record(record)
    settings = Settings(cache_path=tmp_path / "cache.sqlite3", llm_api_key="")

    summary = await build_research_summary(
        "electricians in trichy",
        [verified],
        {"records_with_phone_number": "100%", "records_with_address": "0%", "records_with_rating": "0%"},
        settings,
        [],
    )

    assert summary["rag_enabled"]
    assert not summary["llm_used"]
    assert summary["retrieved_evidence_chunks"] == 2
    assert "electricians in trichy" in summary["summary"]
