from __future__ import annotations

from urllib.parse import urlparse

from research_agent.models import SearchQuery, SearchResult
from research_agent.locality import (
    category_expansions,
    has_location_signal,
    has_wrong_location_signal,
    location_aliases,
)
from research_agent.query_parser import infer_industry


GENERAL_SOURCES = [
    "yelp.com",
    "yellowpages.com",
    "bbb.org",
    "justdial.com",
    "sulekha.com",
    "indiaonline.in",
    "linkedin.com/company",
    "facebook.com",
]

INDUSTRY_SOURCES = {
    "healthcare": [
        "healthgrades.com",
        "zocdoc.com",
        "webmd.com",
        "doximity.com",
        "npiprofile.com",
        "medicare.gov/care-compare",
    ],
    "legal": [
        "avvo.com",
        "justia.com",
        "findlaw.com",
        "lawyers.com",
        "martindale.com",
        "statebar",
    ],
    "trades": [
        "angi.com",
        "homeadvisor.com",
        "thumbtack.com",
        "buildzoom.com",
        "contractors-license.org",
        "justdial.com",
        "sulekha.com",
    ],
    "food_hospitality": [
        "tripadvisor.com",
        "zomato.com",
        "swiggy.com",
        "eazydiner.com",
        "restaurant-guru.in",
        "facebook.com",
        "instagram.com",
    ],
    "retail": [
        "justdial.com",
        "sulekha.com",
        "indiamart.com",
        "facebook.com",
        "instagram.com",
        "linkedin.com/company",
    ],
    "wellness": [
        "justdial.com",
        "sulekha.com",
        "practo.com",
        "facebook.com",
        "instagram.com",
    ],
    "education": [
        "schools.org.in",
        "justdial.com",
        "sulekha.com",
        "shiksha.com",
        "facebook.com",
    ],
}


def build_discovery_queries(query: SearchQuery) -> list[str]:
    base = query.display()
    industry = infer_industry(query.category)
    categories = category_expansions(query.category)
    locations = location_aliases(query.location) if query.location else [""]
    queries = [
        base,
        f"{base} phone address website",
        f"{base} contact number address",
        f"{base} official website phone",
        f"{base} business directory",
        f"{base} reviews hours",
        f"{base} Google maps reviews",
    ]
    for category in categories:
        for location in locations[:3]:
            if location:
                queries.extend(
                    [
                        f'"{category}" "{location}" phone address',
                        f'"{category}" "{location}" contact number',
                        f'"{category}" "{location}" mobile number',
                        f'"{category}" "{location}" official website',
                        f'"{category}" "{location}" opening hours',
                        f'"{category}" "{location}" ratings reviews',
                        f'"{category}" "{location}" Google reviews',
                        f'"{category}" "{location}" site:justdial.com',
                        f'"{category}" "{location}" site:sulekha.com',
                        f'"{category}" "{location}" site:facebook.com',
                        f'"{category}" "{location}" site:instagram.com',
                    ]
                )
    for source in GENERAL_SOURCES + INDUSTRY_SOURCES.get(industry, []):
        queries.append(f"{base} site:{source}")
    if industry == "healthcare":
        queries.extend([f"{base} license NPI", f"{base} board certified"])
    elif industry == "legal":
        queries.extend([f"{base} bar license", f"{base} practice areas"])
    elif industry == "trades":
        queries.extend([f"{base} license insured", f"{base} services reviews"])
    elif industry == "food_hospitality":
        queries.extend([f"{base} menu photos reviews", f"{base} delivery contact number"])
    elif industry == "retail":
        queries.extend([f"{base} showroom contact number", f"{base} catalogue photos reviews"])
    elif industry == "wellness":
        queries.extend([f"{base} appointment phone services", f"{base} price list reviews"])
    elif industry == "education":
        queries.extend([f"{base} admission contact number", f"{base} affiliation reviews"])
    return list(dict.fromkeys(queries))


def result_relevance_score(result: SearchResult, query: SearchQuery) -> float:
    text = f"{result.title} {result.snippet} {result.url}"
    score = 0.15
    if query.location and has_location_signal(text, query.location):
        score += 0.65
    category_terms = [item.lower().rstrip("s") for item in category_expansions(query.category)]
    if any(term and term in text.lower() for term in category_terms):
        score += 0.15
    if query.location and has_wrong_location_signal(text, query.location):
        score -= 0.7
    host = urlparse(result.url).netloc.lower()
    if any(source in host for source in ("google.com", "bing.com", "duckduckgo.com")):
        score -= 0.4
    if re_search_generic_list(result.title):
        score -= 0.15
    return max(score, 0.0)


def re_search_generic_list(title: str) -> bool:
    title_lower = title.lower()
    return any(phrase in title_lower for phrase in ("in india", "near me in india", "top 10"))


def filter_result(result: SearchResult, query: SearchQuery | None = None) -> bool:
    host = urlparse(result.url).netloc.lower()
    path = urlparse(result.url).path.lower()
    if not host:
        return False
    blocked = ("google.com/search", "bing.com/search", "duckduckgo.com")
    if any(item in result.url.lower() for item in blocked):
        return False
    if "google." in host and path.startswith("/maps/search"):
        return False
    if query and query.location:
        return result_relevance_score(result, query) >= 0.35
    return True
