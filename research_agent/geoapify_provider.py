from __future__ import annotations

import json
from urllib.parse import quote_plus

from research_agent.config import Settings
from research_agent.http_client import HttpClient
from research_agent.locality import category_expansions, country_hint_for_text, has_location_signal, location_aliases, region_search_locations
from research_agent.models import BusinessRecord, SearchQuery, SourceEvidence


CATEGORY_MAP = {
    "cardiologist": ["healthcare.clinic_or_praxis.cardiology", "healthcare.clinic_or_praxis"],
    "cardiologists": ["healthcare.clinic_or_praxis.cardiology", "healthcare.clinic_or_praxis"],
    "dentist": ["healthcare.dentist"],
    "dentists": ["healthcare.dentist"],
    "dental clinic": ["healthcare.dentist"],
    "dental clinics": ["healthcare.dentist"],
    "doctor": ["healthcare.clinic_or_praxis.general", "healthcare.clinic_or_praxis", "healthcare.hospital"],
    "doctors": ["healthcare.clinic_or_praxis.general", "healthcare.clinic_or_praxis", "healthcare.hospital"],
    "clinic": ["healthcare.clinic_or_praxis"],
    "clinics": ["healthcare.clinic_or_praxis"],
    "hospital": ["healthcare.hospital"],
    "hospitals": ["healthcare.hospital"],
    "pharmacy": ["healthcare.pharmacy"],
    "pharmacies": ["healthcare.pharmacy"],
    "electrician": ["service", "commercial"],
    "electricians": ["service", "commercial"],
    "electrical contractor": ["service", "commercial"],
    "electrical service": ["service", "commercial"],
    "plumber": ["service", "commercial"],
    "plumbers": ["service", "commercial"],
    "plumbing service": ["service", "commercial"],
    "plumbing contractor": ["service", "commercial"],
    "restaurant": ["catering.restaurant"],
    "restaurants": ["catering.restaurant"],
    "cafe": ["catering.cafe"],
    "cafes": ["catering.cafe"],
    "hotel": ["accommodation.hotel"],
    "hotels": ["accommodation.hotel"],
    "salon": ["commercial.health_and_beauty"],
    "salons": ["commercial.health_and_beauty"],
    "gym": ["sport.fitness"],
    "gyms": ["sport.fitness"],
    "school": ["education.school"],
    "schools": ["education.school"],
    "shop": ["commercial"],
    "shops": ["commercial"],
    "store": ["commercial"],
    "stores": ["commercial"],
}


class GeoapifyProvider:
    def __init__(self, settings: Settings, client: HttpClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def keys(self) -> list[str]:
        return [key for key in [self.settings.geoapify_api_key, self.settings.geoapify_fallback_api_key] if key]

    @property
    def enabled(self) -> bool:
        return bool(self.keys)

    async def search(self, query: SearchQuery, limit: int = 50) -> list[BusinessRecord]:
        if not self.enabled or not query.location:
            return []
        search_locations = region_search_locations(query.location, limit=12) or [query.location]
        categories = self._categories(query.category)
        records: list[BusinessRecord] = []
        seen: set[str] = set()
        for search_location in search_locations:
            location = await self._geocode_location(search_location, parent_location=query.location)
            if not location:
                continue
            lat, lon = location
            for category in categories:
                if len(records) >= limit:
                    break
                for offset in range(0, min(limit, 100), 20):
                    page = await self._places(category, lat, lon, limit=min(20, limit - len(records)), offset=offset)
                    if not page:
                        break
                    for feature in page:
                        properties = feature.get("properties", {})
                        place_id = properties.get("place_id") or properties.get("datasource", {}).get("raw", {}).get("osm_id")
                        if not place_id or place_id in seen:
                            continue
                        seen.add(str(place_id))
                        if not self._matches_query(properties, query, search_location):
                            continue
                        record = self._record_from_feature(feature)
                        await self._enrich_details(record, str(place_id), properties)
                        records.append(record)
                        if len(records) >= limit:
                            break
                if len(records) >= limit:
                    break
        return records

    async def _geocode_location(self, location: str, parent_location: str = "") -> tuple[float, float] | None:
        for alias in _geocode_aliases(location, parent_location):
            for key in self.keys:
                url = (
                    "https://api.geoapify.com/v1/geocode/search"
                    f"?text={quote_plus(alias)}&limit=1&format=json&apiKey={key}"
                )
                fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 30, respect_robots=False)
                if not fetched or fetched.status_code >= 400:
                    continue
                payload = _json(fetched.body)
                results = payload.get("results", [])
                if results and results[0].get("lat") is not None and results[0].get("lon") is not None:
                    return float(results[0]["lat"]), float(results[0]["lon"])
        return None

    async def _places(
        self,
        category: str,
        lat: float,
        lon: float,
        limit: int,
        offset: int,
    ) -> list[dict]:
        for key in self.keys:
            url = (
                "https://api.geoapify.com/v2/places"
                f"?categories={quote_plus(category)}"
                f"&filter=circle:{lon},{lat},18000"
                f"&bias=proximity:{lon},{lat}"
                f"&limit={limit}&offset={offset}&lang=en&apiKey={key}"
            )
            fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 14, respect_robots=False)
            if not fetched or fetched.status_code >= 400:
                continue
            return _json(fetched.body).get("features", [])
        return []

    async def _enrich_details(
        self,
        record: BusinessRecord,
        place_id: str,
        properties: dict,
    ) -> None:
        for key in self.keys:
            url = (
                "https://api.geoapify.com/v2/place-details"
                f"?id={quote_plus(place_id)}&features=details&lang=en&apiKey={key}"
            )
            fetched = await self.client.fetch(url, ttl_seconds=60 * 60 * 24 * 30, respect_robots=False)
            if not fetched or fetched.status_code >= 400:
                continue
            features = _json(fetched.body).get("features", [])
            if not features:
                return
            detail_properties = features[0].get("properties", {})
            self._apply_detail_properties(record, detail_properties, properties)
            return

    def _record_from_feature(self, feature: dict) -> BusinessRecord:
        properties = feature.get("properties", {})
        source_url = _source_url(properties)
        record = BusinessRecord()
        mapping = {
            "business_name": properties.get("name"),
            "address": properties.get("formatted"),
            "phone": _first_contact_value(properties, ["phone", "contact:phone", "contact:mobile", "mobile"]),
            "email": _first_contact_value(properties, ["email", "contact:email"]),
            "working_hours": _first_contact_value(properties, ["opening_hours"]),
            "website": _first_contact_value(properties, ["website", "contact:website", "url"]),
            "services": properties.get("categories", []),
            "specialties": properties.get("categories", []),
        }
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "geoapify", 0.78))
        record.add_evidence(SourceEvidence("website", source_url, source_url, "geoapify", 0.78))
        return record

    def _apply_detail_properties(
        self,
        record: BusinessRecord,
        details: dict,
        fallback: dict,
    ) -> None:
        source_url = _source_url(details or fallback)
        contact = details.get("contact", {}) if isinstance(details.get("contact"), dict) else {}
        raw_phone = _first_contact_value(details, ["phone", "contact:phone", "contact:mobile", "mobile"])
        raw_email = _first_contact_value(details, ["email", "contact:email"])
        raw_website = _first_contact_value(details, ["website", "contact:website", "url"])
        mapping = {
            "business_name": details.get("name") or fallback.get("name"),
            "address": details.get("formatted") or fallback.get("formatted"),
            "phone": contact.get("phone") or raw_phone,
            "email": contact.get("email") or raw_email,
            "website": details.get("website") or raw_website,
            "working_hours": details.get("opening_hours") or _first_contact_value(details, ["opening_hours"]),
            "services": details.get("categories") or fallback.get("categories", []),
            "specialties": details.get("categories") or fallback.get("categories", []),
        }
        image = details.get("wiki_and_media", {}).get("image") if isinstance(details.get("wiki_and_media"), dict) else ""
        if image:
            mapping["images_urls"] = [image]
        for field_name, value in mapping.items():
            record.add_evidence(SourceEvidence(field_name, value, source_url, "geoapify", 0.82))

    def _categories(self, category: str) -> list[str]:
        category_values: list[str] = []
        for expanded in category_expansions(category):
            key = expanded.lower().strip()
            category_values.extend(CATEGORY_MAP.get(key, []))
        if not category_values:
            category_values = ["commercial", "healthcare", "service"]
        return list(dict.fromkeys(category_values))

    def _matches_query(self, properties: dict, query: SearchQuery, search_location: str | None = None) -> bool:
        text = " ".join(
            str(value)
            for value in [
                properties.get("name", ""),
                properties.get("formatted", ""),
                properties.get("city", ""),
                properties.get("county", ""),
                properties.get("state", ""),
                properties.get("address_line2", ""),
                " ".join(properties.get("categories", [])) if isinstance(properties.get("categories"), list) else "",
            ]
        )
        if not has_location_signal(text, query.location) and not (search_location and has_location_signal(text, search_location)):
            return False
        category_terms = [item.lower().rstrip("s") for item in category_expansions(query.category)]
        lowered = text.lower()
        return any(term and term in lowered for term in category_terms) or _is_broad_local_category(query.category)


def _is_broad_local_category(category: str) -> bool:
    lowered = category.lower()
    return any(term in lowered for term in ("shop", "store", "shopping", "service", "business"))


def _geocode_aliases(location: str, parent_location: str = "") -> list[str]:
    aliases: list[str] = []
    parent = (parent_location or "").strip()
    if parent and parent.lower().strip() != location.lower().strip():
        country = _country_name(country_hint_for_text(parent))
        aliases.append(f"{location}, {parent}")
        if country:
            aliases.append(f"{location}, {parent}, {country}")
    country = _country_name(country_hint_for_text(location))
    if country:
        aliases.append(f"{location}, {country}")
    aliases.extend(location_aliases(location))
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _country_name(country_code: str) -> str:
    return {
        "in": "India",
        "us": "United States",
        "gb": "United Kingdom",
        "ca": "Canada",
        "ae": "United Arab Emirates",
    }.get(country_code, "")


def _source_url(properties: dict) -> str:
    lat = properties.get("lat")
    lon = properties.get("lon")
    if lat is not None and lon is not None:
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"
    return "https://www.openstreetmap.org/"


def _json(body: str) -> dict:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def _first_contact_value(properties: dict, keys: list[str]) -> str:
    for source in [
        properties,
        properties.get("datasource", {}).get("raw", {}) if isinstance(properties.get("datasource"), dict) else {},
    ]:
        for key in keys:
            value = source.get(key) if isinstance(source, dict) else None
            if value:
                return str(value)
    return ""
