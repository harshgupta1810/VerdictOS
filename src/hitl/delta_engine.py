from typing import List
from sqlalchemy.orm import Session
from src.db.models import DeltaRun, AuditRecord

def trigger_delta_reanalysis(db: Session, deal_id: str, requested_docs: List[str] = None, uploaded_document_path: str = None) -> DeltaRun:
    """
    Trigger the delta re-analysis engine.
    
    Re-indexes only new document delta chunks, re-runs affected specialist
    agents and debate dimensions, labels supplementary findings, and merges
    them into the existing verdict.
    """
    delta_run = DeltaRun(
        deal_id=deal_id,
        status="started",
        metadata_json={
            "requested_docs": requested_docs or [],
            "uploaded_document_path": uploaded_document_path
        }
    )
    db.add(delta_run)
    
    audit = AuditRecord(
        deal_id=deal_id,
        event_type="DELTA_REANALYSIS_STARTED",
        actor="system",
        description=f"Delta re-analysis started for deal {deal_id}",
        raw_payload={"delta_run_id": delta_run.run_id}
    )
    db.add(audit)
    db.commit()
    db.refresh(delta_run)
    
    # In a full implementation, this would trigger an async celery task
    # that executes the pipeline Phase 1-7 only on the delta.
    
    return delta_run
