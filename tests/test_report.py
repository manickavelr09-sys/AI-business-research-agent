from research_agent.models import BusinessRecord
from research_agent.report import data_quality_summary


def test_data_quality_includes_service_coverage() -> None:
    records = [
        BusinessRecord(business_name="Sea View Restaurant", services=["Seafood"]),
        BusinessRecord(business_name="The Curry"),
    ]

    quality = data_quality_summary(records)

    assert quality["records_with_services"] == "50%"
