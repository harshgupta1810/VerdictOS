"""Integration tests for HITL disputes and delta ingestion."""

import pytest
from unittest.mock import MagicMock

from src.hitl.dispute import handle_user_dispute
from src.hitl.schemas import DisputeRequest
from src.db.models import Deal, Finding, DimensionStateRecord, Dispute, DeltaRun, AuditRecord

def test_post_verdict_dispute_reopens_dimension():
    # Setup mock db session
    mock_db = MagicMock()
    
    # Mock finding
    finding = Finding(
        finding_id="finding_1",
        deal_id="deal123",
        dimension="risk_exposure"
    )
    mock_db.get.return_value = finding
    
    # Mock dimension record
    dim_record = DimensionStateRecord(
        record_id="dim_1",
        deal_id="deal123",
        dimension="risk_exposure",
        state="settled"
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dim_record
    mock_db.execute.return_value = mock_result
    
    # Request False Negative
    request = DisputeRequest(
        scenario="B",
        dispute_reason="Missed a clause.",
        uploaded_document_path="new_evidence.pdf"
    )
    
    # Handle dispute
    dispute = handle_user_dispute(
        db=mock_db,
        deal_id="deal123",
        finding_id="finding_1",
        request=request,
        user_id="user1"
    )
    
    # Verify Dimension reopened
    assert dim_record.state == "active"
    
    # Verify Dispute created
    assert dispute.status == "pending"
    assert dispute.finding_id == "finding_1"
    
    # Verify DeltaRun and AuditRecord added
    added_instances = [args[0][0] for args in mock_db.add.call_args_list]
    delta_runs = [i for i in added_instances if isinstance(i, DeltaRun)]
    assert len(delta_runs) == 1
    assert delta_runs[0].deal_id == "deal123"
    assert delta_runs[0].status == "started"
    
    audit_records = [i for i in added_instances if isinstance(i, AuditRecord)]
    assert len(audit_records) == 2  # One for Dispute, one for Delta
    assert any(a.event_type == "DISPUTE_CREATED" for a in audit_records)
    assert any(a.event_type == "DELTA_REANALYSIS_STARTED" for a in audit_records)
    
    assert mock_db.commit.call_count == 2
