from __future__ import annotations

import json
import re
from typing import Annotated

from fastapi import Body, FastAPI, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
