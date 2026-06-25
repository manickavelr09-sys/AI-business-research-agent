from __future__ import annotations

from urllib.parse import quote_plus

from research_agent.config import Settings
from research_agent.http_client import HttpClient
from research_agent.locality import category_expansions, expanded_search_locations
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
            payload = await self._text_search_new(text_query)
            if not payload.get("places"):
                payload = await self._text_search_legacy(text_query)
            for item in payload.get("places", []):
                place_id = item.get("id") or _place_id_from_name(item.get("name", ""))
                if not place_id or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)
                record = self._record_from_new_place(item)
                await self._enrich_details_new(record, place_id)
                records.append(record)
                if len(records) >= limit:
                    break
            for item in payload.get("results", []):
                place_id = item.get("place_id")
                if not place_id or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)
                record = self._record_from_text_result(item)
                await self._enrich_details_legacy(record, place_id)
                records.append(record)
                if len(records) >= limit:
                    break
        return records

    def _queries(self, query: SearchQuery) -> list[str]:
        searches = []
        for category in category_expansions(query.category):
            for location in expanded_search_locations(query.location, limit=12):
                searches.append(f"{category} in {location}")
        return list(dict.fromkeys(searches))

    async def _text_search_new(self, text_query: str) -> dict:
        field_mask = ",".join(
            [
                "places.id",
                "places.name",
                "places.displayName",
                "places.formattedAddress",
                "places.googleMapsUri",
                "places.websiteUri",
                "places.nationalPhoneNumber",
                "places.internationalPhoneNumber",
                "places.rating",
                "places.userRatingCount",
                "places.regularOpeningHours",
                "places.types",
                "places.photos",
            ]
        )
        try:
            response = await self.client.client.post(
                "https://places.googleapis.com/v1/places:searchText",
                json={"textQuery": text_query, "pageSize": 20},
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.settings.google_maps_api_key,
                    "X-Goog-FieldMask": field_mask,
                },
            )
        except Exception:
            return {}
        if response.status_code >= 400:
            return {}
        return response.json()

    async def _text_search_legacy(self, text_query: str) -> dict:
        url = (
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
            f"?query={quote_plus(text_query)}&key={self.settings.google_maps_api_key}"
        )
        fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 14, respect_robots=False)
        if not fetched or fetched.status_code >= 400:
            return {}
        return fetched_json(fetched.body)

    def _record_from_new_place(self, item: dict) -> BusinessRecord:
        place_id = item.get("id") or _place_id_from_name(item.get("name", ""))
        source_url = item.get("googleMapsUri") or maps_url(place_id)
        display_name = item.get("displayName", {})
        record = BusinessRecord()
        mapping = {
            "business_name": display_name.get("text") if isinstance(display_name, dict) else "",
            "address": item.get("formattedAddress"),
            "phone": item.get("nationalPhoneNumber") or item.get("internationalPhoneNumber"),
            "website": item.get("websiteUri") or source_url,
            "rating": str(item.get("rating")) if item.get("rating") is not None else "",
            "review_count": str(item.get("userRatingCount")) if item.get("userRatingCount") is not None else "",
            "services": item.get("types", []),
        }
        hours = item.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        if hours:
            mapping["working_hours"] = "; ".join(hours)
        photos = [
            f"https://places.googleapis.com/v1/{photo.get('name')}/media?maxWidthPx=1200&key={self.settings.google_maps_api_key}"
            for photo in item.get("photos", [])[:5]
            if photo.get("name")
        ]
        if photos:
            mapping["images_urls"] = photos
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "google_places_new", 0.92))
        return record

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

    async def _enrich_details_new(self, record: BusinessRecord, place_id: str) -> None:
        field_mask = ",".join(
            [
                "id",
                "displayName",
                "formattedAddress",
                "nationalPhoneNumber",
                "internationalPhoneNumber",
                "websiteUri",
                "googleMapsUri",
                "regularOpeningHours",
                "rating",
                "userRatingCount",
                "types",
                "businessStatus",
            ]
        )
        try:
            response = await self.client.client.get(
                f"https://places.googleapis.com/v1/places/{quote_plus(place_id)}",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.settings.google_maps_api_key,
                    "X-Goog-FieldMask": field_mask,
                },
            )
        except Exception:
            return
        if response.status_code >= 400:
            return
        result = response.json()
        source_url = result.get("googleMapsUri") or maps_url(place_id)
        display_name = result.get("displayName", {})
        mapping = {
            "business_name": display_name.get("text") if isinstance(display_name, dict) else "",
            "address": result.get("formattedAddress"),
            "phone": result.get("nationalPhoneNumber") or result.get("internationalPhoneNumber"),
            "website": result.get("websiteUri") or source_url,
            "rating": str(result.get("rating")) if result.get("rating") is not None else "",
            "review_count": str(result.get("userRatingCount")) if result.get("userRatingCount") is not None else "",
            "services": result.get("types", []),
        }
        hours = result.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        if hours:
            mapping["working_hours"] = "; ".join(hours)
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "google_places_new", 0.94))

    async def _enrich_details_legacy(self, record: BusinessRecord, place_id: str) -> None:
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


def _place_id_from_name(value: str) -> str:
    return value.rsplit("/", 1)[-1] if value.startswith("places/") else value


def fetched_json(body: str) -> dict:
    import json

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}
