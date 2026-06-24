from research_agent.pdf_report import build_research_pdf


def test_build_research_pdf_returns_pdf_bytes() -> None:
    report = {
        "search_summary": {
            "query": "Electricians in Trichy",
            "businesses_found": 1,
            "businesses_verified": 1,
            "duplicate_records_removed": 0,
            "sources_searched": 3,
            "research_duration": "1.20 seconds",
        },
        "data_quality_summary": {
            "records_with_website": "100%",
            "records_with_phone_number": "100%",
            "records_with_license_information": "0%",
            "records_with_rating": "100%",
        },
        "business_results": [
            {
                "business_name": "Example Electricals",
                "address": "Trichy, Tamil Nadu",
                "phone": "+91 99999 99999",
                "website": "https://example.com",
                "services": ["Electrical repair"],
                "source_urls": {"phone": ["https://example.com/contact"]},
                "verification": {
                    "phone": {
                        "value": "+91 99999 99999",
                        "verified_level": "high",
                        "confidence": 0.9,
                        "sources": ["https://example.com/contact"],
                    }
                },
                "conflicts": {},
            }
        ],
    }
    pdf = build_research_pdf(report)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
