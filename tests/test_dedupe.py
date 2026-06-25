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


def test_dedupe_tolerates_list_phone_from_source_metadata() -> None:
    left = BusinessRecord(business_name="ABC Heart Clinic", phone=["(205) 555-0100"])  # type: ignore[arg-type]
    right = BusinessRecord(business_name="ABC Heart Clinic", phone="205-555-0100")

    assert business_match_score(left, right) > 0.95


def test_map_source_urls_do_not_dedupe_unrelated_businesses() -> None:
    left = BusinessRecord(
        business_name="The Park Avenue Hotel",
        address="Nabikhan Street, Chennai, Tamil Nadu",
        website="https://www.openstreetmap.org/?mlat=13.09&mlon=80.29",
    )
    right = BusinessRecord(
        business_name="Grand Oliver",
        address="Varasidhi Vinayakar Koil Street, Chennai, Tamil Nadu",
        website="https://www.openstreetmap.org/?mlat=13.09&mlon=80.29",
    )

    assert business_match_score(left, right) < 0.86
    merged, removed = dedupe_records([left, right])
    assert removed == 0
    assert len(merged) == 2


def test_real_matching_website_still_dedupes() -> None:
    left = BusinessRecord(business_name="Hotel Lakeview", website="https://hotellakeview.example/rooms")
    right = BusinessRecord(business_name="Lake View Hotel", website="https://www.hotellakeview.example/contact")

    assert business_match_score(left, right) >= 0.94
