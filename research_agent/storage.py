from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class ResearchCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS http_cache (
                url TEXT PRIMARY KEY,
                status_code INTEGER NOT NULL,
                body TEXT NOT NULL,
                headers_json TEXT NOT NULL,
                fetched_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                query TEXT NOT NULL,
                page INTEGER NOT NULL,
                results_json TEXT NOT NULL,
                fetched_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_search_cache_query ON search_cache(query, provider);
            """
        )
        self.connection.commit()

    def get_http(self, url: str, ttl_seconds: int) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM http_cache WHERE url = ?", (url,)).fetchone()
        if not row or time.time() - row["fetched_at"] > ttl_seconds:
            return None
        return {
            "url": url,
            "status_code": row["status_code"],
            "body": row["body"],
            "headers": json.loads(row["headers_json"]),
        }

    def put_http(self, url: str, status_code: int, body: str, headers: dict[str, str]) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO http_cache(url, status_code, body, headers_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url, status_code, body, json.dumps(headers), time.time()),
        )
        self.connection.commit()

    def get_search(self, provider: str, query: str, page: int, ttl_seconds: int) -> list[dict] | None:
        cache_key = self._search_key(provider, query, page)
        row = self.connection.execute(
            "SELECT * FROM search_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        if not row or time.time() - row["fetched_at"] > ttl_seconds:
            return None
        return json.loads(row["results_json"])

    def put_search(self, provider: str, query: str, page: int, results: list[dict]) -> None:
        cache_key = self._search_key(provider, query, page)
        self.connection.execute(
            """
            INSERT OR REPLACE INTO search_cache(cache_key, provider, query, page, results_json, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cache_key, provider, query, page, json.dumps(results), time.time()),
        )
        self.connection.commit()

    @staticmethod
    def _search_key(provider: str, query: str, page: int) -> str:
        digest = hashlib.sha256(f"{provider}|{query}|{page}".encode()).hexdigest()
        return digest
