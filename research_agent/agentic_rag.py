from __future__ import annotations

import json
from typing import Any

import httpx

from research_agent.config import Settings
from research_agent.models import BusinessRecord


IMPORTANT_FIELDS = {
    "business_name",
    "address",
    "phone",
    "email",
    "website",
    "working_hours",
    "rating",
    "review_count",
    "license_information",
    "services",
    "certifications",
}


async def build_research_summary(
    query: str,
    records: list[BusinessRecord],
    data_quality: dict[str, str],
    settings: Settings,
    source_errors: list[str] | None = None,
) -> dict[str, Any]:
    chunks = retrieve_evidence_chunks(records)
    summary = deterministic_summary(query, records, data_quality, chunks, source_errors or [])
    if not settings.llm_summary_enabled or not settings.llm_api_key or not chunks:
        return summary
    llm_summary = await _llm_summary(query, chunks, summary, settings)
    if llm_summary:
        summary.update(llm_summary)
        summary["llm_used"] = True
        summary["llm_model"] = settings.llm_model
    return summary


def retrieve_evidence_chunks(records: list[BusinessRecord], limit: int = 40) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for record in records:
        for evidence in record.evidence:
            if evidence.field not in IMPORTANT_FIELDS:
                continue
            chunks.append(
                {
                    "business_name": record.business_name,
                    "field": evidence.field,
                    "value": evidence.value,
                    "source_url": evidence.source_url,
                    "source_type": evidence.source_type,
                    "reliability": round(evidence.reliability, 3),
                }
            )
    chunks.sort(key=lambda item: (item["reliability"], bool(item["value"])), reverse=True)
    return chunks[:limit]


def deterministic_summary(
    query: str,
    records: list[BusinessRecord],
    data_quality: dict[str, str],
    chunks: list[dict[str, Any]],
    source_errors: list[str],
) -> dict[str, Any]:
    verified_records = sum(
        1
        for record in records
        if any(value.verified_level in {"medium", "high"} for value in record.verification.values())
    )
    source_types = sorted({chunk["source_type"] for chunk in chunks if chunk.get("source_type")})
    return {
        "rag_enabled": True,
        "llm_used": False,
        "query_understood_as": query,
        "summary": (
            f"Found {len(records)} deduplicated businesses for {query}. "
            f"{verified_records} records include at least one medium/high verified field. "
            "The report uses only retrieved public evidence and flags conflicts instead of guessing."
        ),
        "agent_steps": [
            "Parsed business category and location.",
            "Searched map/place providers, web search providers, directories, social profiles, and official websites.",
            "Extracted public evidence for business fields.",
            "Verified repeated values across sources and flagged conflicts.",
            "Deduplicated likely same businesses.",
            "Retrieved top evidence chunks for report summarization.",
        ],
        "source_strategy": source_types,
        "retrieved_evidence_chunks": len(chunks),
        "data_quality": data_quality,
        "limitations": _quality_limitations(data_quality, source_errors),
        "source_errors": source_errors[:10],
    }


def _quality_limitations(data_quality: dict[str, str], source_errors: list[str]) -> list[str]:
    limitations: list[str] = []
    if _percent(data_quality.get("records_with_phone_number", "0%")) < 60:
        limitations.append("Phone coverage is below target; official websites or paid places APIs may improve it.")
    if _percent(data_quality.get("records_with_address", "0%")) < 70:
        limitations.append("Address coverage is below target; map providers should be prioritized for this query.")
    if _percent(data_quality.get("records_with_rating", "0%")) < 50:
        limitations.append("Rating/review coverage is limited because some public sources do not expose review metadata.")
    if source_errors:
        limitations.append("Some providers returned errors/timeouts; final report was completed with partial evidence.")
    return limitations


def _percent(value: str) -> int:
    try:
        return int(str(value).strip().rstrip("%"))
    except ValueError:
        return 0


async def _llm_summary(
    query: str,
    chunks: list[dict[str, Any]],
    fallback: dict[str, Any],
    settings: Settings,
) -> dict[str, Any] | None:
    evidence_text = "\n".join(
        f"- {item['business_name']} | {item['field']}: {item['value']} | "
        f"{item['source_type']} | {item['source_url']}"
        for item in chunks[:25]
    )
    system = (
        "You are a business research QA analyst. Summarize only the provided evidence. "
        "Do not invent business names, phone numbers, addresses, ratings, licenses, or sources. "
        "Return compact JSON with keys summary, strengths, gaps, recommended_next_steps."
    )
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n"
                    f"Fallback metrics: {json.dumps(fallback, ensure_ascii=False)[:1500]}\n"
                    f"Evidence:\n{evidence_text[:8000]}"
                ),
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
        if response.status_code >= 400:
            return {"llm_error": f"LLM request failed with status {response.status_code}"}
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return {
                "summary": parsed.get("summary", fallback["summary"]),
                "llm_strengths": parsed.get("strengths", []),
                "llm_gaps": parsed.get("gaps", []),
                "recommended_next_steps": parsed.get("recommended_next_steps", []),
            }
    except Exception as exc:
        return {"llm_error": type(exc).__name__}
    return None
