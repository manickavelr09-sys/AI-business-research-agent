from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from research_agent.http_client import HttpClient
from research_agent.locality import country_hint_for_text
from research_agent.models import SearchResult
from research_agent.storage import ResearchCache


class SearchProvider(ABC):
    name: str

    def __init__(self, client: HttpClient, cache: ResearchCache) -> None:
        self.client = client
        self.cache = cache

    async def search(self, query: str, page: int = 1) -> list[SearchResult]:
        cached = self.cache.get_search(self.name, query, page, ttl_seconds=60 * 60 * 24 * 14)
        if cached is not None:
            return [SearchResult(**item) for item in cached]
        results = await self._search_uncached(query, page)
        if results:
            self.cache.put_search(self.name, query, page, [item.__dict__ for item in results])
        return results

    @abstractmethod
    async def _search_uncached(self, query: str, page: int = 1) -> list[SearchResult]:
        raise NotImplementedError


class DuckDuckGoHtmlProvider(SearchProvider):
    name = "duckduckgo_html"

    async def _search_uncached(self, query: str, page: int = 1) -> list[SearchResult]:
        start = (page - 1) * 30
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&s={start}"
        fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24, respect_robots=False)
        if not fetched or fetched.status_code >= 400:
            return []
        return _parse_duckduckgo(fetched.body, self.name)


class BingHtmlProvider(SearchProvider):
    name = "bing_html"

    async def _search_uncached(self, query: str, page: int = 1) -> list[SearchResult]:
        first = (page - 1) * 10 + 1
        url = f"https://www.bing.com/search?q={quote_plus(query)}&first={first}"
        fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24, respect_robots=False)
        if not fetched or fetched.status_code >= 400:
            return []
        return _parse_bing(fetched.body, self.name)


class SerperSearchProvider(SearchProvider):
    name = "serper_search"

    @property
    def enabled(self) -> bool:
        return bool(self.client.settings.serper_api_key)

    async def _search_uncached(self, query: str, page: int = 1) -> list[SearchResult]:
        if not self.enabled:
            return []
        payload = {"q": query, "num": 10, "page": page}
        country = _country_hint(query)
        if country:
            payload["gl"] = country
        try:
            response = await self.client.client.post(
                "https://google.serper.dev/search",
                json=payload,
                headers={"X-API-KEY": self.client.settings.serper_api_key, "Content-Type": "application/json"},
            )
        except httpx.HTTPError:
            return []
        if response.status_code >= 400:
            return []
        data = response.json()
        results: list[SearchResult] = []
        for index, item in enumerate(data.get("organic", []), start=1):
            url = item.get("link")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", "") or item.get("date", ""),
                    provider=self.name,
                    rank=index + ((page - 1) * 10),
                )
            )
        for item in data.get("places", []) or []:
            url = item.get("website") or item.get("link")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=" ".join(str(value) for value in [item.get("address", ""), item.get("phoneNumber", "")] if value),
                    provider=self.name,
                    rank=len(results) + 1,
                )
            )
        return results


class TavilySearchProvider(SearchProvider):
    name = "tavily_search"

    @property
    def enabled(self) -> bool:
        return bool(self.client.settings.tavily_api_key)

    async def _search_uncached(self, query: str, page: int = 1) -> list[SearchResult]:
        if not self.enabled or page > 1:
            return []
        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": 10,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_usage": True,
        }
        country = _tavily_country_hint(query)
        if country:
            payload["country"] = country
        try:
            response = await self.client.client.post(
                "https://api.tavily.com/search",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.client.settings.tavily_api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.HTTPError:
            return []
        if response.status_code >= 400:
            return []
        data = response.json()
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                provider=self.name,
                rank=index,
            )
            for index, item in enumerate(data.get("results", []), start=1)
            if item.get("url")
        ]


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def _unwrap_duckduckgo_url(url: str) -> str:
    parsed = urlparse(html.unescape(url))
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    return html.unescape(url)


def _parse_duckduckgo(body: str, provider: str) -> list[SearchResult]:
    soup = BeautifulSoup(body, "lxml")
    results: list[SearchResult] = []
    for index, anchor in enumerate(soup.select("a.result__a"), start=1):
        href = anchor.get("href")
        if not href:
            continue
        container = anchor.find_parent(class_=re.compile(r"\bresult\b"))
        snippet = ""
        if container:
            snippet_node = container.select_one(".result__snippet")
            if snippet_node:
                snippet = snippet_node.get_text(" ", strip=True)
        results.append(
            SearchResult(
                title=anchor.get_text(" ", strip=True),
                url=_unwrap_duckduckgo_url(href),
                snippet=snippet,
                provider=provider,
                rank=index,
            )
        )
    return results


def _parse_bing(body: str, provider: str) -> list[SearchResult]:
    soup = BeautifulSoup(body, "lxml")
    results: list[SearchResult] = []
    for index, item in enumerate(soup.select("li.b_algo"), start=1):
        anchor = item.select_one("h2 a")
        if not anchor or not anchor.get("href"):
            continue
        snippet_node = item.select_one("p")
        results.append(
            SearchResult(
                title=anchor.get_text(" ", strip=True),
                url=html.unescape(anchor["href"]),
                snippet=snippet_node.get_text(" ", strip=True) if snippet_node else "",
                provider=provider,
                rank=index,
            )
        )
    return results


def _country_hint(query: str) -> str:
    return country_hint_for_text(query)


def _tavily_country_hint(query: str) -> str:
    return {
        "in": "india",
        "gb": "united kingdom",
        "us": "united states",
        "ca": "canada",
        "ae": "united arab emirates",
    }.get(_country_hint(query), "")
