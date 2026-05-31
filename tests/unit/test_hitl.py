import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Deal, Finding, Escalation, Dispute, DeltaRun, AuditRecord, DebateArg
from src.hitl.schemas import EscalationResolutionRequest, DisputeRequest
from src.hitl.escalation import create_escalation, update_escalation_status, resolve_escalation
from src.hitl.dispute import handle_user_dispute
from src.hitl.delta_engine import trigger_delta_reanalysis
from src.hitl.audit import get_audit_trail_for_finding

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

@pytest.fixture
def sample_deal_and_finding(test_db):
    deal = Deal(client_id="client-1")
    test_db.add(deal)
    test_db.commit()
    
    finding = Finding(
        deal_id=deal.deal_id,
        claim="Test Claim",
        citation="Test Citation",
        section_id="Sec 1",
        confidence="high",
        dimension="dim1",
        agent_name="agent1",
        severity="medium",
        clause_type="general"
    )
    test_db.add(finding)
    test_db.commit()
    return deal.deal_id, finding.finding_id

def test_create_and_update_escalation(test_db, sample_deal_and_finding):
    deal_id, finding_id = sample_deal_and_finding
    
    esc = create_escalation(test_db, deal_id, finding_id)
    assert esc.status == "pending"
    assert esc.deal_id == deal_id
    
    esc = update_escalation_status(test_db, esc.escalation_id, "in-progress", "admin")
    assert esc.status == "in-progress"
    
    # Check audit record
    audit = test_db.query(AuditRecord).filter(AuditRecord.deal_id == deal_id).all()
    assert len(audit) == 2
    assert audit[0].event_type == "ESCALATION_CREATED"
    assert audit[1].event_type == "ESCALATION_STATUS_CHANGE"

def test_resolve_escalation_path(test_db, sample_deal_and_finding):
    deal_id, finding_id = sample_deal_and_finding
    esc = create_escalation(test_db, deal_id, finding_id)
    
    req = EscalationResolutionRequest(
        decision="resolve",
        decision_text="It is safe",
        resolved_by="expert@verdict.os"
    )
    
    resolved_esc = resolve_escalation(test_db, esc.escalation_id, req)
    assert resolved_esc.status == "resolved"
    
    # original finding remains
    orig = test_db.query(Finding).filter(Finding.finding_id == finding_id).first()
    assert orig.confidence == "high"
    
    # new finding added
    findings = test_db.query(Finding).filter(Finding.deal_id == deal_id).all()
    assert len(findings) == 2
    assert findings[1].confidence == "human_confirmed"
    assert "Human Resolution Override" in findings[1].notes

def test_dispute_scenario_b(test_db, sample_deal_and_finding):
    deal_id, finding_id = sample_deal_and_finding
    
    req = DisputeRequest(
        scenario="B",
        dispute_reason="Missed clause",
        uploaded_document_path="path/to/doc.pdf"
    )
    
    dispute = handle_user_dispute(test_db, deal_id, finding_id, req, "user1")
    assert dispute.status == "pending"
    
    # Delta run should be triggered
    runs = test_db.query(DeltaRun).filter(DeltaRun.deal_id == deal_id).all()
    assert len(runs) == 1
    assert runs[0].status == "started"

def test_audit_query_service(test_db, sample_deal_and_finding):
    deal_id, finding_id = sample_deal_and_finding
    
    arg = DebateArg(
        finding_id=finding_id,
        round_number=1,
        persona_name="Critic",
        stance="against",
        steelman="Steelman text",
        argument="Arg text",
        calibrated_confidence="low"
    )
    test_db.add(arg)
    test_db.commit()
    
    resp = get_audit_trail_for_finding(test_db, finding_id)
    assert resp.finding_id == finding_id
    assert len(resp.transcripts) == 1
    assert resp.transcripts[0].persona_name == "Critic"
