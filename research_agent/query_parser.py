from __future__ import annotations

import re

from research_agent.models import SearchQuery
from research_agent.locality import is_known_location, normalize_category, normalize_location


LOCATION_SPLIT_RE = re.compile(r"\s+(?:in|near|around|within)\s+", re.IGNORECASE)
NOISE_RE = re.compile(r"\b(find|show|get|list|best|top|near me)\b", re.IGNORECASE)


def parse_user_query(raw_query: str) -> SearchQuery:
    raw_query = " ".join(raw_query.strip().split())
    cleaned = NOISE_RE.sub("", raw_query).strip(" ,")
    parts = LOCATION_SPLIT_RE.split(cleaned, maxsplit=1)
    if len(parts) == 2:
        category, location = parts[0].strip(" ,"), normalize_location(parts[1].strip(" ,"))
    else:
        inferred = _parse_location_without_preposition(cleaned)
        if inferred:
            category, location = inferred
        else:
            category, location = cleaned, ""
    category = normalize_category(category or raw_query)
    return SearchQuery(raw=raw_query, category=category, location=location)


def _parse_location_without_preposition(value: str) -> tuple[str, str] | None:
    tokens = value.split()
    if len(tokens) < 2:
        return None
    max_location_tokens = min(3, len(tokens) - 1)
    for size in range(max_location_tokens, 0, -1):
        prefix_location = " ".join(tokens[:size]).strip(" ,")
        suffix_category = " ".join(tokens[size:]).strip(" ,")
        if suffix_category and is_known_location(prefix_location):
            return suffix_category, normalize_location(prefix_location)

        suffix_location = " ".join(tokens[-size:]).strip(" ,")
        prefix_category = " ".join(tokens[:-size]).strip(" ,")
        if prefix_category and is_known_location(suffix_location):
            return prefix_category, normalize_location(suffix_location)
    return None


def infer_industry(category: str) -> str:
    text = category.lower()
    healthcare = {
        "doctor",
        "cardiologist",
        "dentist",
        "clinic",
        "physician",
        "pediatrician",
        "dermatologist",
        "orthopedic",
        "surgeon",
    }
    legal = {"lawyer", "attorney", "law firm", "family law", "personal injury", "criminal defense"}
    trades = {"plumber", "roofing", "roofer", "electrician", "contractor", "hvac", "landscaping"}
    food = {"restaurant", "cafe", "hotel", "bakery", "food", "dining", "eatery"}
    retail = {"shop", "store", "shopping", "showroom", "supermarket", "mall", "retail"}
    wellness = {"salon", "spa", "gym", "fitness", "beauty parlour"}
    education = {"school", "college", "training", "institute", "academy"}
    if any(term in text for term in healthcare):
        return "healthcare"
    if any(term in text for term in legal):
        return "legal"
    if any(term in text for term in trades):
        return "trades"
    if any(term in text for term in food):
        return "food_hospitality"
    if any(term in text for term in retail):
        return "retail"
    if any(term in text for term in wellness):
        return "wellness"
    if any(term in text for term in education):
        return "education"
    return "general"
