from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import urlparse

from research_agent.models import BusinessRecord
from research_agent.normalization import (
    normalize_address,
    normalize_phone,
    normalize_text,
    normalize_url,
)


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def business_match_score(left: BusinessRecord, right: BusinessRecord) -> float:
    phone_match = (
        normalize_phone(left.phone)
        and normalize_phone(left.phone) == normalize_phone(right.phone)
    )
    left_website = _identity_website(left.website)
    right_website = _identity_website(right.website)
    website_match = left_website and left_website == right_website
    name_score = _similarity(normalize_text(left.business_name), normalize_text(right.business_name))
    address_score = _similarity(normalize_address(left.address), normalize_address(right.address))
    score = max(name_score * 0.55 + address_score * 0.45, name_score * 0.75)
    if phone_match:
        score = max(score, 0.96)
    if website_match:
        score = max(score, 0.94)
    if phone_match and name_score > 0.45:
        score = 0.99
    return score


def _identity_website(value: str) -> str:
    normalized = normalize_url(value)
    if not normalized:
        return ""
    host = urlparse(value if "://" in str(value) else f"https://{value}").netloc.lower().removeprefix("www.")
    if host in {"openstreetmap.org", "google.com", "maps.google.com", "google.co.in"}:
        return ""
    if host.endswith(".google.com") or host.endswith(".openstreetmap.org"):
        return ""
    return normalized


def merge_businesses(primary: BusinessRecord, duplicate: BusinessRecord) -> BusinessRecord:
    for field_name in (
        "business_name",
        "address",
        "phone",
        "email",
        "website",
        "working_hours",
        "rating",
        "review_count",
        "license_information",
    ):
        if not getattr(primary, field_name) and getattr(duplicate, field_name):
            setattr(primary, field_name, getattr(duplicate, field_name))

    for field_name in (
        "services",
        "specialties",
        "certifications",
        "awards",
        "social_profiles",
        "images_urls",
    ):
        merged = list(dict.fromkeys(getattr(primary, field_name) + getattr(duplicate, field_name)))
        setattr(primary, field_name, merged)

    for field_name, urls in duplicate.source_urls.items():
        primary.source_urls.setdefault(field_name, [])
        primary.source_urls[field_name] = list(dict.fromkeys(primary.source_urls[field_name] + urls))
    primary.evidence.extend(duplicate.evidence)
    return primary


def dedupe_records(records: list[BusinessRecord], threshold: float = 0.86) -> tuple[list[BusinessRecord], int]:
    merged: list[BusinessRecord] = []
    removed = 0
    for record in records:
        match_index = None
        for index, existing in enumerate(merged):
            if business_match_score(record, existing) >= threshold:
                match_index = index
                break
        if match_index is None:
            merged.append(record)
        else:
            merge_businesses(merged[match_index], record)
            removed += 1
    return merged, removed
