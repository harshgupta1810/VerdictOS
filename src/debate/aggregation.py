"""Findings Aggregation & Dimension Mapping Engine (Phase 3).

Implements the post-analysis findings processing pipeline:
1. Pydantic v2 findings pool validation and audit log storage of failures.
2. Categorical confidence mapping to numeric weights for Judge consumption.
3. GraphRAG cross-document entity connection and section-link merging.
4. Two-key strategic mapping matrix (AgentName + ClauseType -> FindingDimension).
5. Dimension threshold gating (Full, Limited, Skipped modes with gap reports).
"""

from __future__ import annotations

import logging
from enum import Enum
import networkx as nx
from pydantic import BaseModel, ConfigDict, Field

from src.agents.schemas import AgentName, Confidence, Finding, FindingDimension
from src.common.models import ClauseType
from src.db.models import AuditRecord

# Type checking import for SQLAlchemy session
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Categorical Confidence Weights (Downstream Judge Weighting)
# ---------------------------------------------------------------------------

CONFIDENCE_WEIGHTS: dict[Confidence, float] = {
    Confidence.HIGH:        0.9,
    Confidence.MEDIUM:      0.5,
    Confidence.SPECULATIVE: 0.1,
}

# ---------------------------------------------------------------------------
# Two-Key Mapping Matrix (AgentName, ClauseType) -> FindingDimension
# ---------------------------------------------------------------------------

DIMENSION_MAP: dict[tuple[AgentName, ClauseType], FindingDimension] = {
    # Finance agent mappings (valuation, synergies, exits, pricing timing, legal risks)
    (AgentName.FINANCE, ClauseType.TAX_PROVISION): FindingDimension.RISK_EXPOSURE,
    (AgentName.FINANCE, ClauseType.LIABILITY_CAP): FindingDimension.VALUATION_FAIRNESS,
    (AgentName.FINANCE, ClauseType.FX_HEDGING): FindingDimension.VALUATION_FAIRNESS,
    (AgentName.FINANCE, ClauseType.CHANGE_OF_CONTROL): FindingDimension.EXIT_SCENARIO,
    (AgentName.FINANCE, ClauseType.GENERAL): FindingDimension.SYNERGY_VALIDITY,
    
    # Tax agent mappings (liabilities, unwinding, and fairness)
    (AgentName.TAX, ClauseType.TAX_PROVISION): FindingDimension.RISK_EXPOSURE,
    (AgentName.TAX, ClauseType.CHANGE_OF_CONTROL): FindingDimension.EXIT_SCENARIO,
    (AgentName.TAX, ClauseType.GENERAL): FindingDimension.VALUATION_FAIRNESS,
    
    # HR agent mappings (integration risks, headcount/org synergies)
    (AgentName.HR, ClauseType.EMPLOYMENT_TERM): FindingDimension.INTEGRATION_COMPLEXITY,
    (AgentName.HR, ClauseType.GENERAL): FindingDimension.SYNERGY_VALIDITY,
    
    # Cyber agent mappings (Option A: uses valid data_protection from taxonomy)
    (AgentName.CYBER, ClauseType.DATA_PROTECTION): FindingDimension.INTEGRATION_COMPLEXITY,
    (AgentName.CYBER, ClauseType.GENERAL): FindingDimension.INTEGRATION_COMPLEXITY,
    
    # Governance agent mappings (Option A: uses change_of_control from taxonomy)
    (AgentName.GOVERNANCE, ClauseType.CHANGE_OF_CONTROL): FindingDimension.EXIT_SCENARIO,
    (AgentName.GOVERNANCE, ClauseType.GENERAL): FindingDimension.INTEGRATION_COMPLEXITY,
    
    # Regulatory agent mappings (material risk close vs. regulatory delays)
    (AgentName.REGULATORY, ClauseType.CHANGE_OF_CONTROL): FindingDimension.RISK_EXPOSURE,
    (AgentName.REGULATORY, ClauseType.GENERAL): FindingDimension.REGULATORY_APPROVAL,

    # Litigation agent mappings (Issue 3: Litigation default is Risk Exposure)
    (AgentName.LITIGATION, ClauseType.INDEMNIFICATION): FindingDimension.RISK_EXPOSURE,
    (AgentName.LITIGATION, ClauseType.GENERAL): FindingDimension.RISK_EXPOSURE,
    
    # Assets agent mappings (close triggers vs operational complexities)
    (AgentName.ASSETS, ClauseType.CHANGE_OF_CONTROL): FindingDimension.EXIT_SCENARIO,
    (AgentName.ASSETS, ClauseType.GENERAL): FindingDimension.INTEGRATION_COMPLEXITY,

    # Customer agent mappings (Issue 2: exit liabilities vs. customer cycle timing)
    (AgentName.CUSTOMER, ClauseType.CHANGE_OF_CONTROL): FindingDimension.EXIT_SCENARIO,
    (AgentName.CUSTOMER, ClauseType.GENERAL): FindingDimension.MARKET_TIMING,
}

PRIMARY_AGENT_TO_DIMENSION_MAP: dict[AgentName, FindingDimension] = {
    AgentName.IP:            FindingDimension.REGULATORY_APPROVAL,
    AgentName.LITIGATION:    FindingDimension.RISK_EXPOSURE,
    AgentName.REGULATORY:    FindingDimension.REGULATORY_APPROVAL,
    AgentName.PRIVACY:       FindingDimension.REGULATORY_APPROVAL,
    AgentName.FINANCE:       FindingDimension.VALUATION_FAIRNESS,
    AgentName.TAX:           FindingDimension.RISK_EXPOSURE,
    AgentName.INSURANCE:     FindingDimension.RISK_EXPOSURE,
    AgentName.HR:            FindingDimension.INTEGRATION_COMPLEXITY,
    AgentName.GOVERNANCE:    FindingDimension.INTEGRATION_COMPLEXITY,
    AgentName.RELATED_PARTY: FindingDimension.VALUATION_FAIRNESS,
    AgentName.CYBER:         FindingDimension.INTEGRATION_COMPLEXITY,
    AgentName.ASSETS:        FindingDimension.EXIT_SCENARIO,
    AgentName.SUPPLIER:      FindingDimension.SYNERGY_VALIDITY,
    AgentName.CUSTOMER:      FindingDimension.MARKET_TIMING,
    AgentName.REPUTATION:    FindingDimension.STRATEGIC_FIT,
    AgentName.ESG:           FindingDimension.STRATEGIC_FIT,
}

CORE_DEBATE_QUESTIONS: dict[FindingDimension, str] = {
    FindingDimension.RISK_EXPOSURE: (
        "How severe and likely are identified risks? Are they already priced into the deal valuation?"
    ),
    FindingDimension.VALUATION_FAIRNESS: (
        "Is the asking price justified by the underlying data, or inflated by seller narrative and projections?"
    ),
    FindingDimension.STRATEGIC_FIT: (
        "Does this acquisition genuinely serve the buyer's stated long-term strategic objectives?"
    ),
    FindingDimension.SYNERGY_VALIDITY: (
        "Are the claimed cost savings and revenue synergies achievable given the verified operational data?"
    ),
    FindingDimension.INTEGRATION_COMPLEXITY: (
        "How difficult will it realistically be to merge teams, systems, processes, and culture post-close?"
    ),
    FindingDimension.MARKET_TIMING: (
        "Is now the right moment to close, or would waiting 12 months materially change the risk-reward calculation?"
    ),
    FindingDimension.REGULATORY_APPROVAL: (
        "Will antitrust authorities or sector regulators block, condition, or materially delay this transaction?"
    ),
    FindingDimension.EXIT_SCENARIO: (
        "If this deal fails to deliver expected value, what does unwinding look like and what is the exit cost?"
    ),
}

# ---------------------------------------------------------------------------
# Gating Contracts
# ---------------------------------------------------------------------------

class DimensionActivationMode(str, Enum):
    FULL = "full"
    LIMITED = "limited"
    SKIPPED = "skipped"


class DimensionGateState(BaseModel):
    """Pydantic V2 contract representing a dimension's debate gating status."""

    model_config = ConfigDict(extra="forbid")

    dimension: FindingDimension
    mode: DimensionActivationMode
    findings_count: int
    active_personas: list[str] = Field(default_factory=list)
    max_rounds: int = 0
    core_question: str = ""


# ---------------------------------------------------------------------------
# Phase 3 Core Implementations
# ---------------------------------------------------------------------------

async def validate_findings_pool(
    raw_findings: list[dict],
    deal_id: str,
    db_session: AsyncSession | None = None,
) -> list[Finding]:
    """Step 38: Pydantic v2 findings pool validator.

    Schema-validates each finding, rejects malformed outputs, and logs validation
    failures to the audit database store as a finding_validation_failure.
    """
    valid_findings: list[Finding] = []

    for raw in raw_findings:
        try:
            finding = Finding.model_validate(raw)
            valid_findings.append(finding)
        except Exception as exc:
            err_msg = f"Finding schema validation failure in deal {deal_id}: {exc}"
            logger.error(err_msg)
            
            if db_session is not None:
                try:
                    audit_rec = AuditRecord(
                        deal_id=deal_id,
                        event_type="finding_validation_failure",
                        actor="findings_aggregator",
                        description=err_msg,
                        raw_payload=raw,
                    )
                    db_session.add(audit_rec)
                    await db_session.commit()
                except Exception as db_err:
                    logger.error(f"Failed to persist validation failure to audit store: {db_err}")

    return valid_findings


def normalize_confidences(findings: list[Finding]) -> list[Finding]:
    """Step 39: Confidence normalization wrapper.

    Ensures every finding carries a valid categorical Confidence. Downgrades or weight-mapping
    is handled downstream at Gate D and judge level (using CONFIDENCE_WEIGHTS).
    """
    for f in findings:
        # Pydantic validation handles float-to-categorical coercion; here we verify.
        if not isinstance(f.confidence, Confidence):
            # Fallback to default if somehow not coerced
            f.confidence = Confidence.MEDIUM
    return findings


def merge_graphrag_links(findings: list[Finding], graph: nx.DiGraph) -> list[Finding]:
    """Step 40: GraphRAG cross-document compound risk link merger.

    Uses NetworkX entity graph to identify cross-document risk connections.
    Links findings if their citation chunks share entity nodes or co-occurrence/reference edges.
    """
    if not findings or graph is None or len(graph) == 0:
        return findings

    # Map entity nodes in the graph to the chunk_ids present in their provenance list
    chunk_to_nodes: dict[str, set[str]] = {}
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == "entity":
            for prov in data.get("provenance", []):
                chunk_id = prov.get("chunk_id")
                if chunk_id:
                    chunk_to_nodes.setdefault(chunk_id, set()).add(node_id)

    # Pairwise comparison and merging
    for i in range(len(findings)):
        for j in range(i + 1, len(findings)):
            f1 = findings[i]
            f2 = findings[j]
            
            nodes1 = chunk_to_nodes.get(f1.citation_chunk_id, set())
            nodes2 = chunk_to_nodes.get(f2.citation_chunk_id, set())
            
            linked = False
            if nodes1 & nodes2:
                # 1. Share a common entity (direct node intersection)
                linked = True
            else:
                # 2. Check for direct edges between their entities in the graph
                for n1 in nodes1:
                    for n2 in nodes2:
                        if graph.has_edge(n1, n2) or graph.has_edge(n2, n1):
                            linked = True
                            break
                    if linked:
                        break

            if linked:
                if f2.id not in f1.cross_refs:
                    f1.cross_refs.append(f2.id)
                if f1.id not in f2.cross_refs:
                    f2.cross_refs.append(f1.id)

    return findings


def map_findings_to_dimensions(findings: list[Finding]) -> dict[FindingDimension, list[Finding]]:
    """Step 42 (Part A): Findings-to-dimension mapper.

    Assigns each finding to one of the 8 debate dimensions based on the compound two-key
    lookup DIMENSION_MAP (AgentName, ClauseType), with fallback to PRIMARY_AGENT_TO_DIMENSION_MAP.
    Updates the dimension in-place.
    """
    mapped: dict[FindingDimension, list[Finding]] = {dim: [] for dim in FindingDimension}

    for finding in findings:
        lookup_key = (finding.source_agent, finding.clause_type)
        target_dim = DIMENSION_MAP.get(lookup_key)
        
        if not target_dim:
            # Fallback to the agent's primary default dimension
            target_dim = PRIMARY_AGENT_TO_DIMENSION_MAP.get(finding.source_agent)

        if target_dim:
            finding.dimension = target_dim
            mapped[target_dim].append(finding)
        else:
            # Fallback to the finding's default schema-defined dimension
            mapped[finding.dimension].append(finding)

    return mapped


async def evaluate_dimension_gate(
    mapped_findings: dict[FindingDimension, list[Finding]],
    deal_id: str,
    db_session: AsyncSession | None = None,
) -> dict[FindingDimension, DimensionGateState]:
    """Step 41 & 42 (Part B): Dimension threshold gate.

    Gates debate loops based on the volume of evidence to prevent speculative debate:
    - 3+ findings: Full activation (6 personas, 3 rounds)
    - 1-2 findings: Limited mode (3 personas: Proponent, Critic, Devil's Advocate; 1 round)
    - 0 findings: Skipped (debate skipped, logs evidence gap record to audit store)
    """
    activation_map: dict[FindingDimension, DimensionGateState] = {}

    for dim in FindingDimension:
        findings = mapped_findings.get(dim, [])
        count = len(findings)
        core_q = CORE_DEBATE_QUESTIONS.get(dim, "")

        if count >= 3:
            state = DimensionGateState(
                dimension=dim,
                mode=DimensionActivationMode.FULL,
                findings_count=count,
                active_personas=[
                    "Proponent", "Critic", "Devil's Advocate", 
                    "Valuation Skeptic", "Integration Realist", "Regulator's Eye"
                ],
                max_rounds=3,
                core_question=core_q,
            )
        elif count >= 1:
            state = DimensionGateState(
                dimension=dim,
                mode=DimensionActivationMode.LIMITED,
                findings_count=count,
                active_personas=["Proponent", "Critic", "Devil's Advocate"],
                max_rounds=1,
                core_question=core_q,
            )
        else:
            state = DimensionGateState(
                dimension=dim,
                mode=DimensionActivationMode.SKIPPED,
                findings_count=0,
                active_personas=[],
                max_rounds=0,
                core_question=core_q,
            )

            # Log evidence gap record to audit table
            gap_description = f"Dimension '{dim.value}' skipped due to insufficient evidence (0 findings)."
            logger.info(gap_description)
            
            if db_session is not None:
                try:
                    gap_rec = AuditRecord(
                        deal_id=deal_id,
                        event_type="evidence_gap_record",
                        actor="dimension_gate",
                        description=gap_description,
                        raw_payload={"dimension": dim.value, "findings_count": 0},
                    )
                    db_session.add(gap_rec)
                    await db_session.commit()
                except Exception as db_err:
                    logger.error(f"Failed to persist evidence gap record: {db_err}")

        activation_map[dim] = state

    return activation_map
