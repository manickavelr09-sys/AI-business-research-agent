# AI Business Research Agent

An AI-assisted business research system that discovers, verifies, deduplicates, organizes, and summarizes business information from public internet sources.

The project is built for local business research queries such as:

```text
Cardiologists in Birmingham
Dentists in Austin
Hotels in Tamilnadu
Electricians in Trichy
Restaurants in Kanyakumari
Plumbers in Houston
Family lawyers in Chicago
```

The agent is designed to behave like a research analyst, not a simple scraper. It collects evidence from multiple public sources, attaches source URLs to extracted fields, flags conflicts, removes duplicates, and produces structured JSON plus a PDF report.

## Highlights

- Natural-language query parsing for business category and location.
- Broad region fanout for state-level searches such as `hotels in tamilnadu`.
- Multi-source discovery from map/place providers, web search, directories, official websites, review pages, and social/profile pages.
- Field extraction for names, addresses, phones, emails, websites, hours, ratings, review counts, services, specialties, licenses, certifications, awards, social profiles, images, and evidence URLs.
- Evidence-backed verification with confidence levels and conflict tracking.
- Deduplication using phone, website, name, and address similarity while avoiding false merges from generic map URLs.
- Streamed results in the browser while research is still running.
- Data quality summary for phone, address, website, rating, hours, services, and license coverage.
- PDF report export.
- SQLite cache for repeated searches and optional MongoDB persistence.
- Optional RAG and LLM summary layer that only summarizes retrieved evidence.
- No Docker required.

## Current Verified Behavior

The broad-region pipeline has been tested with:

```text
hotels in tamilnadu, limit 200
```

Observed result:

```text
Final businesses: 200
Address coverage: 100%
Services coverage: 100%
Phone coverage: provider-dependent
```

Phone, rating, review, and hours coverage depends heavily on provider availability. Google Places API New and Serper Places improve those fields significantly when enabled and funded.

## Technology Stack

- Python 3.11+
- FastAPI
- NDJSON streaming
- httpx async HTTP client
- BeautifulSoup and lxml extraction
- SQLite HTTP/search cache
- Optional MongoDB persistence
- ReportLab PDF generation
- Optional Geoapify Places
- Optional Google Places API New
- Optional Serper Search and Places
- Optional Tavily Search
- Optional OpenAI-compatible LLM endpoint, including Gemini OpenAI-compatible API

## Project Structure

```text
research_agent/
  api.py                 FastAPI app, readiness, streaming, PDF routes
  orchestrator.py        Agent pipeline and research workflow
  query_parser.py        Category/location parsing
  locality.py            Region fanout, aliases, country hints
  geoapify_provider.py   Geoapify place discovery
  places_provider.py     Google Places API New and legacy fallback
  serper_provider.py     Serper Places provider
  search_providers.py    Serper, Tavily, DuckDuckGo, Bing search adapters
  extraction.py          HTML, JSON-LD, contact and lead extraction
  verification.py        Evidence scoring and conflict detection
  dedupe.py              Business merge and duplicate removal
  agentic_rag.py         Evidence-only RAG and optional LLM summary
  pdf_report.py          PDF report generation
  static/                Browser UI
tests/                   Regression and pipeline tests
docs/JUDGING_GUIDE.md    Demo and evaluation guide
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
python -m uvicorn research_agent.api:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

Run a quick readiness check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/readiness -UseBasicParsing
```

Run from CLI:

```powershell
research-agent "Hotels in Tamilnadu" --limit 200 --json-out report.json
```

## Environment Variables

Start by copying `.env.example`:

```powershell
copy .env.example .env
```

Recommended local configuration:

```text
GEOAPIFY_API_KEY=your-key
GEOAPIFY_FALLBACK_API_KEY=optional-second-key
GOOGLE_MAPS_API_KEY=your-google-key
SERPER_API_KEY=your-serper-key
TAVILY_API_KEY=your-tavily-key
LLM_API_KEY=your-openai-compatible-key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.5-flash
LLM_SUMMARY_ENABLED=true
```

Optional persistence:

```text
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DATABASE=business_research
```

## Provider Roles

| Provider | Role | Best For |
| --- | --- | --- |
| Geoapify | Place discovery from OpenStreetMap data | Names, addresses, categories, coordinates, some websites and phones |
| Google Places API New | Official map-grade enrichment | Phone, address, rating, review count, hours, website |
| Serper Search | Google-style web search | Official sites, directories, indexed business pages |
| Serper Places | Google-style place discovery | Local business names, addresses, phones, ratings |
| Tavily | Search and evidence retrieval | RAG evidence, source snippets, official pages |
| DuckDuckGo and Bing HTML | Fallback public search | No-key discovery coverage |
| Optional LLM | Evidence-only summary | Explaining strengths, gaps, and next steps |

The agent does not invent missing fields. If a field cannot be found from public evidence, it remains empty.

## API Endpoints

```text
GET  /                         Browser UI
GET  /health                   Basic health check
GET  /readiness                Provider and capability readiness
GET  /research/stream          NDJSON research stream
POST /research/pdf             Generate PDF from a report payload
```

Example stream call:

```powershell
Invoke-WebRequest "http://127.0.0.1:8000/research/stream?query=hotels%20in%20tamilnadu&limit=200" -UseBasicParsing
```

## Report Shape

Each final report contains:

```json
{
  "search_summary": {
    "query": "hotels in tamil nadu",
    "businesses_found": 200,
    "businesses_verified": 16,
    "duplicate_records_removed": 101,
    "sources_searched": 171,
    "research_duration": "124.00 seconds"
  },
  "data_quality_summary": {
    "records_with_website": "25%",
    "records_with_phone_number": "38%",
    "records_with_address": "100%",
    "records_with_rating": "0%",
    "records_with_services": "100%"
  },
  "business_results": [
    {
      "business_name": "Example Hotel",
      "address": "Chennai, Tamil Nadu, India",
      "phone": "",
      "website": "https://example.com",
      "services": ["lodging", "hotel"],
      "source_urls": {
        "address": ["https://source.example/listing"]
      },
      "verification": {
        "address": {
          "value": "Chennai, Tamil Nadu, India",
          "confidence": 0.82,
          "verified_level": "medium",
          "sources": ["https://source.example/listing"]
        }
      },
      "conflicts": {}
    }
  ]
}
```

## Verification Strategy

The agent scores fields using:

- Source type reliability.
- Repeated values across independent sources.
- Completeness of the record.
- Conflicting value detection.
- Business identity similarity.

If two sources disagree, the system records the conflict instead of choosing randomly.

## Deduplication Strategy

Duplicate detection uses:

- Normalized phone number match.
- Real website domain match.
- Business name similarity.
- Address similarity.

Generic map source URLs such as `openstreetmap.org` and `google.com/maps` are treated as evidence links, not identity websites. This prevents unrelated businesses from being merged only because they came from the same map provider.

## Deployment On Vercel

The repository is configured for Vercel's Python runtime.

Set these environment variables in:

```text
Vercel Project -> Settings -> Environment Variables
```

Recommended production variables:

```text
GEOAPIFY_API_KEY
GEOAPIFY_FALLBACK_API_KEY
GOOGLE_MAPS_API_KEY
SERPER_API_KEY
TAVILY_API_KEY
LLM_API_KEY
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.5-flash
LLM_SUMMARY_ENABLED=true
RESEARCH_CONCURRENCY=8
RESEARCH_SEARCH_TIMEOUT_SECONDS=12
RESEARCH_EXTRACTION_TIMEOUT_SECONDS=30
RESEARCH_ENRICHMENT_TIMEOUT_SECONDS=8
RESEARCH_MAX_RESULT_URLS=1000
```

Google setup requirement:

```text
Enable Places API (New) in the same Google Cloud project as GOOGLE_MAPS_API_KEY.
```

After changing environment variables, redeploy the latest `main` branch.

## Testing

```powershell
python -m pytest
python -m compileall research_agent
```

Current suite coverage includes:

- Query parsing and location correction.
- India and global region fanout.
- Geoapify and Google Places provider parsing.
- Source filtering and list-page rejection.
- Lead mining from articles and directories.
- Deduplication and false-merge prevention.
- Verification and conflict handling.
- PDF report generation.
- Readiness endpoint.

## Known Limitations

- Public web pages may block automated access, change markup, or omit structured data.
- Free provider tiers have quota and rate limits.
- Phone, rating, review count, and hours coverage is strongest with Google Places or Serper Places.
- Social platforms often restrict automated access; the agent treats them mainly as discoverable public evidence when indexed.
- Licensing databases vary by industry and region and may require source-specific adapters.


