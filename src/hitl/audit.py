from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.db.models import DebateArg, AuditRecord
from src.hitl.schemas import AuditTrailResponse, AuditTranscriptEntry

def get_audit_trail_for_finding(db: Session, finding_id: str) -> AuditTrailResponse:
    """Retrieve debate transcripts and audit records for a specific finding_id."""
    
    # Retrieve debate arguments for this finding
    debate_args = db.query(DebateArg).filter(DebateArg.finding_id == finding_id).order_by(DebateArg.round_number).all()
    
    transcripts = []
    for arg in debate_args:
        transcripts.append(AuditTranscriptEntry(
            round_number=arg.round_number,
            persona_name=arg.persona_name,
            dimension=arg.dimension,
            stance=arg.stance,
            steelman=arg.steelman,
            argument=arg.argument,
            citations_array=arg.citations_array or [],
            calibrated_confidence=arg.calibrated_confidence,
            contradiction_flag=arg.contradiction_flag,
            bm25_verified=arg.bm25_verified
        ))
        
    # Retrieve relevant audit records (e.g. disputes, escalations related to this finding)
    # We can search the raw_payload JSON for the finding_id.
    # In SQLite JSON, we might have to use text search or simply filter in Python if JSON querying is limited.
    # Let's do a simple text match on the description or payload since we encode finding_id there.
    # SQLAlchemy JSON operators vary by dialect. A safe fallback:
    audit_records = db.query(AuditRecord).filter(
        or_(
            AuditRecord.description.like(f"%{finding_id}%")
        )
    ).order_by(AuditRecord.timestamp).all()
    
    audit_list = []
    for record in audit_records:
        audit_list.append({
            "event_type": record.event_type,
            "actor": record.actor,
            "description": record.description,
            "timestamp": record.timestamp.isoformat()
        })
        
    return AuditTrailResponse(
        finding_id=finding_id,
        transcripts=transcripts,
        audit_records=audit_list
    )
