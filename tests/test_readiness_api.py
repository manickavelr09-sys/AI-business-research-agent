from fastapi.testclient import TestClient

from research_agent.api import app


def test_readiness_endpoint_reports_capabilities_without_secret_values() -> None:
    client = TestClient(app)

    response = client.get("/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "degraded"}
    assert "maps" in payload["providers"]
    assert "search" in payload["providers"]
    assert payload["capabilities"]["lead_mining_from_list_pages"]
    assert payload["capabilities"]["verification_and_conflict_detection"]
    assert all(isinstance(value, bool) for value in payload["providers"]["maps"].values())
    assert all(isinstance(value, bool) for value in payload["providers"]["search"].values())
