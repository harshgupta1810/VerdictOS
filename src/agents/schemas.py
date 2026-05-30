"""Typed contracts for specialist planning, query construction, and analysis output."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.common.models import ClauseType


class AgentName(str, Enum):  # noqa: UP042 - Phase 2 dispatch consumes these string enum values.
    """Stable specialist identifiers shared with Phase 2 dispatch."""

    IP = "ip_agent"
    LITIGATION = "litigation_agent"
    REGULATORY = "regulatory_agent"
    PRIVACY = "privacy_agent"
    FINANCE = "finance_agent"
    TAX = "tax_agent"
    INSURANCE = "insurance_agent"
    HR = "hr_agent"
    GOVERNANCE = "governance_agent"
    RELATED_PARTY = "related_party_agent"
    CYBER = "cyber_agent"
    ASSETS = "assets_agent"
    SUPPLIER = "supplier_agent"
    CUSTOMER = "customer_agent"
    REPUTATION = "reputation_agent"
    ESG = "esg_agent"


class SpecialistDefinition(BaseModel):
    """Data-driven specialist scope used by planner routing."""

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName
    routing_terms: list[str] = Field(min_length=1)
    clause_types: list[ClauseType] = Field(default_factory=list)
    synonym_groups: dict[str, list[str]] = Field(default_factory=dict)
    top_k: int = Field(default=10, ge=1, le=100)


class ActiveSpecialistManifest(BaseModel):
    """Deterministic planner output consumed by Phase 2 dispatch."""

    model_config = ConfigDict(extra="forbid")

    active_agents: list[AgentName] = Field(min_length=1)
    matched_terms: dict[AgentName, list[str]] = Field(default_factory=dict)
    used_fallback: bool = False
    document_type_map: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phase 4: Smart Dispatch & Parallel Analysis — Output Contracts
# ---------------------------------------------------------------------------


class Severity(str, Enum):  # noqa: UP042 - consumed as string by downstream serializers.
    """M&A risk severity levels for specialist findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingDimension(str, Enum):  # noqa: UP042 - consumed as string by downstream serializers.
    """Top-level M&A due diligence workstream used to group findings."""

    LEGAL = "legal"
    FINANCIAL = "financial"
    PEOPLE = "people"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"


# ---------------------------------------------------------------------------
# Severity assignment
# ---------------------------------------------------------------------------

# Per clause-type confidence thresholds: (critical_min, high_min, medium_min).
# Confidence below medium_min maps to LOW.
_SEVERITY_THRESHOLDS: dict[ClauseType, tuple[float, float, float]] = {
    # Deal-stopper clauses — escalate at lower confidence.
    ClauseType.CHANGE_OF_CONTROL:         (0.75, 0.50, 0.30),
    ClauseType.IP_ASSIGNMENT:             (0.75, 0.50, 0.30),
    ClauseType.INDEMNIFICATION:           (0.80, 0.55, 0.35),
    ClauseType.LIABILITY_CAP:             (0.80, 0.55, 0.35),
    # Regulatory and data-risk clauses.
    ClauseType.DATA_PROTECTION:           (0.85, 0.60, 0.40),
    ClauseType.CYBER_SECURITY:            (0.85, 0.60, 0.40),
    ClauseType.GOVERNANCE_CLAUSE:         (0.85, 0.65, 0.45),
    ClauseType.RELATED_PARTY_TRANSACTION: (0.85, 0.65, 0.45),
    # Financial and operational clauses.
    ClauseType.TAX_PROVISION:             (0.90, 0.70, 0.50),
    ClauseType.FX_HEDGING:               (0.90, 0.70, 0.50),
    ClauseType.EMPLOYMENT_TERM:           (0.90, 0.70, 0.50),
    ClauseType.INSURANCE_POLICY:          (0.90, 0.70, 0.50),
    ClauseType.SUPPLIER_CONTRACT:         (0.90, 0.75, 0.55),
    ClauseType.CUSTOMER_CONTRACT:         (0.90, 0.75, 0.55),
    ClauseType.REPUTATION_RISK:           (0.90, 0.70, 0.50),
    ClauseType.ESG_OBLIGATION:            (0.90, 0.70, 0.50),
    # General — lowest baseline risk.
    ClauseType.GENERAL:                   (0.95, 0.80, 0.60),
}

# Claim keywords that can escalate severity above the confidence baseline.
_CRITICAL_ESCALATION_KEYWORDS: frozenset[str] = frozenset({
    "injunction", "void", "unenforceable", "prohibited", "blocked",
    "criminal", "fraud", "sanctions", "ofac", "seizure", "forfeiture",
})
_HIGH_ESCALATION_KEYWORDS: frozenset[str] = frozenset({
    "material breach", "termination", "significant loss", "irreparable",
    "default", "acceleration", "mandatory injunction", "no remedy",
})


def assign_severity(confidence: float, clause_type: ClauseType, claim: str) -> Severity:
    """Map evidence weight (confidence) and risk type (clause_type) to a severity level.

    Keyword escalation: presence of critical-risk terms in the claim raises
    severity by at most one tier above the confidence-based baseline.
    """
    critical_min, high_min, medium_min = _SEVERITY_THRESHOLDS.get(
        clause_type, (0.95, 0.80, 0.60)
    )

    if confidence >= critical_min:
        base = Severity.CRITICAL
    elif confidence >= high_min:
        base = Severity.HIGH
    elif confidence >= medium_min:
        base = Severity.MEDIUM
    else:
        base = Severity.LOW

    lower_claim = claim.lower()
    if any(kw in lower_claim for kw in _CRITICAL_ESCALATION_KEYWORDS):
        if base in (Severity.LOW, Severity.MEDIUM):
            base = Severity.HIGH
    elif any(kw in lower_claim for kw in _HIGH_ESCALATION_KEYWORDS):
        if base == Severity.LOW:
            base = Severity.MEDIUM

    return base


class Finding(BaseModel):
    """Structured finding produced by a specialist agent.

    Citation is mandatory — every finding must reference an exact quote
    from the source document for traceability (citation mandatory rule).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    citation_chunk_id: str = Field(min_length=1)
    source_agent: AgentName
    section_id: str = Field(min_length=1)
    absolute_page: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    dimension: FindingDimension = FindingDimension.LEGAL
    domain: str = ""
    severity: Severity = Severity.MEDIUM
    clause_type: ClauseType = ClauseType.GENERAL
    verified: bool = False
    cross_refs: list[str] = Field(default_factory=list)
    notes: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    relevant: bool = True


class AgentAnalysisResult(BaseModel):
    """Per-agent result from specialist analysis.

    Captures findings, chunk retrieval stats, and any non-fatal errors.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName
    findings: list[Finding] = Field(default_factory=list)
    chunks_retrieved: int = Field(default=0, ge=0)
    chunks_relevant: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    error: str | None = None


class DispatchResult(BaseModel):
    """Aggregated result from all specialist agents running in parallel."""

    model_config = ConfigDict(extra="forbid")

    results: list[AgentAnalysisResult] = Field(default_factory=list)
    total_findings: int = Field(default=0, ge=0)
    unique_findings: list[Finding] = Field(default_factory=list)
    agents_dispatched: int = Field(default=0, ge=0)
    agents_failed: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
