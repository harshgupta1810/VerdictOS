"""Escalation Endpoints.

POST /api/v1/deals/{id}/escalations/{eid}/resolve - Resolve an escalation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from src.db.session import get_db
from src.db.models import Deal, Escalation, AuditRecord
from src.api.schemas.requests import EscalationResolveRequest
from src.api.middleware.validation import validate_deal_state

router = APIRouter(prefix="/deals/{id}/escalations", tags=["escalations"])

@router.post("/{eid}/resolve")
async def resolve_escalation(
    eid: str,
    request: EscalationResolveRequest,
    db: AsyncSession = Depends(get_db),
    deal: Deal = Depends(validate_deal_state)
):
    """Resolve an escalation by a human expert."""
    result = await db.execute(
        select(Escalation).where(Escalation.escalation_id == eid, Escalation.deal_id == deal.deal_id)
    )
    escalation = result.scalars().first()
    
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found for this deal.")
        
    if escalation.status == "resolved":
        raise HTTPException(status_code=400, detail="Escalation is already resolved.")
        
    escalation.status = "resolved"
    escalation.decision = request.decision
    escalation.decision_text = request.decision_text
    escalation.resolved_by = request.resolved_by
    # pyrefly: ignore [deprecated]
    escalation.resolved_at = datetime.utcnow()
    
    # Audit log
    audit = AuditRecord(
        deal_id=deal.deal_id,
        event_type="ESCALATION_RESOLVED",
        actor=request.resolved_by,
        description=f"Escalation {eid} resolved with decision: {request.decision}"
    )
    db.add(audit)
    
    await db.commit()
    
    return {"escalation_id": eid, "status": "resolved"}
