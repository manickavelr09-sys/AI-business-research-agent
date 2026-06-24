from research_agent.config import Settings
from research_agent.http_client import HttpClient
from research_agent.search_providers import SerperSearchProvider, TavilySearchProvider
from research_agent.storage import ResearchCache


def test_serper_search_provider_requires_api_key(tmp_path) -> None:
    settings = Settings(cache_path=tmp_path / "cache.sqlite3", serper_api_key="")
    cache = ResearchCache(settings.cache_path)
    client = HttpClient(settings, cache)
    provider = SerperSearchProvider(client, cache)

    assert not provider.enabled


def test_tavily_search_provider_requires_api_key(tmp_path) -> None:
    settings = Settings(cache_path=tmp_path / "cache.sqlite3", tavily_api_key="")
    cache = ResearchCache(settings.cache_path)
    client = HttpClient(settings, cache)
    provider = TavilySearchProvider(client, cache)

    assert not provider.enabled
