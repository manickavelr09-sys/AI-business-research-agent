from __future__ import annotations

from urllib.parse import urlparse


SOURCE_TYPE_SCORES = {
    "official_website": 0.95,
    "government": 0.95,
    "professional_association": 0.9,
    "google_maps": 0.88,
    "serper_places": 0.86,
    "serper_search": 0.62,
    "tavily_search": 0.68,
    "geoapify": 0.78,
    "healthcare_directory": 0.82,
    "legal_directory": 0.82,
    "business_directory": 0.75,
    "review_platform": 0.72,
    "social_profile": 0.62,
    "search_result": 0.45,
    "unknown": 0.4,
    "content_lead": 0.36,
}

DIRECTORY_HINTS = {
    "yelp.": "review_platform",
    "yellowpages.": "business_directory",
    "healthgrades.": "healthcare_directory",
    "zocdoc.": "healthcare_directory",
    "webmd.": "healthcare_directory",
    "doximity.": "healthcare_directory",
    "avvo.": "legal_directory",
    "justia.": "legal_directory",
    "findlaw.": "legal_directory",
    "bbb.": "business_directory",
    "linkedin.": "social_profile",
    "facebook.": "social_profile",
    "instagram.": "social_profile",
    "justdial.": "business_directory",
    "sulekha.": "business_directory",
    "indiamart.": "business_directory",
    "cybo.": "business_directory",
    "yappe.": "business_directory",
    "webindia123.": "business_directory",
    "cylex.": "business_directory",
    "hotfrog.": "business_directory",
    "tripadvisor.": "review_platform",
    "zomato.": "review_platform",
    "restaurant-guru.": "review_platform",
    "magicpin.": "review_platform",
    "dineout.": "review_platform",
    "quora.": "content_lead",
    "reddit.": "content_lead",
    ".gov": "government",
    ".us": "government",
}


def classify_source(url: str, candidate_website: str = "") -> str:
    host = urlparse(url).netloc.lower()
    website_host = urlparse(candidate_website).netloc.lower() if candidate_website else ""
    if website_host and host.endswith(website_host):
        return "official_website"
    for hint, source_type in DIRECTORY_HINTS.items():
        if hint in host:
            return source_type
    return "unknown"


def reliability_for(source_type: str) -> float:
    return SOURCE_TYPE_SCORES.get(source_type, SOURCE_TYPE_SCORES["unknown"])
