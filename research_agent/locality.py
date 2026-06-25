from __future__ import annotations

import re

from research_agent.normalization import normalize_text


LOCATION_CORRECTIONS = {
    "thamjavur": "thanjavur",
    "tanjavur": "thanjavur",
    "tanjore": "thanjavur",
    "trichy": "tiruchirappalli",
    "ooty": "ooty",
    "udhagamandalam": "ooty",
    "karaikkudi": "karaikudi",
}

LOCATION_ALIASES = {
    "thanjavur": ["thanjavur", "tanjore", "thanjavur tamil nadu", "tamil nadu"],
    "tiruchirappalli": ["tiruchirappalli", "trichy", "tiruchi", "tamil nadu"],
    "ooty": ["ooty", "udhagamandalam", "nilgiris", "the nilgiris", "ooty tamil nadu"],
    "karaikudi": ["karaikudi", "karaikkudi", "karaikudi tamil nadu", "sivaganga", "sivagangai"],
}

OFF_LOCATION_HINTS = {
    "gujarat",
    "ahmedabad",
    "surat",
    "vadodara",
    "rajkot",
    "mumbai",
    "delhi",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "kolkata",
}

CATEGORY_EXPANSIONS = {
    "restaurants": ["restaurant", "restaurants", "food delivery", "dining", "eatery", "family restaurant", "veg restaurant", "non veg restaurant"],
    "restaurant": ["restaurant", "restaurants", "food delivery", "dining", "eatery", "family restaurant", "veg restaurant", "non veg restaurant"],
    "cafes": ["cafe", "coffee shop", "bakery cafe"],
    "cafe": ["cafe", "coffee shop", "bakery cafe"],
    "hotels": ["hotel", "lodging", "accommodation"],
    "hotel": ["hotel", "lodging", "accommodation"],
    "shops": ["shop", "store", "retail store", "shopping", "showroom"],
    "shopping": ["shop", "store", "retail store", "shopping", "showroom", "mall"],
    "stores": ["store", "shop", "retail store", "showroom"],
    "salons": ["salon", "beauty parlour", "beauty salon", "hair salon", "spa"],
    "salon": ["salon", "beauty parlour", "beauty salon", "hair salon", "spa"],
    "gyms": ["gym", "fitness centre", "fitness center", "health club"],
    "gym": ["gym", "fitness centre", "fitness center", "health club"],
    "schools": ["school", "private school", "education", "training institute"],
    "school": ["school", "private school", "education", "training institute"],
    "doctors": ["doctor", "physician", "medical clinic", "hospital", "clinic"],
    "doctor": ["doctor", "physician", "medical clinic", "hospital", "clinic"],
    "dentists": ["dentist", "dental clinic", "orthodontist"],
    "dentist": ["dentist", "dental clinic", "orthodontist"],
    "electricians": ["electrician", "electrical contractor", "electrical service", "electricals", "electrical works", "electrical shop", "wiring contractor", "wiring service", "electric repair"],
    "electrician": ["electrician", "electrical contractor", "electrical service", "electricals", "electrical works", "electrical shop", "wiring contractor", "wiring service", "electric repair"],
    "plumbers": ["plumber", "plumbing service", "plumbing contractor", "pipe repair"],
    "plumber": ["plumber", "plumbing service", "plumbing contractor", "pipe repair"],
    "roofers": ["roofer", "roofing contractor", "roofing service"],
    "roofer": ["roofer", "roofing contractor", "roofing service"],
    "roofing contractors": ["roofing contractor", "roofer", "roofing service"],
    "lawyers": ["lawyer", "attorney", "advocate", "law firm", "legal service"],
    "lawyer": ["lawyer", "attorney", "advocate", "law firm", "legal service"],
    "family lawyers": ["family lawyer", "divorce lawyer", "family law attorney", "law firm"],
    "accountants": ["accountant", "chartered accountant", "tax consultant", "cpa"],
    "accountant": ["accountant", "chartered accountant", "tax consultant", "cpa"],
    "mechanics": ["mechanic", "car repair", "auto repair", "automobile service"],
    "mechanic": ["mechanic", "car repair", "auto repair", "automobile service"],
    "repair services": ["repair service", "service centre", "service center", "appliance repair"],
}

CATEGORY_CORRECTIONS = {
    "cardialagist": "cardiologists",
    "cardiologyst": "cardiologists",
    "cardiologit": "cardiologists",
    "dentel clinic": "dental clinic",
    "electritian": "electricians",
    "electricion": "electricians",
    "plumers": "plumbers",
    "restaurtents": "restaurants",
    "resturants": "restaurants",
}


def normalize_location(value: str) -> str:
    normalized = normalize_text(value)
    corrected = LOCATION_CORRECTIONS.get(normalized)
    if corrected:
        return corrected
    return " ".join((value or "").strip().split())


def normalize_category(value: str) -> str:
    normalized = normalize_text(value)
    return CATEGORY_CORRECTIONS.get(normalized, " ".join((value or "").strip().split()))


def location_aliases(value: str) -> list[str]:
    normalized = normalize_location(value)
    aliases = LOCATION_ALIASES.get(normalized, [normalized])
    return list(dict.fromkeys([alias for alias in aliases if alias]))


def category_expansions(category: str) -> list[str]:
    category = normalize_category(category)
    normalized = normalize_text(category)
    expansions = CATEGORY_EXPANSIONS.get(normalized, [category])
    return list(dict.fromkeys([category, *expansions]))


def has_location_signal(text: str, location: str) -> bool:
    haystack = normalize_text(text)
    return any(normalize_text(alias) in haystack for alias in location_aliases(location))


def has_wrong_location_signal(text: str, location: str) -> bool:
    haystack = normalize_text(text)
    aliases = set(location_aliases(location))
    for hint in OFF_LOCATION_HINTS:
        if hint in aliases:
            continue
        if re.search(rf"\b{re.escape(hint)}\b", haystack):
            return True
    return False
