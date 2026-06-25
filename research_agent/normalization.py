from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse


PUNCT_RE = re.compile(r"[^a-z0-9]+")
BUSINESS_SUFFIX_RE = re.compile(
    r"\b(llc|inc|corp|corporation|company|co|pllc|pc|pa|ltd|the|clinic|center|centre)\b",
    re.IGNORECASE,
)


def coerce_source_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(
            coerce_source_text(item)
            for item in value.values()
            if item not in (None, "", [], {})
        )
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(
            coerce_source_text(item)
            for item in value
            if item not in (None, "", [], {})
        )
    return str(value)


def normalize_text(value: Any) -> str:
    value = BUSINESS_SUFFIX_RE.sub(" ", coerce_source_text(value))
    value = PUNCT_RE.sub(" ", value.lower())
    return " ".join(value.split())


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", coerce_source_text(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) < 8:
        return ""
    return digits


def normalize_url(value: Any) -> str:
    value = coerce_source_text(value)
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc.lower().removeprefix("www.")
    return host.rstrip("/")


def normalize_address(value: Any) -> str:
    text = coerce_source_text(value).lower()
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
