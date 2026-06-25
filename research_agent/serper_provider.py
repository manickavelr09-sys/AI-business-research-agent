from __future__ import annotations

import httpx

from research_agent.config import Settings
from research_agent.http_client import HttpClient
from research_agent.locality import category_expansions, location_aliases
from research_agent.models import BusinessRecord, SearchQuery, SourceEvidence


class SerperPlacesProvider:
    def __init__(self, settings: Settings, client: HttpClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def enabled(self) -> bool:
        return bool(self.settings.serper_api_key)

    async def search(self, query: SearchQuery, limit: int = 40) -> list[BusinessRecord]:
        if not self.enabled or not query.location:
            return []
        records: list[BusinessRecord] = []
        seen: set[str] = set()
        for text_query in self._queries(query):
            if len(records) >= limit:
                break
            for page in range(1, 3):
                if len(records) >= limit:
                    break
                items = await self._places(text_query, page=page)
                if not items:
                    break
                for item in items:
                    identity = item.get("placeId") or item.get("cid") or item.get("title")
                    if not identity or identity in seen:
                        continue
                    seen.add(str(identity))
                    record = self._record_from_place(item)
                    records.append(record)
                    if len(records) >= limit:
                        break
        return records

    def _queries(self, query: SearchQuery) -> list[str]:
        searches: list[str] = []
        for category in category_expansions(query.category):
            for location in location_aliases(query.location)[:3]:
                searches.append(f"{category} in {location}")
        return list(dict.fromkeys(searches))

    async def _places(self, search_query: str, page: int) -> list[dict]:
        payload = {"q": search_query, "num": 20, "page": page}
        country = _country_hint(search_query)
        if country:
            payload["gl"] = country
        try:
            response = await self.client.client.post(
                "https://google.serper.dev/places",
                json=payload,
                headers={"X-API-KEY": self.settings.serper_api_key, "Content-Type": "application/json"},
            )
        except httpx.HTTPError:
            return []
        if response.status_code >= 400:
            return []
        data = response.json()
        return data.get("places", []) or []

    def _record_from_place(self, item: dict) -> BusinessRecord:
        source_url = item.get("link") or item.get("website") or "https://google.com/maps"
        record = BusinessRecord()
        mapping = {
            "business_name": item.get("title"),
            "address": item.get("address"),
            "phone": item.get("phoneNumber"),
            "website": item.get("website") or source_url,
            "rating": str(item.get("rating")) if item.get("rating") is not None else "",
            "review_count": str(item.get("ratingCount")) if item.get("ratingCount") is not None else "",
            "services": [item.get("category")] if item.get("category") else [],
            "images_urls": [item.get("thumbnailUrl")] if item.get("thumbnailUrl") else [],
        }
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "serper_places", 0.86))
        return record


def _country_hint(query: str) -> str:
    lowered = query.lower()
    if any(value in lowered for value in ("india", "tamil nadu", "thanjavur", "trichy", "tiruchirappalli", "karaikudi", "karaikkudi", "sivaganga", "sivagangai", "ooty", "udhagamandalam", "kanyakumari", "kanniyakumari", "madurai", "coimbatore", "kovai", "chennai", "mumbai", "delhi", "pune", "kolkata", "hyderabad", "bangalore", "bengaluru")):
        return "in"
    if any(value in lowered for value in ("united kingdom", "birmingham uk", "london", "manchester")):
        return "gb"
    if any(value in lowered for value in ("united states", "usa", "austin", "dallas", "houston", "chicago")):
        return "us"
    return ""
