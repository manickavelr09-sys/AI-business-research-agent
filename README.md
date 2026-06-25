# AI Business Research Agent

Enterprise-grade public web research agent for business discovery, verification, deduplication, structured extraction, and report generation.

The project is intentionally API-free by default: it uses public search/result pages and official websites through open-source tooling, with a pluggable provider layer for directories, professional registries, and licensing sources. It does not invent missing fields. Every extracted value is attached to source evidence and confidence metadata.

## Capabilities

- Parses natural language queries such as `Cardiologists in Birmingham`.
- Searches multiple public web surfaces using provider adapters.
- Expands source coverage with industry-aware query variants.
- Extracts business names, addresses, phones, emails, websites, hours, ratings, services, specialties, licenses, certifications, awards, social profiles, images, and source URLs where found.
- Cross-checks field values across sources and flags conflicts.
- Deduplicates businesses using normalized name, phone, domain, and address signals.
- Scores source reliability by source type, field consistency, and completeness.
- Streams newly discovered/merged businesses while research continues.
- Caches search pages and fetched documents in SQLite to reduce repeated work.
- Produces JSON research reports suitable for database storage and downstream analysis.

## Stack

- Python 3.11+
- FastAPI + NDJSON streaming
- Async HTTP with httpx
- BeautifulSoup/lxml extraction
- SQLite cache, no external database required
- Optional MongoDB persistence for research runs and business records
- Optional Serper Places/Search for broad local business discovery across restaurants, shops, services, trades, and professionals
- Optional Tavily Search for agent-friendly web evidence retrieval
- Optional Google Places enrichment for map-grade address, phone, rating, reviews, and hours
- CLI and web console
- Optional Playwright provider hook for browser-backed public pages
- No Docker

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
python -m uvicorn research_agent.api:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

CLI:

```powershell
research-agent "Cardiologists in Birmingham" --limit 200 --json-out report.json
```

MongoDB persistence is enabled when `MONGO_URI` is set:

```powershell
$env:MONGO_URI="mongodb://127.0.0.1:27017"
research-agent "Dentists in Austin" --limit 250
```

SQLite remains the local cache for HTTP/search responses; MongoDB stores final research runs and upserted business profiles.

Google Maps/Places enrichment is enabled when `GOOGLE_MAPS_API_KEY` is set. The agent uses the official Places API path instead of scraping Google Maps pages:

```powershell
$env:GOOGLE_MAPS_API_KEY="your-key"
research-agent "Dental clinics in Thanjavur" --limit 200
```

This is the recommended way to get reliable local phone numbers, addresses, ratings, review counts, and map URLs.

Geoapify enrichment is enabled when `GEOAPIFY_API_KEY` is set. It is a strong free-tier option for local discovery from OpenStreetMap-powered place data:

```powershell
$env:GEOAPIFY_API_KEY="your-key"
$env:GEOAPIFY_FALLBACK_API_KEY="optional-second-key"
research-agent "Doctors in Thanjavur" --limit 200
```

Geoapify is especially useful for names, addresses, coordinates, categories, websites, email, phone numbers when present in OSM, and opening hours when present. It does not provide Google review counts.

Serper discovery is enabled when `SERPER_API_KEY` is set. It adds Google-style Places and Search coverage, which is the strongest free/low-cost upgrade for universal local business categories:

```powershell
$env:SERPER_API_KEY="your-key"
research-agent "Electricians in Trichy" --limit 200
research-agent "Restaurants in Austin" --limit 200
research-agent "Shopping stores in Dallas" --limit 200
research-agent "Hotels in Tamilnadu" --limit 200
```

Tavily discovery is enabled when `TAVILY_API_KEY` is set. It adds agent-oriented web search evidence for official sites, directories, source snippets, and RAG-style retrieval:

```powershell
$env:TAVILY_API_KEY="your-key"
research-agent "Plumbers in Houston" --limit 200
```

Recommended free/low-cost stack:

```powershell
$env:GEOAPIFY_API_KEY="your-key"
$env:GEOAPIFY_FALLBACK_API_KEY="optional-second-key"
$env:SERPER_API_KEY="your-key"
$env:TAVILY_API_KEY="your-key"
$env:LLM_API_KEY="your-openai-compatible-key"
$env:LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
$env:LLM_MODEL="gemini-3.5-flash"
python -m uvicorn research_agent.api:app --host 127.0.0.1 --port 8000
```

## Deploy On Vercel

This project is configured for Vercel's Python runtime through `tool.vercel.entrypoint` in `pyproject.toml`.

Required production environment variables:

```text
GEOAPIFY_API_KEY
GEOAPIFY_FALLBACK_API_KEY
SERPER_API_KEY
TAVILY_API_KEY
LLM_API_KEY
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.5-flash
LLM_SUMMARY_ENABLED=true
RESEARCH_ENRICHMENT_TIMEOUT_SECONDS=8
RESEARCH_SEARCH_TIMEOUT_SECONDS=12
RESEARCH_EXTRACTION_TIMEOUT_SECONDS=30
RESEARCH_CONCURRENCY=8
```

Optional:

```text
MONGO_URI
MONGO_DATABASE
GOOGLE_MAPS_API_KEY
```

On Vercel, the SQLite HTTP/search cache automatically uses `/tmp/research_agent.sqlite3`, because serverless deployments should not write to the read-only project bundle. For persistent storage, set `MONGO_URI`.

The LLM variables are optional. When no LLM key is configured, the agent still creates a deterministic RAG-style summary from retrieved evidence chunks. When an OpenAI-compatible key is configured, the LLM receives only verified evidence snippets and is instructed not to invent missing business fields.

## Notes On Public Data

This code is designed for publicly available information. Some targets rate-limit, block automated traffic, or disallow scraping in their terms or robots rules. The default client has robots.txt checks enabled, conservative request headers, timeouts, caching, and concurrency controls. For production use, review each source's terms and configure allow/deny policies for your jurisdiction and use case.

## Architecture

```text
User Query
  -> query parser
  -> industry-aware discovery plan
  -> search providers
  -> URL fetch/cache
  -> page and snippet extractors
  -> evidence store
  -> dedupe/merge
  -> verification/conflict scoring
  -> streaming events + final report
```

## Example Response Shape

```json
{
  "business_name": "Example Heart Clinic",
  "address": {
    "value": "100 Main St, Birmingham, AL",
    "confidence": 0.91,
    "verified_level": "high",
    "sources": ["https://example.com/contact", "https://directory.example/listing"]
  },
  "phone": {
    "value": "(205) 555-0123",
    "confidence": 0.95,
    "verified_level": "high",
    "sources": ["https://example.com/contact"]
  },
  "website": "https://example.com",
  "services": ["Cardiology", "Echocardiogram"],
  "source_urls": {
    "phone": ["https://example.com/contact"],
    "working_hours": ["https://directory.example/listing"]
  },
  "conflicts": {}
}
```

## Scaling

For tens of thousands of records, run multiple CLI jobs with distinct query partitions, increase `RESEARCH_CONCURRENCY` cautiously, keep SQLite on a local SSD, and export NDJSON into a queue or analytical store. The core pipeline is stream-first, so records are available before the full crawl completes.
