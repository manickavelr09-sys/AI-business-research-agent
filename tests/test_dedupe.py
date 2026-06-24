from research_agent.dedupe import business_match_score, dedupe_records
from research_agent.models import BusinessRecord


def test_phone_match_dedupes_businesses() -> None:
    left = BusinessRecord(business_name="ABC Heart Clinic", phone="(205) 555-0100")
    right = BusinessRecord(business_name="ABC Cardiology Center", phone="205-555-0100")
    assert business_match_score(left, right) > 0.95


def test_dedupe_merges_duplicate() -> None:
    records = [
        BusinessRecord(business_name="ABC Heart Clinic", phone="(205) 555-0100"),
        BusinessRecord(business_name="ABC Cardiology Center", phone="205-555-0100", website="https://abc.example"),
    ]
    merged, removed = dedupe_records(records)
    assert removed == 1
    assert len(merged) == 1
    assert merged[0].website == "https://abc.example"
