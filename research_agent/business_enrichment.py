from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from research_agent.dedupe import merge_businesses
from research_agent.extraction import extract_business_from_html, record_from_search_result
from research_agent.http_client import HttpClient
from research_agent.models import BusinessRecord, SearchQuery, SearchResult
from research_agent.normalization import normalize_text
from research_agent.query_parser import infer_industry
from research_agent.search_providers import SearchProvider
from research_agent.verification import verify_record


DIRECTORY_BOOSTS = {
    "healthcare": ["practo.com", "dentee.com", "lybrate.com", "justdial.com", "sulekha.com"],
    "legal": ["justia.com", "avvo.com", "findlaw.com", "lawyers.com"],
    "trades": ["justdial.com", "sulekha.com", "indiamart.com", "yellowpages.com"],
    "food_hospitality": ["tripadvisor.in", "zomato.com", "restaurant-guru.in", "facebook.com", "justdial.com"],
    "retail": ["justdial.com", "sulekha.com", "indiamart.com", "facebook.com"],
    "wellness": ["justdial.com", "sulekha.com", "practo.com", "facebook.com"],
    "general": ["justdial.com", "sulekha.com", "yelp.com", "yellowpages.com"],
}

GENERIC_DIRECTORY_PATHS = (
    "/dentist",
    "/dentists",
    "/doctor",
    "/doctors",
    "/cardiologist",
    "/cardiologists",
    "/plumber",
    "/plumbers",
    "/electrician",
    "/electricians",
)


class BusinessEnricher:
    def __init__(
        self,
        providers: list[SearchProvider],
        http: HttpClient,
        concurrency: int,
    ) -> None:
        self.providers = providers
        self.http = http
        self.semaphore = asyncio.Semaphore(max(2, min(concurrency, 8)))

    async def enrich_many(
        self,
        records: list[BusinessRecord],
        query: SearchQuery,
        per_business_limit: int = 4,
        timeout_seconds: float = 10,
    ) -> list[BusinessRecord]:
        tasks = [
            asyncio.create_task(self.enrich(record, query, per_business_limit=per_business_limit))
            for record in records
            if record.business_name
        ]
        if not tasks:
            return records
        done, pending = await asyncio.wait(tasks, timeout=timeout_seconds)
        for task in pending:
            task.cancel()
        enriched = [task.result() for task in done if not task.cancelled() and task.exception() is None]
        untouched = [record for record in records if record not in enriched]
        return [*enriched, *untouched]

    async def enrich(
        self,
        record: BusinessRecord,
        query: SearchQuery,
        per_business_limit: int = 4,
    ) -> BusinessRecord:
        search_results = await self._exact_search(record, query)
        candidates = self._rank_results(search_results, record, query)[:per_business_limit]
        for result in candidates:
            if _is_generic_directory_page(result.url, query):
                continue
            merge_businesses(record, record_from_search_result(result))
            fetched = await self._fetch(result.url)
            if not fetched:
                continue
            extracted = extract_business_from_html(fetched.url, fetched.body, record_from_search_result(result))
            if not _page_matches_business(extracted, record, query):
                continue
            merge_businesses(record, extracted)
        return verify_record(record)

    async def _exact_search(self, record: BusinessRecord, query: SearchQuery) -> list[SearchResult]:
        searches = self._queries(record, query)
        results: dict[str, SearchResult] = {}

        async def run(provider: SearchProvider, text: str) -> None:
            async with self.semaphore:
                for result in await provider.search(text, page=1):
                    if _search_result_matches(result, record, query):
                        results.setdefault(result.url, result)

        await asyncio.gather(
            *[run(provider, text) for text in searches for provider in self.providers],
            return_exceptions=True,
        )
        return list(results.values())

    def _queries(self, record: BusinessRecord, query: SearchQuery) -> list[str]:
        name = record.business_name
        location = query.location
        searches = [
            f'"{name}" "{location}" phone',
            f'"{name}" "{location}" contact number',
        ]
        for source in DIRECTORY_BOOSTS.get(infer_industry(query.category), DIRECTORY_BOOSTS["general"])[:3]:
            searches.append(f'"{name}" "{location}" site:{source}')
        return list(dict.fromkeys(searches))

    def _rank_results(
        self,
        results: list[SearchResult],
        record: BusinessRecord,
        query: SearchQuery,
    ) -> list[SearchResult]:
        return sorted(results, key=lambda item: _business_result_score(item, record, query), reverse=True)

    async def _fetch(self, url: str):
        async with self.semaphore:
            return await self.http.fetch(url, ttl_seconds=60 * 60 * 24 * 14)


def _business_result_score(result: SearchResult, record: BusinessRecord, query: SearchQuery) -> float:
    if _is_generic_directory_page(result.url, query):
        return 0.0
    text = normalize_text(f"{result.title} {result.snippet} {result.url}")
    name = normalize_text(record.business_name)
    score = 0.0
    for token in _important_tokens(name):
        if token in text:
            score += 0.22
    if query.location and normalize_text(query.location) in text:
        score += 0.25
    host = urlparse(result.url).netloc.lower()
    if record.website and urlparse(record.website).netloc.lower() in host:
        score += 0.35
    if any(marker in host for marker in ("justdial.", "sulekha.", "practo.", "dentee.")):
        score += 0.1
    return score


def _search_result_matches(result: SearchResult, record: BusinessRecord, query: SearchQuery) -> bool:
    return _business_result_score(result, record, query) >= 0.45


def _page_matches_business(extracted: BusinessRecord, seed: BusinessRecord, query: SearchQuery) -> bool:
    if _is_generic_directory_page(extracted.website, query):
        return False
    text = normalize_text(
        " ".join(
            [
                extracted.business_name,
                extracted.address,
                extracted.website,
                " ".join(extracted.source_urls.get("business_name", [])),
            ]
        )
    )
    seed_name = normalize_text(seed.business_name)
    important = _important_tokens(seed_name)
    if not important:
        return False
    token_hits = sum(1 for token in important if token in text)
    if token_hits >= max(1, len(important) - 1):
        return True
    if seed.address and query.location and normalize_text(query.location) in text and token_hits >= 1:
        return True
    return False


def _important_tokens(value: str) -> list[str]:
    ignored = {
        "clinic",
        "hospital",
        "care",
        "dental",
        "doctor",
        "dr",
        "the",
        "and",
        "in",
        "near",
        "best",
    }
    return [token for token in normalize_text(value).split() if len(token) > 2 and token not in ignored]


def _is_generic_directory_page(url: str, query: SearchQuery) -> bool:
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower().rstrip("/")
    if not any(marker in host for marker in ("practo.", "dentee.", "justdial.", "sulekha.")):
        return False
    location = normalize_text(query.location)
    category = normalize_text(query.category).rstrip("s")
    path_text = normalize_text(path.replace("/", " "))
    if location and category and location in path_text and category in path_text:
        return True
    return any(path.endswith(generic_path) for generic_path in GENERIC_DIRECTORY_PATHS)
