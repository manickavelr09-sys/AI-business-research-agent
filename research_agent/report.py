from __future__ import annotations

from research_agent.models import BusinessRecord


def data_quality_summary(records: list[BusinessRecord]) -> dict[str, str]:
    total = max(len(records), 1)
    checks = {
        "records_with_website": sum(1 for record in records if record.website),
        "records_with_phone_number": sum(1 for record in records if record.phone),
        "records_with_working_hours": sum(1 for record in records if record.working_hours),
        "records_with_license_information": sum(1 for record in records if record.license_information),
        "records_with_email": sum(1 for record in records if record.email),
        "records_with_address": sum(1 for record in records if record.address),
        "records_with_rating": sum(1 for record in records if record.rating),
    }
    return {key: f"{value / total:.0%}" for key, value in checks.items()}


def verified_count(records: list[BusinessRecord]) -> int:
    return sum(
        1
        for record in records
        if any(value.verified_level in {"medium", "high"} for value in record.verification.values())
    )
