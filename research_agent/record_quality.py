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

CONTENT_HOSTS = (
    "quora.",
    "reddit.",
    "youtube.",
    "youtu.be",
    "medium.",
    "wanderlog.",
    "travelandleisure",
    "socialmaharaj.",
    "treebo.",
    "blog.",
    "medium.",
    "youtube.",
    "youtu.be",
)

GENERIC_PHRASES = (
    "best ",
    "top ",
    "near me",
    "list of ",
    "directory",
    "find ",
)

GENERIC_BUSINESS_NAMES = {
    "dining",
    "google",
    "tripadvisor",
    "ooty restaurants",
    "ooty india",
    "exploring ooty",
    "access denied",
    "sulekha.com",
    "sulekha com",
    "service experts",
    "electrical electronics",
}

GENERIC_TITLE_PHRASES = (
    "what are ",
    "what is ",
    "where ",
    "how ",
    "guide to ",
    "your guide",
    "must try",
    "must-try",
    "places to eat",
    "food guide",
    "famous food",
    "famous restaurants",
    "local delights",
    "culinary delights",
    "best places",
    "best attractions",
    "popular restaurants",
    "restaurants near",
    "list of companies",
    "business directory",
    "small business directory",
    "map of ",
    "watch ",
    "experience in ",
    "is a ",
    "if you",
    "how to",
    "where to",
    "things to",
    "for your ",
    "repair needs",
    "dealers in ",
    "suppliers in ",
    "manufacturers in ",
    "companies in ",
    "buy latest",
    "wires switches",
    "led lights",
    "check prices",
    "order online",
    "book online",
    "near you",
    "phone numbers in",
    "travelling to",
    "traveling to",
    "well regarded",
    "well-regarded",
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
    raw_name = (record.business_name or "").strip()
    name = normalize_text(record.business_name)
    category = normalize_text(query.category)
    location = normalize_text(query.location)
    if not name:
        return True
    if raw_name.startswith("#"):
        return True
    if "@" in raw_name:
        return True
    if _looks_like_sentence_or_seo_title(raw_name):
        return True
    category_variants = _category_variants(category)
    if category and location:
        generic_names = {
            f"{variant} in {location}" for variant in category_variants
        } | {
            f"{variant} {location}" for variant in category_variants
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
    if name in GENERIC_BUSINESS_NAMES:
        return True
    if any(phrase in name for phrase in GENERIC_TITLE_PHRASES):
        return True
    if _looks_like_category_listicle(name, category_variants):
        return True
    if name.endswith("?"):
        return True
    if _host_is_content_page(record.website):
        return True
    if _host_is_directory(record.website) and any(variant in name for variant in category_variants) and location in name:
        return True
    if _host_is_directory(record.website) and _looks_like_directory_title(name):
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
        variants.update({"electrical contractor", "electrical contractors", "electricals", "electrical works", "electrical shop", "wiring contractor", "wiring service"})
    if "roofer" in variants or "roofing contractor" in variants:
        variants.update({"roofer", "roofers", "roofing contractor", "roofing contractors"})
    if "restaurant" in variants:
        variants.update({"restaurants", "dining", "eatery", "food delivery"})
    if "shop" in variants or "shopping" in variants or "store" in variants:
        variants.update({"shop", "shops", "store", "stores", "retail store", "showroom", "shopping"})
    if "salon" in variants:
        variants.update({"salons", "beauty salon", "beauty parlour", "hair salon", "spa"})
    if "gym" in variants:
        variants.update({"gyms", "fitness centre", "fitness center", "health club"})
    if "school" in variants:
        variants.update({"schools", "training institute", "academy"})
    return {variant for variant in variants if variant}


def _starts_with_listing_title(name: str, generic: str) -> bool:
    return name.startswith(f"{generic} ") or name.startswith(f"{generic},") or name.startswith(f"{generic} -")


def _host_is_directory(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(marker in host for marker in DIRECTORY_HOSTS)


def _host_is_content_page(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(marker in host for marker in CONTENT_HOSTS)


def _looks_like_directory_title(name: str) -> bool:
    return any(
        phrase in name
        for phrase in (
            "restaurants",
            "companies",
            "directory",
            "near me",
            "order online",
            "check prices",
            "reviews",
        )
    )


def _looks_like_category_listicle(name: str, category_variants: set[str]) -> bool:
    if not any(variant in name for variant in category_variants):
        return False
    if any(token in name for token in (" updated ", " food lovers", " culinary ", " district")):
        return True
    if any(name.startswith(prefix) for prefix in ("best ", "top ", "famous ", "popular ")):
        return True
    if name.startswith("the ") and " best " in name:
        return True
    if any(char.isdigit() for char in name) and any(
        token in name for token in ("best", "top", "famous", "updated")
    ):
        return True
    return False


def _looks_like_sentence_or_seo_title(raw_name: str) -> bool:
    normalized = normalize_text(raw_name)
    words = normalized.split()
    if len(words) > 10:
        return True
    if "..." in raw_name or "…" in raw_name:
        return True
    if raw_name.count(",") >= 3:
        return True
    if raw_name.count(" - ") >= 2:
        return True
    if normalized.startswith(("if ", "when ", "where ", "how ", "why ", "what ")):
        return True
    return False
