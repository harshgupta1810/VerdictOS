from sqlalchemy.orm import Session
from src.db.models import Dispute, AuditRecord, Escalation
from src.hitl.schemas import DisputeRequest, AuditTrailResponse
from src.hitl.delta_engine import trigger_delta_reanalysis
from src.hitl.audit import get_audit_trail_for_finding
from src.hitl.escalation import create_escalation

def handle_user_dispute(db: Session, deal_id: str, finding_id: str, request: DisputeRequest, user_id: str):
    """Process a user dispute based on the chosen scenario."""
    
    if request.scenario == "D":
        # Scenario D: Transparency
        # Return complete audit trail for the specified finding
        return get_audit_trail_for_finding(db, finding_id)
        
    # For A, B, C, create the Dispute record
    dispute = Dispute(
        deal_id=deal_id,
        finding_id=finding_id,
        dispute_reason=request.dispute_reason,
        status="pending"
    )
    db.add(dispute)
    db.flush()
    
    audit = AuditRecord(
        deal_id=deal_id,
        event_type="DISPUTE_CREATED",
        actor=user_id,
        description=f"Dispute {dispute.dispute_id} created for finding {finding_id} (Scenario {request.scenario})",
        raw_payload={"dispute_id": dispute.dispute_id, "scenario": request.scenario, "reason": request.dispute_reason}
    )
    db.add(audit)
    
    if request.scenario == "A":
        # Scenario A: False Positive
        # Route to escalation list for expert arbitration
        escalation = create_escalation(db, deal_id, finding_id)
        
    elif request.scenario == "B":
        # Scenario B: False Negative
        # Re-open the dimension state to active
        from src.db.models import Finding, DimensionStateRecord
        from sqlalchemy import select
        finding = db.get(Finding, finding_id)
        if finding:
            stmt = select(DimensionStateRecord).where(
                DimensionStateRecord.deal_id == deal_id,
                DimensionStateRecord.dimension == finding.dimension
            )
            dim_record = db.execute(stmt).scalar_one_or_none()
            if dim_record:
                dim_record.state = "active"
                
        # Accept uploaded document or clause pointer, trigger delta re-analysis
        trigger_delta_reanalysis(
            db=db, 
            deal_id=deal_id, 
            uploaded_document_path=request.uploaded_document_path
        )
        
    elif request.scenario == "C":
        # Scenario C: Wrong Recommendation
        # Escalate to human expert with user reasoning
        escalation = create_escalation(db, deal_id, finding_id)
        
    db.commit()
    db.refresh(dispute)
    
    return dispute
