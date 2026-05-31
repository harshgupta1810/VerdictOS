"""Pydantic schemas for Phase 7 Verdict Output."""

from pydantic import BaseModel, ConfigDict, Field

class GoNoGoFinding(BaseModel):
    """A ranked finding included in the Go/No-Go brief."""
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    claim: str
    severity: str
    confidence: float
    dimension: str
    section_citation: str
    clause_type: str

class GoNoGoBrief(BaseModel):
    """The Go/No-Go brief summarizing settled and confirmed risks."""
    model_config = ConfigDict(extra="forbid")

    findings: list[GoNoGoFinding] = Field(default_factory=list)

class EscalationArgument(BaseModel):
    """Represents a side of an argument in the escalation list."""
    model_config = ConfigDict(extra="forbid")

    persona: str
    stance: str
    argument: str
    calibrated_confidence: str

class EscalationItem(BaseModel):
    """An item requiring human escalation (Contested/Unresolved findings)."""
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    claim: str
    dimension: str
    arguments: list[EscalationArgument] = Field(default_factory=list)
    has_contradictions: bool = False
    has_dropouts: bool = False
    judge_override: bool = False
    judge_notes: str = ""

class HumanEscalationList(BaseModel):
    """List of all items requiring human escalation."""
    model_config = ConfigDict(extra="forbid")

    escalations: list[EscalationItem] = Field(default_factory=list)

class EvidenceGapItem(BaseModel):
    """Details on a dimension or claim missing required evidence."""
    model_config = ConfigDict(extra="forbid")

    dimension: str
    missing_claims: list[str] = Field(default_factory=list)
    unconfirmed_entities: list[str] = Field(default_factory=list)
    suggested_remedies: list[str] = Field(default_factory=list)

class EvidenceGapReport(BaseModel):
    """Report detailing evidence gaps across the deal."""
    model_config = ConfigDict(extra="forbid")

    skipped_dimensions: list[str] = Field(default_factory=list)
    gaps: list[EvidenceGapItem] = Field(default_factory=list)

class VerdictOutput(BaseModel):
    """Final assembled JSON structured verdict for a deal."""
    model_config = ConfigDict(extra="forbid")

    deal_id: str
    brief: GoNoGoBrief
    escalation_list: HumanEscalationList
    evidence_gap_report: EvidenceGapReport
