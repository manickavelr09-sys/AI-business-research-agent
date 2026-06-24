from __future__ import annotations

import asyncio
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from research_agent.config import Settings
from research_agent.storage import ResearchCache


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    body: str
    headers: dict[str, str]
    from_cache: bool = False


class RobotsGuard:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._lock = asyncio.Lock()

    async def allowed(self, url: str) -> bool:
        if not self.settings.respect_robots:
            return True
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        base = f"{parsed.scheme}://{parsed.netloc}"
        async with self._lock:
            parser = self._cache.get(base)
            if parser is None:
                parser = urllib.robotparser.RobotFileParser(f"{base}/robots.txt")
                try:
                    await asyncio.to_thread(parser.read)
                except Exception:
                    return True
                self._cache[base] = parser
        return parser.can_fetch(self.settings.user_agent, url)


class HttpClient:
    def __init__(self, settings: Settings, cache: ResearchCache) -> None:
        self.settings = settings
        self.cache = cache
        self.robots = RobotsGuard(settings)
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.user_agent, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def fetch(
        self,
        url: str,
        ttl_seconds: int = 60 * 60 * 24 * 7,
        respect_robots: bool | None = None,
    ) -> FetchResult | None:
        cached = self.cache.get_http(url, ttl_seconds)
        if cached:
            return FetchResult(from_cache=True, **cached)
        should_respect_robots = self.settings.respect_robots if respect_robots is None else respect_robots
        if should_respect_robots and not await self.robots.allowed(url):
            return None
        try:
            response = await self.client.get(url)
        except httpx.HTTPError:
            return None
        text = response.text[:2_000_000]
        self.cache.put_http(url, response.status_code, text, dict(response.headers))
        return FetchResult(url=str(response.url), status_code=response.status_code, body=text, headers=dict(response.headers))
