import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from src.api.main import app
from src.db.models import Escalation
from src.db.session import get_db
from src.api.middleware.validation import validate_deal_state

@pytest.fixture
def override_deps():
    db_mock = AsyncMock()
    deal_mock = MagicMock()
    deal_mock.deal_id = "123"
    deal_mock.status = "complete"
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[validate_deal_state] = lambda: deal_mock
    yield db_mock, deal_mock
    app.dependency_overrides.clear()

def test_resolve_escalation_success(override_deps) -> None:
    db_mock, deal_mock = override_deps
    escalation = Escalation(escalation_id="e1", status="pending")
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = escalation
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/escalations/e1/resolve", json={"decision": "agree", "decision_text": "ok", "resolved_by": "user"})
    assert response.status_code == 200
    assert escalation.status == "resolved"

def test_resolve_escalation_not_found(override_deps) -> None:
    db_mock, deal_mock = override_deps
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/escalations/e1/resolve", json={"decision": "agree", "decision_text": "ok", "resolved_by": "user"})
    assert response.status_code == 404

def test_resolve_escalation_already_resolved(override_deps) -> None:
    db_mock, deal_mock = override_deps
    escalation = Escalation(escalation_id="e1", status="resolved")
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = escalation
    db_mock.execute.return_value = result_mock
    
    client = TestClient(app, headers={"X-API-Key": "dev-key-123"})
    response = client.post("/api/v1/deals/123/escalations/e1/resolve", json={"decision": "agree", "decision_text": "ok", "resolved_by": "user"})
    assert response.status_code == 400
