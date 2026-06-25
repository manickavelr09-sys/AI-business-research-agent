# Judging Guide

This guide explains how to evaluate the AI Business Research Agent quickly and fairly.

## Objective

The system finds, verifies, deduplicates, organizes, and summarizes business information from public internet sources. It is designed for broad local business research across categories and regions.

Example queries:

```text
Cardiologists in Birmingham
Dentists in Austin
Hotels in Tamilnadu
Electricians in Trichy
Restaurants in Kanyakumari
Plumbers in Houston
Family lawyers in Chicago
```

## Recommended Demo Flow

1. Start the app:

```powershell
python -m uvicorn research_agent.api:app --host 127.0.0.1 --port 8000
```

2. Open:

```text
http://127.0.0.1:8000/
```

3. Check system readiness:

```text
The readiness panel should show configured map, search, intelligence, and storage providers.
```

4. Run a broad regional query:

```text
hotels in tamilnadu
limit: 200
```

5. Inspect:

```text
Business count
Verified count
Duplicate records removed
Data quality percentages
Individual field evidence links
Conflict status
PDF report download
```

6. Run a precise local query:

```text
dentists in thanjavur
limit: 50
```

7. Run a service-category query:

```text
electricians in trichy
limit: 50
```

## What To Look For

The project should be evaluated on these dimensions:

| Area | What The System Does |
| --- | --- |
| Query understanding | Extracts business category and location from natural language |
| Search breadth | Uses maps, search engines, directories, official sites, and public pages |
| Region scaling | Expands state-level locations into major cities |
| Evidence extraction | Collects fields with source URLs instead of unsupported guesses |
| Verification | Scores confidence and marks low, medium, or high verification |
| Conflict handling | Flags conflicting values instead of hiding them |
| Deduplication | Merges likely duplicates while avoiding false merges from generic map URLs |
| Streaming | Shows businesses while research is still in progress |
| Reporting | Produces structured JSON and downloadable PDF |
| Readiness | Shows provider configuration and capability status |

## Requirement Mapping

| Challenge Requirement | Implementation |
| --- | --- |
| Understand category and location | `query_parser.py`, `locality.py` |
| Search multiple public sources | `search_providers.py`, `geoapify_provider.py`, `places_provider.py`, `serper_provider.py` |
| Discover relevant businesses | Map providers, search query planner, lead mining |
| Collect business fields | `extraction.py`, provider-specific adapters |
| Verify by comparing sources | `verification.py` |
| Remove duplicates | `dedupe.py` |
| Structured results | `models.py`, JSON report payload |
| Research summary | `agentic_rag.py` |
| Stream results | `/research/stream` NDJSON endpoint |
| Cache repeated work | `storage.py` SQLite cache |
| Source reliability scoring | `source_reliability.py`, verification scoring |
| PDF export | `pdf_report.py`, `/research/pdf` |
| Optional database storage | `mongo_store.py` |

## Provider Readiness

Use:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/readiness -UseBasicParsing
```

Interpretation:

```text
ready: at least one map provider and one search provider are available
degraded: the app can run, but some provider classes are missing keys
```

Recommended provider setup for the strongest demo:

```text
Geoapify: place discovery and addresses
Google Places API New: phones, ratings, review counts, hours, websites
Serper: Google-style search and places
Tavily: web evidence and RAG support
Gemini/OpenAI-compatible LLM: evidence-only summary
```

## Evaluation Notes

The system intentionally leaves unavailable fields blank. This is a feature, not a failure. The challenge states that the agent must not invent or estimate information.

For public web research, field coverage varies by region and category:

```text
Names and addresses: usually high with map providers
Phones: best with Google Places or Serper Places
Ratings and review counts: best with Google Places
Hours: depends on provider availability
License data: needs industry and jurisdiction-specific adapters
Social profiles: mostly available when indexed publicly
```

## Suggested Judge Test Cases

Use a mix of broad and precise searches:

```text
hotels in tamilnadu
dentists in kerala
electricians in trichy
restaurants in kanyakumari
cardiologists in birmingham
plumbers in houston
family lawyers in chicago
roofing contractors in dallas
```

For broad state-level tests, use limits between 100 and 200. For city-level tests, use limits between 25 and 75.

## Design Decisions

- The system uses provider APIs where available instead of scraping protected map pages.
- It treats listicles and Q&A pages as lead sources, not final business records.
- It over-collects raw candidates before deduplication so final result counts are closer to the requested limit.
- It avoids false duplicate merges from generic map source URLs.
- It exposes source evidence in the UI because judge trust depends on visible provenance.

## Commands For Verification

```powershell
python -m pytest
python -m compileall research_agent
```

Expected result:

```text
All tests pass.
```
