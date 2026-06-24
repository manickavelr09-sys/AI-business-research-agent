from __future__ import annotations

from urllib.parse import urlparse

from research_agent.locality import has_location_signal
from research_agent.models import BusinessRecord, SearchQuery
from research_agent.normalization import normalize_text


DIRECTORY_HOSTS = (
    "justdial.",
    "sulekha.",
    "dentee.",
    "healthgrades.",
    "webmd.",
    "yellowpages.",
    "yelp.",
    "practo.",
)

GENERIC_PHRASES = (
    "best ",
    "top ",
    "near me",
    "list of ",
    "directory",
    "find ",
)


def should_stream_record(record: BusinessRecord, query: SearchQuery, source_kind: str) -> bool:
    if not record.business_name:
        return False
    if query.location and not _record_has_location(record, query):
        return False
    if _looks_like_generic_listing(record, query):
        return False

    if source_kind in {"geoapify", "google_places", "serper_places"}:
        return bool(record.address or record.phone)

    strong_fields = [
        record.address,
        record.phone,
        record.email,
        record.working_hours,
        record.rating,
        record.review_count,
        record.license_information,
    ]
    if any(str(field).strip() for field in strong_fields):
        return True

    # A direct official-looking site with a specific business name is useful as a seed.
    return bool(record.website and not _host_is_directory(record.website))


def _record_has_location(record: BusinessRecord, query: SearchQuery) -> bool:
    text = " ".join(
        [
            record.business_name,
            record.address,
            record.website,
            " ".join(record.source_urls.get("business_name", [])),
            " ".join(record.source_urls.get("address", [])),
        ]
    )
    return has_location_signal(text, query.location)


def _looks_like_generic_listing(record: BusinessRecord, query: SearchQuery) -> bool:
    name = normalize_text(record.business_name)
    category = normalize_text(query.category)
    location = normalize_text(query.location)
    if not name:
        return True
    category_variants = _category_variants(category)
    if category and location:
        generic_names = {
            f"{variant} in {location}" for variant in category_variants
        } | {
            f"best {variant} in {location}" for variant in category_variants
        } | {
            f"top {variant} in {location}" for variant in category_variants
        } | {
            f"{variant} near me in {location}" for variant in category_variants
        } | {
            f"best {variant} near me in {location}" for variant in category_variants
        }
        if name in generic_names or any(_starts_with_listing_title(name, generic) for generic in generic_names):
            return True
    if any(phrase in name for phrase in GENERIC_PHRASES) and any(variant in name for variant in category_variants):
        return True
    if _host_is_directory(record.website) and any(variant in name for variant in category_variants) and location in name:
        return True
    has_business_fields = bool(record.address or record.phone or record.email or record.working_hours)
    if has_business_fields:
        return False
    return False


def _category_variants(category: str) -> set[str]:
    if not category:
        return set()
    variants = {category}
    if category.endswith("ies"):
        variants.add(f"{category[:-3]}y")
    if category.endswith("s"):
        variants.add(category[:-1])
    if "dentist" in variants:
        variants.update({"dental clinic", "dental clinics"})
    if "doctor" in variants:
        variants.update({"physician", "physicians", "clinic", "clinics", "medical clinic", "medical clinics"})
    if "cardiologist" in variants:
        variants.update({"cardiology clinic", "cardiology clinics", "heart clinic", "heart clinics"})
    if "lawyer" in variants:
        variants.update({"attorney", "attorneys", "law firm", "law firms"})
    if "plumber" in variants:
        variants.update({"plumbing contractor", "plumbing contractors"})
    if "electrician" in variants:
        variants.update({"electrical contractor", "electrical contractors"})
    if "roofer" in variants or "roofing contractor" in variants:
        variants.update({"roofer", "roofers", "roofing contractor", "roofing contractors"})
    return {variant for variant in variants if variant}


def _starts_with_listing_title(name: str, generic: str) -> bool:
    return name.startswith(f"{generic} ") or name.startswith(f"{generic},") or name.startswith(f"{generic} -")


def _host_is_directory(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(marker in host for marker in DIRECTORY_HOSTS)
