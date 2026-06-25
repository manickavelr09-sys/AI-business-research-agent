from __future__ import annotations

import json
import re
from typing import Annotated

from fastapi import Body, FastAPI, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from research_agent.config import settings
from research_agent.orchestrator import ResearchAgent
from research_agent.pdf_report import build_research_pdf

app = FastAPI(
    title="AI Business Research Agent",
    version="0.1.0",
    description="Public web business research, verification, dedupe, and structured reporting.",
)
app.mount("/static", StaticFiles(directory="research_agent/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    with open("research_agent/static/index.html", "r", encoding="utf-8") as handle:
        return handle.read()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readiness")
async def readiness() -> dict[str, object]:
    providers = {
        "maps": {
            "geoapify": bool(settings.geoapify_api_key or settings.geoapify_fallback_api_key),
            "google_places": bool(settings.google_maps_api_key),
            "serper_places": bool(settings.serper_api_key),
        },
        "search": {
            "serper_search": bool(settings.serper_api_key),
            "tavily_search": bool(settings.tavily_api_key),
            "duckduckgo_html": True,
            "bing_html": True,
        },
        "intelligence": {
            "rag_summary": True,
            "llm_summary": bool(settings.llm_summary_enabled and settings.llm_api_key),
        },
        "storage": {
            "sqlite_cache": True,
            "mongo_reports": bool(settings.mongo_uri),
            "pdf_export": True,
        },
    }
    map_ready = any(providers["maps"].values())
    search_ready = any(providers["search"].values())
    warnings = []
    if not map_ready:
        warnings.append("Maps are disabled. Add SERPER_API_KEY, GEOAPIFY_API_KEY, or GOOGLE_MAPS_API_KEY for high-volume phone/address coverage.")
    if not bool(settings.serper_api_key):
        warnings.append("Serper is disabled. Google-style places and search coverage will be limited.")
    if not bool(settings.tavily_api_key):
        warnings.append("Tavily is disabled. RAG evidence discovery will rely more on HTML search fallback.")
    if settings.llm_summary_enabled and not settings.llm_api_key:
        warnings.append("LLM summaries are disabled because no LLM_API_KEY is configured; evidence-only RAG summaries still work.")
    return {
        "status": "ready" if search_ready and map_ready else "degraded",
        "providers": providers,
        "capabilities": {
            "multi_source_discovery": search_ready,
            "map_backed_enrichment": map_ready,
            "lead_mining_from_list_pages": True,
            "exact_name_places_lookup": map_ready,
            "verification_and_conflict_detection": True,
            "deduplication": True,
            "streaming_results": True,
            "pdf_report": True,
            "region_fanout": True,
        },
        "warnings": warnings,
    }


@app.get("/research/stream")
async def research_stream(
    query: Annotated[str, Query(min_length=3)],
    limit: Annotated[int | None, Query(ge=1, le=5000)] = None,
) -> StreamingResponse:
    async def events():
        agent = ResearchAgent()
        try:
            async for event in agent.research_stream(query, limit=limit):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            await agent.close()

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.post("/research/pdf")
async def research_pdf(report: Annotated[dict, Body(...)]) -> Response:
    pdf_bytes = build_research_pdf(report)
    query = report.get("search_summary", {}).get("query", "business-research")
    filename = _filename(query)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


def _filename(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "business-research-report"
