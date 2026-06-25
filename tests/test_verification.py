from research_agent.models import BusinessRecord, SourceEvidence
from research_agent.verification import verify_record


def test_verification_flags_conflicting_phone() -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("phone", "(205) 111-1111", "https://site.example", "official_website", 0.95))
    record.add_evidence(SourceEvidence("phone", "(205) 222-2222", "https://dir.example", "business_directory", 0.75))
    verified = verify_record(record)
    assert verified.phone == "(205) 111-1111"
    assert "phone" in verified.conflicts


def test_verification_ignores_postal_code_phone_fragment() -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("phone", "-, 246001", "https://dir.example", "business_directory", 0.75))

    verified = verify_record(record)

    assert verified.phone == ""
    assert "phone" not in verified.verification


def test_verification_cleans_directory_phone_and_address_display() -> None:
    record = BusinessRecord()
    record.add_evidence(SourceEvidence("phone", "8667510681, -", "https://dir.example", "business_directory", 0.75))
    record.add_evidence(
        SourceEvidence(
            "address",
            "['Vivekanandapuram, Kanyakumari - 629702'], -, Kanyakumari, 629702, IN",
            "https://dir.example",
            "business_directory",
            0.75,
        )
    )

    verified = verify_record(record)

    assert verified.phone == "8667510681"
    assert verified.address == "Vivekanandapuram, Kanyakumari - 629702, Kanyakumari, 629702, IN"
