from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from research_agent.models import BusinessRecord, SearchResult, SourceEvidence
from research_agent.source_reliability import classify_source, reliability_for


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?"
    r"|(?:\+?91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}"
    r"|0\d{2,5}[\s.-]?\d{5,8}"
)
HOURS_RE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s*[-:]\s*[^<\n]{3,80}",
    re.IGNORECASE,
)
RATING_RE = re.compile(r"\b([1-5](?:\.\d)?)\s*(?:out of|/)\s*5\b", re.IGNORECASE)
REVIEW_RE = re.compile(r"\b(\d[\d,]*)\s+reviews?\b", re.IGNORECASE)
LICENSE_RE = re.compile(r"\b(?:license|lic\.?|npi|bar no\.?|bar number)\s*[:#]?\s*([A-Z0-9 -]{4,30})", re.IGNORECASE)

SOCIAL_HOSTS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com")
SERVICE_WORDS = (
    "services",
    "practice areas",
    "specialties",
    "treatments",
    "procedures",
    "emergency",
    "consultation",
)


def record_from_search_result(result: SearchResult) -> BusinessRecord:
    record = BusinessRecord()
    source_type = classify_source(result.url)
    reliability = reliability_for("search_result")
    name = _clean_title(result.title)
    if name:
        record.add_evidence(SourceEvidence("business_name", name, result.url, "search_result", reliability))
    if result.url:
        record.add_evidence(SourceEvidence("website", result.url, result.url, source_type, reliability_for(source_type)))
    _extract_from_text(record, f"{result.title} {result.snippet}", result.url, "search_result", reliability)
    return record


def extract_business_from_html(url: str, html_text: str, seed: BusinessRecord | None = None) -> BusinessRecord:
    record = seed or BusinessRecord()
    soup = BeautifulSoup(html_text, "lxml")
    text = soup.get_text(" ", strip=True)
    source_type = classify_source(url, record.website)
    reliability = reliability_for(source_type)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    json_ld_records = _extract_json_ld(soup)
    for item in json_ld_records:
        _apply_structured_data(record, item, url, source_type, reliability)

    meta_title = _meta(soup, "og:title") or title
    if meta_title:
        record.add_evidence(SourceEvidence("business_name", _clean_title(meta_title), url, source_type, reliability))
    description = _meta(soup, "description") or _meta(soup, "og:description")
    if description:
        _extract_from_text(record, description, url, source_type, reliability)
    _extract_from_text(record, text[:50_000], url, source_type, reliability)

    canonical = _canonical_url(soup, url)
    if canonical:
        record.add_evidence(SourceEvidence("website", canonical, url, source_type, reliability))

    social_profiles, images = _extract_links_and_images(soup, url)
    if social_profiles:
        record.add_evidence(SourceEvidence("social_profiles", social_profiles, url, source_type, reliability))
    if images:
        record.add_evidence(SourceEvidence("images_urls", images[:20], url, source_type, reliability))

    services = _extract_services(soup)
    if services:
        record.add_evidence(SourceEvidence("services", services, url, source_type, reliability))
        record.add_evidence(SourceEvidence("specialties", services, url, source_type, reliability))
    return record


def _extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    items: list[dict] = []
    for script in soup.find_all("script", {"type": re.compile("ld\\+json", re.I)}):
        try:
            payload = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            candidates = payload
        elif isinstance(payload, dict) and "@graph" in payload:
            candidates = payload.get("@graph", [])
        else:
            candidates = [payload]
        items.extend(item for item in candidates if isinstance(item, dict))
    return items


def _apply_structured_data(
    record: BusinessRecord,
    item: dict,
    source_url: str,
    source_type: str,
    reliability: float,
) -> None:
    item_type = item.get("@type", "")
    if isinstance(item_type, list):
        item_type = " ".join(item_type)
    relevant = any(
        token in str(item_type).lower()
        for token in ("localbusiness", "organization", "physician", "dentist", "legalservice")
    )
    if not relevant and not any(key in item for key in ("telephone", "address", "openingHours")):
        return
    mapping = {
        "name": "business_name",
        "telephone": "phone",
        "email": "email",
        "url": "website",
        "openingHours": "working_hours",
        "description": "services",
    }
    for source_key, field_name in mapping.items():
        value = item.get(source_key)
        if value:
            record.add_evidence(SourceEvidence(field_name, value, source_url, source_type, reliability))
    if item.get("address"):
        record.add_evidence(
            SourceEvidence("address", _format_address(item["address"]), source_url, source_type, reliability)
        )
    aggregate_rating = item.get("aggregateRating") or {}
    if isinstance(aggregate_rating, dict):
        if aggregate_rating.get("ratingValue"):
            record.add_evidence(
                SourceEvidence("rating", str(aggregate_rating["ratingValue"]), source_url, source_type, reliability)
            )
        if aggregate_rating.get("reviewCount"):
            record.add_evidence(
                SourceEvidence(
                    "review_count", str(aggregate_rating["reviewCount"]), source_url, source_type, reliability
                )
            )


def _format_address(value) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    parts = [
        value.get("streetAddress"),
        value.get("addressLocality"),
        value.get("addressRegion"),
        value.get("postalCode"),
        value.get("addressCountry"),
    ]
    return ", ".join(str(part) for part in parts if part)


def _extract_from_text(
    record: BusinessRecord,
    text: str,
    source_url: str,
    source_type: str,
    reliability: float,
) -> None:
    text = unescape(text or "")
    for email in sorted(set(EMAIL_RE.findall(text))):
        record.add_evidence(SourceEvidence("email", email, source_url, source_type, reliability))
    for phone in sorted(set(_clean_phone_match(match.group(0)) for match in PHONE_RE.finditer(text))):
        record.add_evidence(SourceEvidence("phone", phone, source_url, source_type, reliability))
    hours = sorted(set(match.group(0).strip() for match in HOURS_RE.finditer(text)))
    if hours:
        record.add_evidence(SourceEvidence("working_hours", "; ".join(hours[:14]), source_url, source_type, reliability))
    rating = RATING_RE.search(text)
    if rating:
        record.add_evidence(SourceEvidence("rating", rating.group(1), source_url, source_type, reliability))
    review = REVIEW_RE.search(text)
    if review:
        record.add_evidence(SourceEvidence("review_count", review.group(1), source_url, source_type, reliability))
    license_match = LICENSE_RE.search(text)
    if license_match:
        record.add_evidence(
            SourceEvidence("license_information", license_match.group(0), source_url, source_type, reliability)
        )


def _extract_links_and_images(soup: BeautifulSoup, base_url: str) -> tuple[list[str], list[str]]:
    socials: list[str] = []
    images: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        host = urlparse(href).netloc.lower()
        if any(social in host for social in SOCIAL_HOSTS):
            socials.append(href.split("?")[0])
    for image in soup.find_all("img", src=True):
        src = urljoin(base_url, image["src"])
        if src.startswith(("http://", "https://")):
            images.append(src)
    return list(dict.fromkeys(socials)), list(dict.fromkeys(images))


def _extract_services(soup: BeautifulSoup) -> list[str]:
    candidates: list[str] = []
    for node in soup.find_all(["li", "a", "h2", "h3"]):
        text = node.get_text(" ", strip=True)
        if 3 <= len(text) <= 80 and any(word in text.lower() for word in SERVICE_WORDS):
            candidates.append(text)
    return list(dict.fromkeys(candidates))[:30]


def _canonical_url(soup: BeautifulSoup, fallback: str) -> str:
    canonical = soup.find("link", rel=lambda rel: rel and "canonical" in rel)
    if canonical and canonical.get("href"):
        return urljoin(fallback, canonical["href"])
    parsed = urlparse(fallback)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else fallback


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
    return tag.get("content", "").strip() if tag else ""


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+[-|]\s+.*$", "", title or "").strip()
    return title[:180]


def _clean_phone_match(value: str) -> str:
    return " ".join((value or "").strip(" .,-").split())
