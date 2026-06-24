from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from research_agent.config import Settings
from research_agent.normalization import normalize_address, normalize_phone, normalize_text, normalize_url

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent
    AsyncIOMotorClient = None


class MongoResearchStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = bool(settings.mongo_uri)
        self.client = None
        self.database = None
        self.runs = None
        self.businesses = None
        if self.enabled and AsyncIOMotorClient is not None:
            self.client = AsyncIOMotorClient(settings.mongo_uri)
            self.database = self.client[settings.mongo_database]
            prefix = settings.mongo_collection_prefix
            self.runs = self.database[f"{prefix}_runs"]
            self.businesses = self.database[f"{prefix}_businesses"]

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()

    async def ensure_indexes(self) -> None:
        if not self.enabled or self.runs is None or self.businesses is None:
            return
        await self.runs.create_index("run_id", unique=True)
        await self.runs.create_index("search_summary.query")
        await self.runs.create_index("created_at")
        await self.businesses.create_index("business_key", unique=True)
        await self.businesses.create_index("business_name")
        await self.businesses.create_index("phone.value")
        await self.businesses.create_index("website")

    async def save_report(self, report: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled or self.runs is None or self.businesses is None:
            return None
        await self.ensure_indexes()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        summary = report.get("search_summary", {})
        run_id = _run_id(summary.get("query", ""), summary.get("started_at", created_at))
        run_document = {
            "run_id": run_id,
            "created_at": created_at,
            **report,
        }
        await self.runs.update_one({"run_id": run_id}, {"$set": run_document}, upsert=True)

        upserted = 0
        for business in report.get("business_results", []):
            key = _business_key(business)
            business_document = {
                **business,
                "business_key": key,
                "last_seen_run_id": run_id,
                "updated_at": created_at,
            }
            result = await self.businesses.update_one(
                {"business_key": key},
                {
                    "$set": business_document,
                    "$addToSet": {"seen_in_run_ids": run_id},
                    "$setOnInsert": {"created_at": created_at},
                },
                upsert=True,
            )
            if result.upserted_id is not None or result.modified_count:
                upserted += 1
        return {"run_id": run_id, "business_records_upserted": upserted}


def _run_id(query: str, started_at: str) -> str:
    return hashlib.sha256(f"{query}|{started_at}".encode()).hexdigest()[:24]


def _business_key(business: dict[str, Any]) -> str:
    phone = _verified_value(business, "phone") or business.get("phone", "")
    website = business.get("website") or _verified_value(business, "website")
    name = business.get("business_name", "")
    address = business.get("address", "")
    basis = "|".join(
        [
            normalize_phone(str(phone)),
            normalize_url(str(website)),
            normalize_text(str(name)),
            normalize_address(str(address)),
        ]
    )
    return hashlib.sha256(basis.encode()).hexdigest()


def _verified_value(business: dict[str, Any], field_name: str) -> Any:
    verification = business.get("verification", {})
    if isinstance(verification, dict):
        field = verification.get(field_name)
        if isinstance(field, dict):
            return field.get("value")
    return None
