from datetime import datetime
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from src.db.models import Escalation, Finding, AuditRecord, Deal
from src.hitl.schemas import EscalationResolutionRequest
from src.hitl.delta_engine import trigger_delta_reanalysis

def create_escalation(db: Session, deal_id: str, finding_id: Optional[str] = None) -> Escalation:
    """Create a new escalation and log the status transition."""
    escalation = Escalation(
        deal_id=deal_id,
        finding_id=finding_id,
        status="pending"
    )
    db.add(escalation)
    db.flush()

    audit = AuditRecord(
        deal_id=deal_id,
        event_type="ESCALATION_CREATED",
        actor="system",
        description=f"Escalation {escalation.escalation_id} created for finding {finding_id}",
        raw_payload={"escalation_id": escalation.escalation_id, "finding_id": finding_id}
    )
    db.add(audit)
    db.commit()
    db.refresh(escalation)
    return escalation

def update_escalation_status(db: Session, escalation_id: str, new_status: str, actor: str) -> Escalation:
    """Update escalation status and append audit record."""
    escalation = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
    if not escalation:
        raise ValueError(f"Escalation {escalation_id} not found.")

    old_status = escalation.status
    escalation.status = new_status
    if new_status == "resolved":
        # pyrefly: ignore [deprecated]
        escalation.resolved_at = datetime.utcnow()

    audit = AuditRecord(
        deal_id=escalation.deal_id,
        event_type="ESCALATION_STATUS_CHANGE",
        actor=actor,
        description=f"Escalation {escalation_id} status changed from {old_status} to {new_status}",
        raw_payload={"escalation_id": escalation_id, "old_status": old_status, "new_status": new_status}
    )
    db.add(audit)
    db.commit()
    db.refresh(escalation)
    return escalation

def resolve_escalation(db: Session, escalation_id: str, request: EscalationResolutionRequest) -> Escalation:
    """Handle escalation resolution based on the decision path."""
    escalation = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
    if not escalation:
        raise ValueError(f"Escalation {escalation_id} not found.")

    if escalation.status == "resolved":
        raise ValueError(f"Escalation {escalation_id} is already resolved.")

    escalation.decision = request.decision
    escalation.decision_text = request.decision_text
    escalation.resolved_by = request.resolved_by

    if request.decision == "resolve":
        # Append human-confirmed finding as additive record; original AI finding never modified
        if escalation.finding_id:
            original_finding = db.query(Finding).filter(Finding.finding_id == escalation.finding_id).first()
            if original_finding:
                # Add human override note to original finding via an audit record or additive finding
                # The checklist says "append human-confirmed finding as additive record; original AI finding never modified"
                new_finding = Finding(
                    deal_id=original_finding.deal_id,
                    claim=original_finding.claim,
                    citation=original_finding.citation,
                    section_id=original_finding.section_id,
                    confidence="human_confirmed",
                    dimension=original_finding.dimension,
                    agent_name=f"human_expert_{request.resolved_by}",
                    severity=original_finding.severity,
                    clause_type=original_finding.clause_type,
                    verified=True,
                    cross_refs=original_finding.cross_refs,
                    notes=f"Human Resolution Override: {request.decision_text}"
                )
                db.add(new_finding)

    elif request.decision == "request_docs":
        # Trigger delta re-analysis
        trigger_delta_reanalysis(
            db=db, 
            deal_id=escalation.deal_id, 
            requested_docs=request.supporting_docs_requested or []
        )
        
    elif request.decision == "accept_risk":
        # Log formal written acceptance
        pass # The audit record below serves as the formal log

    else:
        raise ValueError(f"Unknown decision path: {request.decision}")

    escalation.status = "resolved"
    # pyrefly: ignore [deprecated]
    escalation.resolved_at = datetime.utcnow()

    # Append audit record
    audit = AuditRecord(
        deal_id=escalation.deal_id,
        event_type="ESCALATION_RESOLVED",
        actor=request.resolved_by,
        description=f"Escalation {escalation_id} resolved with decision: {request.decision}",
        raw_payload=request.model_dump()
    )
    db.add(audit)
    db.commit()
    db.refresh(escalation)
    return escalation
