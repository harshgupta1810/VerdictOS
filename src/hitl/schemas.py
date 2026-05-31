from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field

class EscalationResolutionRequest(BaseModel):
    """Payload for resolving an expert escalation."""
    decision: Literal["resolve", "request_docs", "accept_risk"] = Field(
        ..., description="The resolution decision path."
    )
    decision_text: str = Field(
        ..., description="Explanation or reasoning for the decision."
    )
    resolved_by: str = Field(
        ..., description="Identity (e.g. email) of the human expert."
    )
    supporting_docs_requested: Optional[List[str]] = Field(
        default=None, description="List of document names requested, if applicable."
    )

class DisputeRequest(BaseModel):
    """Payload for filing an end-user dispute against a finding."""
    scenario: Literal["A", "B", "C", "D"] = Field(
        ..., description="Dispute scenario: A(false positive), B(false negative), C(wrong recommendation), D(transparency)"
    )
    dispute_reason: str = Field(
        ..., description="User rebuttal or reasoning for the dispute."
    )
    uploaded_document_path: Optional[str] = Field(
        default=None, description="Path or reference to an uploaded document for Scenario B."
    )
    clause_pointer: Optional[str] = Field(
        default=None, description="Pointer to specific clause for Scenario B."
    )

class AuditTranscriptEntry(BaseModel):
    """Formatted debate transcript entry for transparency."""
    round_number: int
    persona_name: str
    dimension: str
    stance: str
    steelman: str
    argument: str
    citations_array: List[str]
    calibrated_confidence: str
    contradiction_flag: bool
    bm25_verified: bool

class AuditTrailResponse(BaseModel):
    """Response payload for transparency audit queries."""
    finding_id: str
    transcripts: List[AuditTranscriptEntry]
    audit_records: List[Dict[str, Any]]
