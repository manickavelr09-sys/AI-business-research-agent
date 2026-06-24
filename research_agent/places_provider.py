from __future__ import annotations

from urllib.parse import quote_plus

from research_agent.config import Settings
from research_agent.http_client import HttpClient
from research_agent.locality import category_expansions, location_aliases
from research_agent.models import BusinessRecord, SearchQuery, SourceEvidence


class GooglePlacesProvider:
    def __init__(self, settings: Settings, client: HttpClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def enabled(self) -> bool:
        return bool(self.settings.google_maps_api_key)

    async def search(self, query: SearchQuery, limit: int = 20) -> list[BusinessRecord]:
        if not self.enabled:
            return []
        records: list[BusinessRecord] = []
        seen_place_ids: set[str] = set()
        searches = self._queries(query)
        for text_query in searches:
            if len(records) >= limit:
                break
            url = (
                "https://maps.googleapis.com/maps/api/place/textsearch/json"
                f"?query={quote_plus(text_query)}&key={self.settings.google_maps_api_key}"
            )
            fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 14, respect_robots=False)
            if not fetched or fetched.status_code >= 400:
                continue
            payload = fetched_json(fetched.body)
            for item in payload.get("results", []):
                place_id = item.get("place_id")
                if not place_id or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)
                record = self._record_from_text_result(item)
                await self._enrich_details(record, place_id)
                records.append(record)
                if len(records) >= limit:
                    break
        return records

    def _queries(self, query: SearchQuery) -> list[str]:
        searches = []
        for category in category_expansions(query.category):
            for location in location_aliases(query.location)[:2]:
                searches.append(f"{category} in {location}")
        return list(dict.fromkeys(searches))

    def _record_from_text_result(self, item: dict) -> BusinessRecord:
        place_id = item.get("place_id", "")
        source_url = maps_url(place_id)
        record = BusinessRecord()
        evidence = {
            "business_name": item.get("name"),
            "address": item.get("formatted_address"),
            "rating": str(item.get("rating")) if item.get("rating") is not None else "",
            "review_count": str(item.get("user_ratings_total")) if item.get("user_ratings_total") is not None else "",
            "website": source_url,
        }
        for field_name, value in evidence.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "google_maps", 0.88))
        if item.get("photos"):
            urls = [
                "https://maps.googleapis.com/maps/api/place/photo"
                f"?maxwidth=1200&photo_reference={photo.get('photo_reference')}&key={self.settings.google_maps_api_key}"
                for photo in item.get("photos", [])[:5]
                if photo.get("photo_reference")
            ]
            record.add_evidence(SourceEvidence("images_urls", urls, source_url, "google_maps", 0.88))
        return record

    async def _enrich_details(self, record: BusinessRecord, place_id: str) -> None:
        fields = ",".join(
            [
                "name",
                "formatted_address",
                "formatted_phone_number",
                "international_phone_number",
                "website",
                "url",
                "opening_hours",
                "rating",
                "user_ratings_total",
                "types",
                "business_status",
            ]
        )
        url = (
            "https://maps.googleapis.com/maps/api/place/details/json"
            f"?place_id={place_id}&fields={fields}&key={self.settings.google_maps_api_key}"
        )
        fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 30, respect_robots=False)
        if not fetched or fetched.status_code >= 400:
            return
        result = fetched_json(fetched.body).get("result", {})
        source_url = result.get("url") or maps_url(place_id)
        mapping = {
            "business_name": result.get("name"),
            "address": result.get("formatted_address"),
            "phone": result.get("formatted_phone_number") or result.get("international_phone_number"),
            "website": result.get("website") or source_url,
            "rating": str(result.get("rating")) if result.get("rating") is not None else "",
            "review_count": str(result.get("user_ratings_total")) if result.get("user_ratings_total") is not None else "",
            "services": result.get("types", []),
        }
        hours = result.get("opening_hours", {}).get("weekday_text", [])
        if hours:
            mapping["working_hours"] = "; ".join(hours)
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "google_maps", 0.9))


def maps_url(place_id: str) -> str:
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "https://www.google.com/maps"


def fetched_json(body: str) -> dict:
    import json

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}
