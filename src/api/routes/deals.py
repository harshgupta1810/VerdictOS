"""Deal Endpoints.

POST /api/v1/deals          - Submit a deal with document manifest
GET  /api/v1/deals/{id}/status  - Fetch progress
WebSocket /api/v1/deals/{id}/stream - Stream progress via WebSocket
GET  /api/v1/deals/{id}/verdict - Compiled structured JSON verdict
GET  /api/v1/deals/{id}/audit   - Immutable debate transcripts
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import uuid

from src.db.session import get_db
from src.db.models import Deal, AuditRecord, Finding, Dispute
from src.api.schemas.requests import DealCreateRequest, DisputeRequest, DocumentUploadRequest
from src.api.websockets.emitter import manager
from src.api.middleware.validation import validate_deal_state

# We will import the pipeline runner task later from workers
from src.workers.tasks import run_deal_pipeline

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("")
async def list_deals(db: AsyncSession = Depends(get_db)):
    """List all deals."""
    result = await db.execute(select(Deal).order_by(Deal.deal_id))
    deals = result.scalars().all()
    return [
        {
            "deal_id": d.deal_id,
            "client_id": d.client_id,
            "status": d.status,
            "metadata": d.metadata_json,
        }
        for d in deals
    ]


@router.post("", status_code=201)
async def create_deal(
    request: DealCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new deal and trigger the background pipeline."""
    deal_id = str(uuid.uuid4())
    deal = Deal(
        deal_id=deal_id,
        client_id=request.client_id,
        status="created",
        metadata_json=request.metadata_json
    )
    db.add(deal)
    await db.commit()
    
    # Trigger background pipeline
    background_tasks.add_task(run_deal_pipeline, deal_id, request.document_paths)
    
    return {"deal_id": deal_id, "status": deal.status}


@router.get("/{id}/status")
async def get_deal_status(deal: Deal = Depends(validate_deal_state)):
    """Fetch current state of the deal."""
    return {
        "deal_id": deal.deal_id,
        "status": deal.status,
        "metadata": deal.metadata_json
    }


@router.websocket("/{id}/stream")
async def deal_stream(websocket: WebSocket, id: str):
    """WebSocket endpoint for real-time pipeline events."""
    # Note: WebSocket validation can be trickier, ignoring validate_deal_state dependency here 
    # to keep it simple, but we can verify the ID via a DB query if needed.
    await manager.connect(id, websocket)
    try:
        while True:
            # Keep connection open, optionally receive ping/pong
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(id, websocket)


@router.get("/{id}/verdict")
async def get_deal_verdict(db: AsyncSession = Depends(get_db), deal: Deal = Depends(validate_deal_state)):
    """Fetch the final verdict (all findings)."""
    if deal.status != "complete":
        raise HTTPException(status_code=400, detail="Verdict is not yet available.")
        
    result = await db.execute(select(Finding).where(Finding.deal_id == deal.deal_id))
    findings = result.scalars().all()
    
    return {
        "deal_id": deal.deal_id,
        "status": deal.status,
        "findings": [
            {
                "finding_id": f.finding_id,
                "claim": f.claim,
                "citation": f.citation,
                "confidence": f.confidence,
                "severity": f.severity,
                "dimension": f.dimension,
                "clause_type": f.clause_type,
            } for f in findings
        ]
    }


@router.get("/{id}/audit")
async def get_deal_audit(db: AsyncSession = Depends(get_db), deal: Deal = Depends(validate_deal_state)):
    """Fetch the immutable audit trail for the deal."""
    result = await db.execute(
        select(AuditRecord).where(AuditRecord.deal_id == deal.deal_id).order_by(AuditRecord.timestamp)
    )
    audits = result.scalars().all()
    return {
        "deal_id": deal.deal_id,
        "audit_trail": [
            {
                "audit_id": a.audit_id,
                "event_type": a.event_type,
                "actor": a.actor,
                "description": a.description,
                "timestamp": a.timestamp.isoformat()
            } for a in audits
        ]
    }


@router.post("/{id}/documents")
async def upload_delta_documents(
    request: DocumentUploadRequest,
    background_tasks: BackgroundTasks,
    deal: Deal = Depends(validate_deal_state)
):
    """Upload new documents and trigger delta re-analysis."""
    # Assume delta pipeline runner is a variation or a flag in run_deal_pipeline
    background_tasks.add_task(run_deal_pipeline, deal.deal_id, request.document_paths, True)
    return {"status": "delta_analysis_triggered"}


@router.post("/{id}/findings/{fid}/dispute")
async def dispute_finding(
    fid: str,
    request: DisputeRequest,
    db: AsyncSession = Depends(get_db),
    deal: Deal = Depends(validate_deal_state)
):
    """File an end-user dispute against a specific finding."""
    # Check if finding exists
    result = await db.execute(select(Finding).where(Finding.finding_id == fid, Finding.deal_id == deal.deal_id))
    finding = result.scalars().first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found for this deal.")
        
    dispute = Dispute(
        deal_id=deal.deal_id,
        finding_id=fid,
        dispute_reason=request.dispute_reason,
        status="pending"
    )
    db.add(dispute)
    
    # Audit log
    audit = AuditRecord(
        deal_id=deal.deal_id,
        event_type="DISPUTE_FILED",
        actor="User",
        description=f"Dispute filed for finding {fid}"
    )
    db.add(audit)
    
    await db.commit()
    return {"dispute_id": dispute.dispute_id, "status": "pending"}
