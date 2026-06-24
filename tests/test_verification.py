from research_agent.models import BusinessRecord, SourceEvidence
from research_agent.verification import verify_record


def test_verification_flags_conflicting_phone() -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("phone", "(205) 111-1111", "https://site.example", "official_website", 0.95))
    record.add_evidence(SourceEvidence("phone", "(205) 222-2222", "https://dir.example", "business_directory", 0.75))
    verified = verify_record(record)
    assert verified.phone == "(205) 111-1111"
    assert "phone" in verified.conflicts
