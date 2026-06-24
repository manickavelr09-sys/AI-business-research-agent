from __future__ import annotations

import re
from urllib.parse import urlparse


PUNCT_RE = re.compile(r"[^a-z0-9]+")
BUSINESS_SUFFIX_RE = re.compile(
    r"\b(llc|inc|corp|corporation|company|co|pllc|pc|pa|ltd|the|clinic|center|centre)\b",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    value = BUSINESS_SUFFIX_RE.sub(" ", value or "")
    value = PUNCT_RE.sub(" ", value.lower())
    return " ".join(value.split())


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def normalize_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc.lower().removeprefix("www.")
    return host.rstrip("/")


def normalize_address(value: str) -> str:
    text = (value or "").lower()
    replacements = {
        " street": " st",
        " avenue": " ave",
        " road": " rd",
        " boulevard": " blvd",
        " drive": " dr",
        " suite": " ste",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = PUNCT_RE.sub(" ", text)
    return " ".join(text.split())
