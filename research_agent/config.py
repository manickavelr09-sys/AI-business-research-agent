from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _default_cache_path() -> str:
    if os.getenv("VERCEL"):
        return "/tmp/research_agent.sqlite3"
    return ".cache/research_agent.sqlite3"


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("APP_PORT", "8000"))
    cache_path: Path = Path(os.getenv("RESEARCH_CACHE_PATH", _default_cache_path()))
    concurrency: int = int(os.getenv("RESEARCH_CONCURRENCY", "12"))
    request_timeout_seconds: float = float(os.getenv("RESEARCH_REQUEST_TIMEOUT_SECONDS", "15"))
    search_timeout_seconds: float = float(os.getenv("RESEARCH_SEARCH_TIMEOUT_SECONDS", "12"))
    extraction_timeout_seconds: float = float(os.getenv("RESEARCH_EXTRACTION_TIMEOUT_SECONDS", "30"))
    enrichment_timeout_seconds: float = float(os.getenv("RESEARCH_ENRICHMENT_TIMEOUT_SECONDS", "10"))
    search_query_budget: int = int(os.getenv("RESEARCH_SEARCH_QUERY_BUDGET", "36"))
    lead_enrichment_limit: int = int(os.getenv("RESEARCH_LEAD_ENRICHMENT_LIMIT", "100"))
    max_search_pages: int = int(os.getenv("RESEARCH_MAX_SEARCH_PAGES", "2"))
    max_result_urls: int = int(os.getenv("RESEARCH_MAX_RESULT_URLS", "300"))
    user_agent: str = os.getenv(
        "RESEARCH_USER_AGENT",
        "Mozilla/5.0 (compatible; BusinessResearchAgent/0.1; +https://example.local/research-agent)",
    )
    respect_robots: bool = _bool_env("RESEARCH_RESPECT_ROBOTS", True)
    mongo_uri: str = os.getenv("MONGO_URI", "")
    mongo_database: str = os.getenv("MONGO_DATABASE", "business_research")
    mongo_collection_prefix: str = os.getenv("MONGO_COLLECTION_PREFIX", "research")
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    geoapify_api_key: str = os.getenv("GEOAPIFY_API_KEY", "")
    geoapify_fallback_api_key: str = os.getenv("GEOAPIFY_FALLBACK_API_KEY", "")
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    brave_search_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    llm_base_url: str = os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_summary_enabled: bool = _bool_env("LLM_SUMMARY_ENABLED", True)


settings = Settings()
