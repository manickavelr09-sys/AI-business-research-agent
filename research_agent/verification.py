from __future__ import annotations

from collections import defaultdict
from typing import Any

from research_agent.models import BusinessRecord, LIST_FIELDS, SCALAR_FIELDS, SourceEvidence, VerifiedValue
from research_agent.normalization import normalize_address, normalize_phone, normalize_text, normalize_url


def _canonical(field_name: str, value: Any) -> str:
    if isinstance(value, list):
        return "|".join(sorted(normalize_text(str(item)) for item in value if item))
    text = str(value or "")
    if field_name == "phone":
        return normalize_phone(text)
    if field_name == "website":
        return normalize_url(text)
    if field_name == "address":
        return normalize_address(text)
    return normalize_text(text)


def _choose_value(field_name: str, evidence_items: list[SourceEvidence]) -> tuple[Any, VerifiedValue, list[dict]]:
    grouped: dict[str, list[SourceEvidence]] = defaultdict(list)
    for item in evidence_items:
        key = _canonical(field_name, item.value)
        if key:
            grouped[key].append(item)
    if not grouped:
        return "", VerifiedValue(), []

    def group_score(group: list[SourceEvidence]) -> float:
        unique_sources = {item.source_url for item in group}
        source_types = {item.source_type for item in group}
        reliability = sum(item.reliability for item in group) / max(len(group), 1)
        return reliability * 0.65 + min(len(unique_sources), 4) * 0.08 + min(len(source_types), 3) * 0.04

    ranked = sorted(grouped.values(), key=group_score, reverse=True)
    winner = ranked[0]
    winner_sources = sorted({item.source_url for item in winner})
    confidence = min(group_score(winner), 0.99)
    if len(winner_sources) >= 3 and confidence >= 0.8:
        level = "high"
    elif len(winner_sources) >= 2 or confidence >= 0.72:
        level = "medium"
    else:
        level = "low"

    conflicts = []
    for group in ranked[1:]:
        conflicts.append(
            {
                "value": group[0].value,
                "sources": sorted({item.source_url for item in group}),
                "source_types": sorted({item.source_type for item in group}),
            }
        )

    verified = VerifiedValue(
        value=winner[0].value,
        confidence=confidence,
        verified_level=level,
        sources=winner_sources,
        evidence_count=len(winner),
    )
    return winner[0].value, verified, conflicts


def verify_record(record: BusinessRecord) -> BusinessRecord:
    evidence_by_field: dict[str, list[SourceEvidence]] = defaultdict(list)
    for item in record.evidence:
        evidence_by_field[item.field].append(item)

    conflicts: dict[str, list[dict]] = {}
    verification: dict[str, VerifiedValue] = {}
    for field_name in SCALAR_FIELDS:
        value, verified, field_conflicts = _choose_value(field_name, evidence_by_field[field_name])
        if value:
            setattr(record, field_name, value)
            verification[field_name] = verified
        if field_conflicts:
            conflicts[field_name] = field_conflicts

    for field_name in LIST_FIELDS:
        values = []
        for item in evidence_by_field[field_name]:
            if isinstance(item.value, list):
                values.extend(str(value) for value in item.value if value)
            elif item.value:
                values.append(str(item.value))
        deduped = list(dict.fromkeys(values))
        if deduped:
            setattr(record, field_name, deduped)
            verification[field_name] = VerifiedValue(
                value=deduped,
                confidence=min(0.55 + len(record.source_urls.get(field_name, [])) * 0.1, 0.9),
                verified_level="medium" if len(record.source_urls.get(field_name, [])) > 1 else "low",
                sources=record.source_urls.get(field_name, []),
                evidence_count=len(values),
            )

    record.conflicts = conflicts
    record.verification = verification
    completeness = sum(1 for field_name in SCALAR_FIELDS if getattr(record, field_name)) / len(SCALAR_FIELDS)
    verification_strength = (
        sum(value.confidence for value in verification.values()) / max(len(verification), 1)
    )
    record.reliability_score = min(completeness * 0.35 + verification_strength * 0.65, 1.0)
    return record
