import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.main import app
from src.db.models import Finding, AuditRecord
from src.db.session import get_db
from src.api.middleware.validation import validate_deal_state

@pytest.fixture
def override_deps():
    db_mock = AsyncMock()
    deal_mock = MagicMock()
    deal_mock.deal_id = "123"
    deal_mock.status = "complete"
    deal_mock.metadata_json = {}
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[validate_deal_state] = lambda: deal_mock
    yield db_mock, deal_mock
    app.dependency_overrides.clear()

def test_create_deal(override_deps) -> None:
    db_mock, _ = override_deps
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    with patch("src.api.routes.deals.run_deal_pipeline") as mock_run:
        response = client.post("/api/v1/deals", json={"client_id": "client1", "document_paths": ["doc1.pdf"]})
        assert response.status_code == 201
        assert "deal_id" in response.json()
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()

def test_get_deal_status(override_deps) -> None:
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/api/v1/deals/123/status")
    assert response.status_code == 200
    assert response.json()["deal_id"] == "123"

def test_get_deal_verdict_complete(override_deps) -> None:
    db_mock, deal_mock = override_deps
    finding = Finding(finding_id="f1", claim="c", citation="cit", confidence=0.9, severity="high", dimension="ip", clause_type="ip_assignment")
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [finding]
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/api/v1/deals/123/verdict")
    assert response.status_code == 200
    assert len(response.json()["findings"]) == 1

def test_get_deal_verdict_incomplete(override_deps) -> None:
    db_mock, deal_mock = override_deps
    deal_mock.status = "ingesting"
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/api/v1/deals/123/verdict")
    assert response.status_code == 400

def test_get_deal_audit(override_deps) -> None:
    db_mock, deal_mock = override_deps
    import datetime
    audit = AuditRecord(audit_id=1, event_type="test", actor="user", description="desc", timestamp=datetime.datetime.now(datetime.timezone.utc))
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [audit]
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.get("/api/v1/deals/123/audit")
    assert response.status_code == 200

def test_upload_delta_documents(override_deps) -> None:
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/documents", json={"document_paths": ["doc2.pdf"]})
    assert response.status_code == 200

def test_dispute_finding_success(override_deps) -> None:
    db_mock, deal_mock = override_deps
    finding = Finding(finding_id="f1")
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = finding
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/findings/f1/dispute", json={"dispute_reason": "this is wrong enough"})
    assert response.status_code == 200

def test_dispute_finding_not_found(override_deps) -> None:
    db_mock, deal_mock = override_deps
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/findings/f1/dispute", json={"dispute_reason": "this is wrong enough"})
    assert response.status_code == 404

def test_websocket_stream() -> None:
    client = TestClient(app)
    with client.websocket_connect("/api/v1/deals/123/stream", headers={"X-API-Key": "dev-key-123"}) as websocket:
        websocket.send_text("ping")
        websocket.close()
