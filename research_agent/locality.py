from __future__ import annotations

import re

from research_agent.normalization import normalize_text


LOCATION_CORRECTIONS = {
    "andhrapradesh": "andhra pradesh",
    "arunachalpradesh": "arunachal pradesh",
    "himachalpradesh": "himachal pradesh",
    "madhyapradesh": "madhya pradesh",
    "uttarpradesh": "uttar pradesh",
    "westbengal": "west bengal",
    "unitedstates": "united states",
    "unitedstatesofamerica": "united states",
    "usa": "united states",
    "u s a": "united states",
    "uk": "united kingdom",
    "u k": "united kingdom",
    "uae": "united arab emirates",
    "u a e": "united arab emirates",
    "b c": "british columbia",
    "maharastra": "maharashtra",
    "thamjavur": "thanjavur",
    "tanjavur": "thanjavur",
    "tanjore": "thanjavur",
    "trichy": "tiruchirappalli",
    "ooty": "ooty",
    "udhagamandalam": "ooty",
    "karaikkudi": "karaikudi",
    "cape comorin": "kanyakumari",
}

LOCATION_ALIASES = {
    "thanjavur": ["thanjavur", "tanjore", "thanjavur tamil nadu", "tamil nadu"],
    "tiruchirappalli": ["tiruchirappalli", "trichy", "tiruchi", "tamil nadu"],
    "ooty": ["ooty", "udhagamandalam", "nilgiris", "the nilgiris", "ooty tamil nadu"],
    "karaikudi": ["karaikudi", "karaikkudi", "karaikudi tamil nadu", "sivaganga", "sivagangai"],
    "kanyakumari": ["kanyakumari", "kanniyakumari", "cape comorin", "kanyakumari tamil nadu", "tamil nadu"],
    "madurai": ["madurai", "madurai tamil nadu", "tamil nadu"],
    "coimbatore": ["coimbatore", "kovai", "coimbatore tamil nadu", "tamil nadu"],
    "chennai": ["chennai", "madras", "chennai tamil nadu", "tamil nadu"],
    "kerala": ["kerala", "kerala india"],
    "birmingham": ["birmingham"],
    "austin": ["austin", "austin texas", "texas"],
    "dallas": ["dallas", "dallas texas", "texas"],
    "houston": ["houston", "houston texas", "texas"],
    "chicago": ["chicago", "chicago illinois", "illinois"],
    "london": ["london", "london uk", "united kingdom", "england"],
    "toronto": ["toronto", "toronto ontario", "ontario", "canada"],
    "dubai": ["dubai", "dubai uae", "united arab emirates"],
}

REGION_SEARCH_LOCATIONS = {
    "andhra pradesh": [
        "visakhapatnam",
        "vijayawada",
        "guntur",
        "nellore",
        "kurnool",
        "tirupati",
        "kakinada",
        "rajahmundry",
        "ananthapur",
        "kadapa",
    ],
    "arunachal pradesh": ["itanagar", "naharlagun", "pasighat", "tawang", "ziro"],
    "assam": ["guwahati", "silchar", "dibrugarh", "jorhat", "tezpur", "nagaon", "tinsukia"],
    "bihar": ["patna", "gaya", "bhagalpur", "muzaffarpur", "darbhanga", "purnia"],
    "chhattisgarh": ["raipur", "bhilai", "bilaspur", "durg", "korba", "raigarh"],
    "delhi": ["new delhi", "delhi", "dwarka delhi", "rohini delhi", "saket delhi"],
    "goa": ["panaji", "margao", "vasco da gama", "mapusa", "ponda"],
    "gujarat": ["ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar", "gandhinagar"],
    "haryana": ["gurugram", "faridabad", "panipat", "ambala", "hisar", "karnal", "rohtak"],
    "himachal pradesh": ["shimla", "dharamshala", "solan", "mandi", "kullu", "hamirpur"],
    "jharkhand": ["ranchi", "jamshedpur", "dhanbad", "bokaro", "deoghar", "hazaribagh"],
    "karnataka": ["bengaluru", "mysuru", "mangaluru", "hubballi", "belagavi", "davangere", "ballari"],
    "tamil nadu": [
        "chennai",
        "coimbatore",
        "madurai",
        "tiruchirappalli",
        "salem",
        "tirunelveli",
        "thanjavur",
        "vellore",
        "erode",
        "thoothukudi",
        "dindigul",
        "kanyakumari",
        "karur",
        "namakkal",
        "cuddalore",
        "kanchipuram",
        "tiruppur",
        "sivaganga",
        "karaikudi",
        "nagapattinam",
    ],
    "tamilnadu": [
        "chennai",
        "coimbatore",
        "madurai",
        "tiruchirappalli",
        "salem",
        "tirunelveli",
        "thanjavur",
        "vellore",
        "erode",
        "thoothukudi",
        "dindigul",
        "kanyakumari",
        "karur",
        "namakkal",
        "cuddalore",
        "kanchipuram",
        "tiruppur",
        "sivaganga",
        "karaikudi",
        "nagapattinam",
    ],
    "kerala": [
        "kochi",
        "thiruvananthapuram",
        "kozhikode",
        "thrissur",
        "kollam",
        "kannur",
        "kottayam",
        "alappuzha",
        "palakkad",
        "malappuram",
        "pathanamthitta",
        "kasaragod",
        "idukki",
        "wayanad",
    ],
    "madhya pradesh": ["indore", "bhopal", "jabalpur", "gwalior", "ujjain", "sagar", "rewa"],
    "maharashtra": ["mumbai", "pune", "nagpur", "nashik", "thane", "aurangabad", "solapur", "kolhapur"],
    "manipur": ["imphal", "thoubal", "bishnupur", "churachandpur"],
    "meghalaya": ["shillong", "tura", "jowai", "nongpoh"],
    "mizoram": ["aizawl", "lunglei", "champhai", "serchhip"],
    "nagaland": ["kohima", "dimapur", "mokokchung", "tuensang"],
    "odisha": ["bhubaneswar", "cuttack", "rourkela", "berhampur", "sambalpur", "puri"],
    "punjab": ["ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali"],
    "rajasthan": ["jaipur", "jodhpur", "udaipur", "kota", "ajmer", "bikaner", "alwar"],
    "sikkim": ["gangtok", "namchi", "gyalshing", "mangan"],
    "telangana": ["hyderabad", "warangal", "nizamabad", "karimnagar", "khammam", "secunderabad"],
    "tripura": ["agartala", "udaipur tripura", "dharmanagar", "kailashahar"],
    "uttar pradesh": ["lucknow", "kanpur", "varanasi", "agra", "noida", "ghaziabad", "prayagraj", "meerut"],
    "uttarakhand": ["dehradun", "haridwar", "haldwani", "roorkee", "rishikesh", "nainital"],
    "west bengal": ["kolkata", "howrah", "durgapur", "asansol", "siliguri", "bardhaman", "kharagpur"],
    "andaman and nicobar islands": ["port blair", "diglipur", "mayabunder"],
    "chandigarh": ["chandigarh", "manimajra"],
    "dadra and nagar haveli and daman and diu": ["daman", "diu", "silvassa"],
    "jammu and kashmir": ["srinagar", "jammu", "anantnag", "baramulla", "udhampur"],
    "ladakh": ["leh", "kargil"],
    "lakshadweep": ["kavaratti", "agatti", "minicoy"],
    "puducherry": ["puducherry", "karaikal", "yanam", "mahe"],
    "united states": [
        "new york",
        "los angeles",
        "chicago",
        "houston",
        "phoenix",
        "philadelphia",
        "san antonio",
        "san diego",
        "dallas",
        "austin",
        "birmingham alabama",
    ],
    "usa": [
        "new york",
        "los angeles",
        "chicago",
        "houston",
        "phoenix",
        "philadelphia",
        "san antonio",
        "san diego",
        "dallas",
        "austin",
        "birmingham alabama",
    ],
    "alabama": ["birmingham alabama", "montgomery", "mobile", "huntsville", "tuscaloosa", "hoover"],
    "texas": ["austin", "dallas", "houston", "san antonio", "fort worth", "el paso", "plano", "arlington"],
    "illinois": ["chicago", "aurora illinois", "naperville", "joliet", "rockford", "springfield illinois", "peoria"],
    "california": ["los angeles", "san diego", "san jose", "san francisco", "fresno", "sacramento", "oakland"],
    "florida": ["miami", "orlando", "tampa", "jacksonville", "fort lauderdale", "st petersburg"],
    "new york state": ["new york", "buffalo", "rochester", "yonkers", "syracuse", "albany"],
    "united kingdom": ["london", "birmingham uk", "manchester", "leeds", "liverpool", "bristol", "glasgow", "edinburgh"],
    "england": ["london", "birmingham uk", "manchester", "leeds", "liverpool", "bristol", "sheffield", "nottingham"],
    "scotland": ["glasgow", "edinburgh", "aberdeen", "dundee", "inverness"],
    "canada": ["toronto", "montreal", "vancouver", "calgary", "edmonton", "ottawa", "winnipeg"],
    "ontario": ["toronto", "ottawa", "mississauga", "brampton", "hamilton", "london ontario", "kitchener"],
    "quebec": ["montreal", "quebec city", "laval", "gatineau", "longueuil"],
    "british columbia": ["vancouver", "surrey", "burnaby", "richmond", "victoria"],
    "alberta": ["calgary", "edmonton", "red deer", "lethbridge", "medicine hat"],
    "united arab emirates": ["dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah"],
    "uae": ["dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah"],
}

INDIA_REGION_KEYS = {
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "delhi",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "tamil nadu",
    "tamilnadu",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "andaman and nicobar islands",
    "chandigarh",
    "dadra and nagar haveli and daman and diu",
    "jammu and kashmir",
    "ladakh",
    "lakshadweep",
    "puducherry",
}

COUNTRY_REGION_KEYS = {
    "in": INDIA_REGION_KEYS,
    "us": {"united states", "usa", "alabama", "texas", "illinois", "california", "florida", "new york state"},
    "gb": {"united kingdom", "england", "scotland"},
    "ca": {"canada", "ontario", "quebec", "british columbia", "alberta"},
    "ae": {"united arab emirates", "uae"},
}

COUNTRY_ALIASES = {
    "in": ["india", "bharat"],
    "us": ["united states", "united states of america", "usa", "u s a"],
    "gb": ["united kingdom", "uk", "u k", "great britain", "england", "scotland"],
    "ca": ["canada"],
    "ae": ["united arab emirates", "uae", "u a e"],
}

OFF_LOCATION_HINTS = {
    "gujarat",
    "maharashtra",
    "west bengal",
    "tamil nadu",
    "kerala",
    "karnataka",
    "telangana",
    "ahmedabad",
    "surat",
    "vadodara",
    "rajkot",
    "mumbai",
    "pune",
    "nagpur",
    "nashik",
    "thane",
    "delhi",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "kolkata",
    "howrah",
    "durgapur",
    "asansol",
    "kochi",
    "thiruvananthapuram",
    "kozhikode",
    "thrissur",
    "texas",
    "illinois",
    "alabama",
    "california",
    "florida",
    "ontario",
    "quebec",
    "united kingdom",
    "united states",
    "canada",
    "united arab emirates",
    "austin",
    "dallas",
    "houston",
    "chicago",
    "birmingham alabama",
    "london",
    "toronto",
    "dubai",
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
    "clinics": ["clinic", "medical clinic", "health clinic", "specialty clinic", "diagnostic center"],
    "clinic": ["clinic", "medical clinic", "health clinic", "specialty clinic", "diagnostic center"],
    "hospitals": ["hospital", "medical center", "emergency hospital", "multi specialty hospital"],
    "hospital": ["hospital", "medical center", "emergency hospital", "multi specialty hospital"],
    "cardiologists": ["cardiologist", "cardiology clinic", "heart clinic", "cardiac care", "heart specialist", "cardiac hospital"],
    "cardiologist": ["cardiologist", "cardiology clinic", "heart clinic", "cardiac care", "heart specialist", "cardiac hospital"],
    "dermatologists": ["dermatologist", "skin clinic", "dermatology clinic", "cosmetology clinic"],
    "dermatologist": ["dermatologist", "skin clinic", "dermatology clinic", "cosmetology clinic"],
    "pediatricians": ["pediatrician", "paediatrician", "child specialist", "children clinic"],
    "pediatrician": ["pediatrician", "paediatrician", "child specialist", "children clinic"],
    "pharmacies": ["pharmacy", "medical store", "chemist", "drug store"],
    "pharmacy": ["pharmacy", "medical store", "chemist", "drug store"],
    "dentists": ["dentist", "dental clinic", "orthodontist"],
    "dentist": ["dentist", "dental clinic", "orthodontist"],
    "electricians": ["electrician", "electrical contractor", "electrical service", "electricals", "electrical works", "electrical shop", "wiring contractor", "wiring service", "electric repair"],
    "electrician": ["electrician", "electrical contractor", "electrical service", "electricals", "electrical works", "electrical shop", "wiring contractor", "wiring service", "electric repair"],
    "plumbers": ["plumber", "plumbing service", "plumbing contractor", "pipe repair"],
    "plumber": ["plumber", "plumbing service", "plumbing contractor", "pipe repair"],
    "hvac": ["hvac contractor", "air conditioning service", "ac repair", "heating contractor", "ventilation service"],
    "hvac contractors": ["hvac contractor", "air conditioning service", "ac repair", "heating contractor", "ventilation service"],
    "roofers": ["roofer", "roofing contractor", "roofing service"],
    "roofer": ["roofer", "roofing contractor", "roofing service"],
    "roofing contractors": ["roofing contractor", "roofer", "roofing service"],
    "lawyers": ["lawyer", "attorney", "advocate", "law firm", "legal service"],
    "lawyer": ["lawyer", "attorney", "advocate", "law firm", "legal service"],
    "family lawyers": ["family lawyer", "divorce lawyer", "family law attorney", "law firm"],
    "accountants": ["accountant", "chartered accountant", "tax consultant", "cpa"],
    "accountant": ["accountant", "chartered accountant", "tax consultant", "cpa"],
    "cpa": ["cpa", "certified public accountant", "accountant", "tax consultant"],
    "mechanics": ["mechanic", "car repair", "auto repair", "automobile service"],
    "mechanic": ["mechanic", "car repair", "auto repair", "automobile service"],
    "real estate agents": ["real estate agent", "realtor", "property consultant", "real estate agency"],
    "realtors": ["realtor", "real estate agent", "property consultant", "real estate agency"],
    "insurance agents": ["insurance agent", "insurance broker", "insurance agency"],
    "travel agents": ["travel agent", "tour operator", "travel agency"],
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
    if normalized == "tamilnadu":
        return "tamil nadu"
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


def is_known_location(value: str) -> bool:
    normalized = normalize_text(normalize_location(value))
    if not normalized:
        return False
    known = set(LOCATION_ALIASES) | set(REGION_SEARCH_LOCATIONS)
    for aliases in LOCATION_ALIASES.values():
        known.update(normalize_text(alias) for alias in aliases)
    for locations in REGION_SEARCH_LOCATIONS.values():
        known.update(normalize_text(location) for location in locations)
    return normalized in known


def _regions_for_location(value: str) -> set[str]:
    normalized = normalize_text(normalize_location(value))
    regions = set()
    for region, locations in REGION_SEARCH_LOCATIONS.items():
        if normalized == normalize_text(region) or normalized in {normalize_text(location) for location in locations}:
            regions.add(region)
    return regions


def _all_known_location_hints() -> set[str]:
    hints = set(OFF_LOCATION_HINTS)
    hints.update(REGION_SEARCH_LOCATIONS.keys())
    for locations in REGION_SEARCH_LOCATIONS.values():
        hints.update(locations)
    for aliases in LOCATION_ALIASES.values():
        hints.update(normalize_text(alias) for alias in aliases)
    return {normalize_text(hint) for hint in hints if normalize_text(hint)}


def _contains_location_phrase(haystack: str, hint: str) -> bool:
    normalized_hint = normalize_text(hint)
    if not normalized_hint:
        return False
    return bool(re.search(rf"\b{re.escape(normalized_hint)}\b", haystack))


def country_hint_for_text(text: str) -> str:
    haystack = normalize_text(text)
    if not haystack:
        return ""
    for code, aliases in COUNTRY_ALIASES.items():
        if any(_contains_location_phrase(haystack, alias) for alias in aliases):
            return code
    for code, regions in COUNTRY_REGION_KEYS.items():
        for region in regions:
            if _contains_location_phrase(haystack, region):
                return code
            if any(_contains_location_phrase(haystack, city) for city in REGION_SEARCH_LOCATIONS.get(region, [])):
                return code
    return ""


def region_search_locations(value: str, limit: int = 20) -> list[str]:
    normalized = normalize_text(normalize_location(value))
    locations = REGION_SEARCH_LOCATIONS.get(normalized, [])
    if not locations:
        return []
    return locations[:limit]


def expanded_search_locations(value: str, limit: int = 20) -> list[str]:
    regional = region_search_locations(value, limit=limit)
    if regional:
        return regional
    return location_aliases(value)[:limit]


def category_expansions(category: str) -> list[str]:
    category = normalize_category(category)
    normalized = normalize_text(category)
    expansions = CATEGORY_EXPANSIONS.get(normalized, [category])
    return list(dict.fromkeys([category, *expansions]))


def has_location_signal(text: str, location: str) -> bool:
    haystack = normalize_text(text)
    region_locations = region_search_locations(location)
    if region_locations and any(normalize_text(item) in haystack for item in region_locations):
        return True
    return any(normalize_text(alias) in haystack for alias in location_aliases(location))


def has_wrong_location_signal(text: str, location: str) -> bool:
    haystack = normalize_text(text)
    aliases = {normalize_text(alias) for alias in location_aliases(location)}
    aliases.update(normalize_text(item) for item in region_search_locations(location))
    for region in _regions_for_location(location):
        aliases.add(normalize_text(region))
        aliases.update(normalize_text(item) for item in REGION_SEARCH_LOCATIONS.get(region, []))
    for hint in _all_known_location_hints():
        if hint in aliases:
            continue
        if re.search(rf"\b{re.escape(hint)}\b", haystack):
            return True
    return False
