from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SCALAR_FIELDS = (
    "business_name",
    "address",
    "phone",
    "email",
    "website",
    "working_hours",
    "rating",
    "review_count",
    "license_information",
)

LIST_FIELDS = (
    "services",
    "specialties",
    "certifications",
    "awards",
    "social_profiles",
    "images_urls",
)


@dataclass(frozen=True)
class SourceEvidence:
    field: str
    value: Any
    source_url: str
    source_type: str
    reliability: float
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "reliability": self.reliability,
            "observed_at": self.observed_at,
        }


@dataclass
class VerifiedValue:
    value: Any = ""
    confidence: float = 0.0
    verified_level: str = "unverified"
    sources: list[str] = field(default_factory=list)
    evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "verified_level": self.verified_level,
            "sources": sorted(set(self.sources)),
            "evidence_count": self.evidence_count,
        }


@dataclass
class BusinessRecord:
    business_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    working_hours: str = ""
    rating: str = ""
    review_count: str = ""
    services: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)
    license_information: str = ""
    certifications: list[str] = field(default_factory=list)
    awards: list[str] = field(default_factory=list)
    social_profiles: list[str] = field(default_factory=list)
    images_urls: list[str] = field(default_factory=list)
    source_urls: dict[str, list[str]] = field(default_factory=dict)
    evidence: list[SourceEvidence] = field(default_factory=list)
    conflicts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    verification: dict[str, VerifiedValue] = field(default_factory=dict)
    reliability_score: float = 0.0

    def add_evidence(self, evidence: SourceEvidence) -> None:
        if evidence.value in (None, "", [], {}):
            return
        self.evidence.append(evidence)
        self.source_urls.setdefault(evidence.field, [])
        if evidence.source_url not in self.source_urls[evidence.field]:
            self.source_urls[evidence.field].append(evidence.source_url)

    def to_flat_dict(self) -> dict[str, Any]:
        return {
            "business_name": self.business_name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "working_hours": self.working_hours,
            "rating": self.rating,
            "review_count": self.review_count,
            "services": self.services,
            "specialties": self.specialties,
            "license_information": self.license_information,
            "certifications": self.certifications,
            "awards": self.awards,
            "social_profiles": self.social_profiles,
            "images_urls": self.images_urls,
            "source_urls": self.source_urls,
        }

    def to_dict(self) -> dict[str, Any]:
        data = self.to_flat_dict()
        data.update(
            {
                "verification": {
                    field_name: verified.to_dict()
                    for field_name, verified in sorted(self.verification.items())
                },
                "conflicts": self.conflicts,
                "reliability_score": round(self.reliability_score, 3),
                "evidence": [item.to_dict() for item in self.evidence],
            }
        )
        return data


@dataclass(frozen=True)
class SearchQuery:
    raw: str
    category: str
    location: str
    modifiers: list[str] = field(default_factory=list)

    def display(self) -> str:
        if self.location:
            return f"{self.category} in {self.location}"
        return self.category


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    rank: int


@dataclass
class ResearchReport:
    query: str
    started_at: str
    completed_at: str
    duration_seconds: float
    businesses_found: int
    businesses_verified: int
    duplicate_records_removed: int
    sources_searched: int
    data_quality: dict[str, str]
    results: list[BusinessRecord]
    research_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "search_summary": {
                "query": self.query,
                "businesses_found": self.businesses_found,
                "businesses_verified": self.businesses_verified,
                "duplicate_records_removed": self.duplicate_records_removed,
                "sources_searched": self.sources_searched,
                "research_duration": f"{self.duration_seconds:.2f} seconds",
                "started_at": self.started_at,
                "completed_at": self.completed_at,
            },
            "data_quality_summary": self.data_quality,
            "research_summary": self.research_summary,
            "business_results": [business.to_dict() for business in self.results],
        }
