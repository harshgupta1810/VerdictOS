"""API Request Models.

Pydantic schemas for incoming API request bodies
(deal submissions, dispute payloads, escalation resolutions).
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DealCreateRequest(BaseModel):
    """Payload for creating a new deal."""
    
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(..., description="The ID of the client creating the deal.")
    metadata_json: dict[str, Any] | None = Field(default=None, description="Optional metadata for the deal.")
    document_paths: list[str] = Field(..., min_length=1, description="List of file paths to the documents to ingest.")
    selected_agents: list[str] | None = Field(
        default=None,
        description="Optional list of agent IDs to activate. If omitted, the planner auto-assigns agents."
    )


class DisputeRequest(BaseModel):
    """Payload for disputing a finding."""
    
    model_config = ConfigDict(extra="forbid")
    
    dispute_reason: str = Field(..., min_length=10, description="The reason for the dispute provided by the user.")


class EscalationResolveRequest(BaseModel):
    """Payload for resolving an escalation."""
    
    model_config = ConfigDict(extra="forbid")
    
    decision: str = Field(..., description="The decision made by the expert (e.g., 'accepted', 'rejected', 'modified').")
    decision_text: str | None = Field(default=None, description="Optional detailed text about the decision.")
    resolved_by: str = Field(..., description="The name or ID of the human expert resolving the escalation.")


class DocumentUploadRequest(BaseModel):
    """Payload for delta document uploads."""
    
    model_config = ConfigDict(extra="forbid")
    
    document_paths: list[str] = Field(..., min_length=1, description="List of file paths to new documents to ingest.")
