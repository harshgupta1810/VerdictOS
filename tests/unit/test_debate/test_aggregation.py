"""Unit tests for Phase 3 Findings Aggregation & Dimension Mapping."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest
from pydantic import ValidationError

from src.agents.schemas import AgentName, Confidence, Finding, FindingDimension, Severity
from src.common.models import ClauseType
from src.debate.aggregation import (
    CONFIDENCE_WEIGHTS,
    CORE_DEBATE_QUESTIONS,
    DIMENSION_MAP,
    PRIMARY_AGENT_TO_DIMENSION_MAP,
    DimensionActivationMode,
    evaluate_dimension_gate,
    map_findings_to_dimensions,
    merge_graphrag_links,
    normalize_confidences,
    validate_findings_pool,
)


def _make_finding(
    source_agent: AgentName,
    citation: str = "Standard quote.",
    chunk_id: str = "chunk-1",
    confidence: str | float = "medium",
    clause_type: ClauseType = ClauseType.GENERAL,
) -> Finding:
    """Helper to instantiate a valid Finding."""
    return Finding(
        id=str(uuid.uuid4()),
        claim="Identified risk flag",
        citation=citation,
        citation_chunk_id=chunk_id,
        source_agent=source_agent,
        section_id="Section 1",
        absolute_page=1,
        confidence=confidence,  # type: ignore[arg-type] - supports float coercion via our model_validator
        dimension=FindingDimension.RISK_EXPOSURE,
        domain="litigation",
        severity=Severity.HIGH,
        clause_type=clause_type,
    )


# ---------------------------------------------------------------------------
# Confidence Categorical & Float Coercion
# ---------------------------------------------------------------------------

def test_finding_coerces_float_confidence() -> None:
    f_high = _make_finding(AgentName.IP, confidence=0.85)
    f_med = _make_finding(AgentName.IP, confidence=0.55)
    f_spec = _make_finding(AgentName.IP, confidence=0.3)

    assert f_high.confidence == Confidence.HIGH
    assert f_med.confidence == Confidence.MEDIUM
    assert f_spec.confidence == Confidence.SPECULATIVE


def test_confidence_weight_lookup() -> None:
    assert CONFIDENCE_WEIGHTS[Confidence.HIGH] == 0.9
    assert CONFIDENCE_WEIGHTS[Confidence.MEDIUM] == 0.5
    assert CONFIDENCE_WEIGHTS[Confidence.SPECULATIVE] == 0.1


# ---------------------------------------------------------------------------
# Step 38: validate_findings_pool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_findings_pool_success() -> None:
    raw_list = [
        {
            "id": "f-1",
            "claim": "Claim 1",
            "citation": "Quote 1",
            "citation_chunk_id": "chunk-1",
            "source_agent": "ip_agent",
            "section_id": "Section 1",
            "absolute_page": 2,
            "confidence": 0.9,  # float will be coerced to "high"
            "dimension": "regulatory_approval",
            "severity": "high",
        },
        {
            "id": "f-2",
            "claim": "Claim 2",
            "citation": "Quote 2",
            "citation_chunk_id": "chunk-2",
            "source_agent": "tax_agent",
            "section_id": "Section 2",
            "absolute_page": 5,
            "confidence": "medium",  # string maps directly
            "dimension": "risk_exposure",
            "severity": "medium",
        },
    ]

    valid = await validate_findings_pool(raw_list, deal_id="deal-123")
    assert len(valid) == 2
    assert valid[0].id == "f-1"
    assert valid[1].id == "f-2"
    assert valid[0].confidence == Confidence.HIGH
    assert valid[1].confidence == Confidence.MEDIUM


@pytest.mark.asyncio
async def test_validate_findings_pool_rejects_malformed_and_logs() -> None:
    raw_list = [
        {
            "id": "f-1",
            "claim": "Claim 1",
            "citation": "Quote 1",
            "citation_chunk_id": "chunk-1",
            "source_agent": "ip_agent",
            "section_id": "Section 1",
            "absolute_page": 2,
            "confidence": 0.9,
        },
        {
            "claim": "Claim 2",
            "citation": "Quote 2",
            "citation_chunk_id": "chunk-2",
            "source_agent": "tax_agent",
        },
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    valid = await validate_findings_pool(raw_list, deal_id="deal-123", db_session=mock_session)

    # Only 1 valid finding survives
    assert len(valid) == 1
    assert valid[0].id == "f-1"

    # Verify db logging occurred
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    added_record = mock_session.add.call_args[0][0]
    assert added_record.deal_id == "deal-123"
    assert added_record.event_type == "finding_validation_failure"


# ---------------------------------------------------------------------------
# Step 39: normalize_confidences
# ---------------------------------------------------------------------------

def test_normalize_confidences_verifies_categorical() -> None:
    findings = [
        _make_finding(AgentName.IP, confidence="high"),
        _make_finding(AgentName.TAX, confidence="medium"),
    ]
    normalized = normalize_confidences(findings)
    assert normalized[0].confidence == Confidence.HIGH
    assert normalized[1].confidence == Confidence.MEDIUM


# ---------------------------------------------------------------------------
# Step 40: merge_graphrag_links
# ---------------------------------------------------------------------------

def test_merge_graphrag_links_by_shared_entity() -> None:
    f1 = _make_finding(AgentName.IP, chunk_id="c-1")
    f2 = _make_finding(AgentName.TAX, chunk_id="c-2")
    findings = [f1, f2]

    graph = nx.DiGraph()
    graph.add_node(
        "entity-abc",
        node_type="entity",
        canonical_name="Acme Corp",
        provenance=[
            {"chunk_id": "c-1", "document_name": "ip.pdf"},
            {"chunk_id": "c-2", "document_name": "tax.pdf"},
        ]
    )

    merged = merge_graphrag_links(findings, graph)
    assert f2.id in merged[0].cross_refs
    assert f1.id in merged[1].cross_refs


def test_merge_graphrag_links_by_entity_edge() -> None:
    f1 = _make_finding(AgentName.IP, chunk_id="c-1")
    f2 = _make_finding(AgentName.TAX, chunk_id="c-2")
    findings = [f1, f2]

    graph = nx.DiGraph()
    graph.add_node(
        "entity-1",
        node_type="entity",
        canonical_name="Entity One",
        provenance=[{"chunk_id": "c-1", "document_name": "ip.pdf"}]
    )
    graph.add_node(
        "entity-2",
        node_type="entity",
        canonical_name="Entity Two",
        provenance=[{"chunk_id": "c-2", "document_name": "tax.pdf"}]
    )
    graph.add_edge("entity-1", "entity-2")

    merged = merge_graphrag_links(findings, graph)
    assert f2.id in merged[0].cross_refs
    assert f1.id in merged[1].cross_refs


# ---------------------------------------------------------------------------
# Step 42: map_findings_to_dimensions (Two-Key Compound Mapping)
# ---------------------------------------------------------------------------

def test_map_findings_to_dimensions_compound() -> None:
    # 1. Finance with tax_provision maps to RISK_EXPOSURE
    f_fin_tax = _make_finding(AgentName.FINANCE, clause_type=ClauseType.TAX_PROVISION)
    # 2. Finance with liability_cap maps to VALUATION_FAIRNESS
    f_fin_cap = _make_finding(AgentName.FINANCE, clause_type=ClauseType.LIABILITY_CAP)
    # 3. Finance general maps to SYNERGY_VALIDITY
    f_fin_gen = _make_finding(AgentName.FINANCE, clause_type=ClauseType.GENERAL)

    # 4. Customer with change_of_control maps to EXIT_SCENARIO
    f_cust_exit = _make_finding(AgentName.CUSTOMER, clause_type=ClauseType.CHANGE_OF_CONTROL)
    # 5. Customer general maps to MARKET_TIMING
    f_cust_gen = _make_finding(AgentName.CUSTOMER, clause_type=ClauseType.GENERAL)

    # 6. Litigation general maps to RISK_EXPOSURE
    f_lit_gen = _make_finding(AgentName.LITIGATION, clause_type=ClauseType.GENERAL)
    # 7. Litigation indemnification maps to RISK_EXPOSURE
    f_lit_indem = _make_finding(AgentName.LITIGATION, clause_type=ClauseType.INDEMNIFICATION)

    # 8. Cyber general maps to INTEGRATION_COMPLEXITY (Option A default/fallback)
    f_cyb_gen = _make_finding(AgentName.CYBER, clause_type=ClauseType.GENERAL)
    # 9. Cyber data_protection maps to INTEGRATION_COMPLEXITY (Option A data security)
    f_cyb_prot = _make_finding(AgentName.CYBER, clause_type=ClauseType.DATA_PROTECTION)

    findings = [
        f_fin_tax, f_fin_cap, f_fin_gen, f_cust_exit, f_cust_gen,
        f_lit_gen, f_lit_indem, f_cyb_gen, f_cyb_prot
    ]

    mapped = map_findings_to_dimensions(findings)

    assert f_fin_tax.dimension == FindingDimension.RISK_EXPOSURE
    assert f_fin_cap.dimension == FindingDimension.VALUATION_FAIRNESS
    assert f_fin_gen.dimension == FindingDimension.SYNERGY_VALIDITY

    assert f_cust_exit.dimension == FindingDimension.EXIT_SCENARIO
    assert f_cust_gen.dimension == FindingDimension.MARKET_TIMING

    assert f_lit_gen.dimension == FindingDimension.RISK_EXPOSURE
    assert f_lit_indem.dimension == FindingDimension.RISK_EXPOSURE

    assert f_cyb_gen.dimension == FindingDimension.INTEGRATION_COMPLEXITY
    assert f_cyb_prot.dimension == FindingDimension.INTEGRATION_COMPLEXITY


# ---------------------------------------------------------------------------
# Step 41: evaluate_dimension_gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_dimension_gate_full() -> None:
    mapped = {
        FindingDimension.RISK_EXPOSURE: [
            _make_finding(AgentName.LITIGATION),
            _make_finding(AgentName.TAX),
            _make_finding(AgentName.INSURANCE),
        ]
    }
    
    gates = await evaluate_dimension_gate(mapped, deal_id="deal-1")
    gate = gates[FindingDimension.RISK_EXPOSURE]
    
    assert gate.mode == DimensionActivationMode.FULL
    assert gate.findings_count == 3
    assert gate.max_rounds == 3
    assert len(gate.active_personas) == 6
    assert "Regulator's Eye" in gate.active_personas
    assert gate.core_question == CORE_DEBATE_QUESTIONS[FindingDimension.RISK_EXPOSURE]


@pytest.mark.asyncio
async def test_evaluate_dimension_gate_limited() -> None:
    mapped = {
        FindingDimension.VALUATION_FAIRNESS: [
            _make_finding(AgentName.FINANCE),
            _make_finding(AgentName.RELATED_PARTY),
        ]
    }
    
    gates = await evaluate_dimension_gate(mapped, deal_id="deal-1")
    gate = gates[FindingDimension.VALUATION_FAIRNESS]
    
    assert gate.mode == DimensionActivationMode.LIMITED
    assert gate.findings_count == 2
    assert gate.max_rounds == 1
    assert gate.active_personas == ["Proponent", "Critic", "Devil's Advocate"]
    assert gate.core_question == CORE_DEBATE_QUESTIONS[FindingDimension.VALUATION_FAIRNESS]


@pytest.mark.asyncio
async def test_evaluate_dimension_gate_skipped_and_writes_gap() -> None:
    mapped = {}
    
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    gates = await evaluate_dimension_gate(mapped, deal_id="deal-1", db_session=mock_session)
    gate = gates[FindingDimension.EXIT_SCENARIO]
    
    assert gate.mode == DimensionActivationMode.SKIPPED
    assert gate.findings_count == 0
    assert gate.max_rounds == 0
    assert gate.active_personas == []

    # Since all 8 dimensions are empty, it will call add 8 times (one for each skipped dimension)
    assert mock_session.add.call_count == 8
    mock_session.commit.assert_called()
    
    added_descriptions = [call[0][0].description for call in mock_session.add.call_args_list]
    assert any("exit_scenario" in desc for desc in added_descriptions)
