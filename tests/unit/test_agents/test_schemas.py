"""Tests for Finding, AgentAnalysisResult, and DispatchResult output schemas."""

from typing import Any
import pytest
from pydantic import ValidationError

from src.agents.schemas import (
    AgentAnalysisResult,
    AgentName,
    DispatchResult,
    Finding,
    FindingDimension,
    Severity,
    assign_severity,
)
from src.common.models import ClauseType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_finding(**overrides: Any) -> dict[str, Any]:
    """Return a valid Finding dict with optional overrides."""
    base: dict[str, Any] = {
        "id": "f-001",
        "claim": "Patent assignment clause found",
        "citation": "All intellectual property rights shall be assigned.",
        "citation_chunk_id": "doc1:chunk:42",
        "source_agent": AgentName.IP,
        "section_id": "Section 4.2",
        "absolute_page": 12,
        "confidence": 0.85,
        "dimension": FindingDimension.RISK_EXPOSURE,
        "domain": "intellectual_property",
        "severity": Severity.CRITICAL,
        "clause_type": ClauseType.IP_ASSIGNMENT,
        "verified": False,
        "cross_refs": [],
        "notes": "",
        "relevant": True,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Finding tests
# ---------------------------------------------------------------------------


class TestFinding:
    """Finding Pydantic V2 validation."""

    def test_valid_finding(self) -> None:
        f = Finding(**_valid_finding())
        assert f.id == "f-001"
        assert f.claim == "Patent assignment clause found"
        assert f.citation == "All intellectual property rights shall be assigned."
        assert f.source_agent == AgentName.IP
        assert f.confidence == 0.85

    def test_citation_mandatory_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="citation"):
            Finding(**_valid_finding(citation=""))

    def test_claim_mandatory_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="claim"):
            Finding(**_valid_finding(claim=""))

    def test_id_mandatory_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="id"):
            Finding(**_valid_finding(id=""))

    def test_confidence_bounds(self) -> None:
        Finding(**_valid_finding(confidence=0.0))
        Finding(**_valid_finding(confidence=1.0))
        with pytest.raises(ValidationError):
            Finding(**_valid_finding(confidence=-0.1))
        with pytest.raises(ValidationError):
            Finding(**_valid_finding(confidence=1.1))

    def test_absolute_page_non_negative(self) -> None:
        Finding(**_valid_finding(absolute_page=0))
        with pytest.raises(ValidationError):
            Finding(**_valid_finding(absolute_page=-1))

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Finding(**_valid_finding(extra_field="bad"))

    def test_default_clause_type_is_general(self) -> None:
        data = _valid_finding()
        del data["clause_type"]
        f = Finding(**data)
        assert f.clause_type == ClauseType.GENERAL

    def test_default_relevant_is_true(self) -> None:
        data = _valid_finding()
        del data["relevant"]
        f = Finding(**data)
        assert f.relevant is True

    # New-field defaults

    def test_default_verified_is_false(self) -> None:
        data = _valid_finding()
        del data["verified"]
        f = Finding(**data)
        assert f.verified is False

    def test_default_cross_refs_is_empty_list(self) -> None:
        data = _valid_finding()
        del data["cross_refs"]
        f = Finding(**data)
        assert f.cross_refs == []

    def test_default_notes_is_empty_string(self) -> None:
        data = _valid_finding()
        del data["notes"]
        f = Finding(**data)
        assert f.notes == ""

    def test_timestamp_auto_populated(self) -> None:
        f = Finding(**_valid_finding())
        assert f.timestamp is not None
        assert f.timestamp.tzinfo is not None

    def test_severity_field(self) -> None:
        f = Finding(**_valid_finding(severity=Severity.HIGH))
        assert f.severity == Severity.HIGH

    def test_dimension_field(self) -> None:
        f = Finding(**_valid_finding(dimension=FindingDimension.VALUATION_FAIRNESS))
        assert f.dimension == FindingDimension.VALUATION_FAIRNESS

    def test_domain_field(self) -> None:
        f = Finding(**_valid_finding(domain="litigation"))
        assert f.domain == "litigation"

    def test_cross_refs_stored(self) -> None:
        f = Finding(**_valid_finding(cross_refs=["governance_agent", "cyber_agent"]))
        assert f.cross_refs == ["governance_agent", "cyber_agent"]


# ---------------------------------------------------------------------------
# assign_severity tests
# ---------------------------------------------------------------------------


class TestAssignSeverity:
    """Severity assignment logic: confidence thresholds + keyword escalation."""

    def test_high_confidence_ip_assignment_is_critical(self) -> None:
        s = assign_severity(0.85, ClauseType.IP_ASSIGNMENT, "Missing IP assignment clause")
        assert s == Severity.CRITICAL

    def test_medium_confidence_ip_assignment_is_high(self) -> None:
        s = assign_severity(0.55, ClauseType.IP_ASSIGNMENT, "IP assignment gap found")
        assert s == Severity.HIGH

    def test_low_confidence_general_is_low(self) -> None:
        s = assign_severity(0.3, ClauseType.GENERAL, "Some clause text")
        assert s == Severity.LOW

    def test_high_confidence_general_is_critical(self) -> None:
        s = assign_severity(0.96, ClauseType.GENERAL, "Some clause text")
        assert s == Severity.CRITICAL

    def test_critical_keyword_escalates_low_to_high(self) -> None:
        s = assign_severity(0.3, ClauseType.GENERAL, "This clause is void and unenforceable")
        assert s == Severity.HIGH

    def test_critical_keyword_escalates_medium_to_high(self) -> None:
        s = assign_severity(0.65, ClauseType.GENERAL, "The injunction prevents assignment")
        assert s == Severity.HIGH

    def test_critical_keyword_does_not_lower_critical(self) -> None:
        s = assign_severity(0.96, ClauseType.GENERAL, "void clause detected")
        assert s == Severity.CRITICAL

    def test_high_keyword_escalates_low_to_medium(self) -> None:
        s = assign_severity(0.1, ClauseType.GENERAL, "possible material breach scenario")
        assert s == Severity.MEDIUM

    def test_change_of_control_low_confidence_is_medium(self) -> None:
        s = assign_severity(0.35, ClauseType.CHANGE_OF_CONTROL, "Change of control trigger")
        assert s == Severity.MEDIUM

    def test_change_of_control_very_low_confidence_is_low(self) -> None:
        s = assign_severity(0.20, ClauseType.CHANGE_OF_CONTROL, "Change of control trigger")
        assert s == Severity.LOW


# ---------------------------------------------------------------------------
# AgentAnalysisResult tests
# ---------------------------------------------------------------------------


class TestAgentAnalysisResult:
    """AgentAnalysisResult validation."""

    def test_valid_result_with_findings(self) -> None:
        finding = Finding(**_valid_finding())
        result = AgentAnalysisResult(
            agent_name=AgentName.IP,
            findings=[finding],
            chunks_retrieved=10,
            chunks_relevant=3,
            duration_ms=1200,
        )
        assert result.agent_name == AgentName.IP
        assert len(result.findings) == 1
        assert result.chunks_retrieved == 10
        assert result.chunks_relevant == 3

    def test_empty_findings_allowed(self) -> None:
        result = AgentAnalysisResult(agent_name=AgentName.TAX)
        assert result.findings == []
        assert result.error is None

    def test_error_field_captures_non_fatal(self) -> None:
        result = AgentAnalysisResult(
            agent_name=AgentName.LITIGATION,
            error="LLM timeout after 120s",
        )
        assert result.error == "LLM timeout after 120s"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AgentAnalysisResult(agent_name=AgentName.IP, bogus="data")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DispatchResult tests
# ---------------------------------------------------------------------------


class TestDispatchResult:
    """DispatchResult validation."""

    def test_valid_dispatch_result(self) -> None:
        agent_result = AgentAnalysisResult(
            agent_name=AgentName.FINANCE,
            findings=[Finding(**_valid_finding(source_agent=AgentName.FINANCE))],
            chunks_retrieved=20,
            chunks_relevant=5,
            duration_ms=3000,
        )
        dispatch = DispatchResult(
            results=[agent_result],
            total_findings=1,
            agents_dispatched=1,
            agents_failed=0,
            duration_ms=3200,
        )
        assert dispatch.total_findings == 1
        assert dispatch.agents_dispatched == 1
        assert dispatch.agents_failed == 0

    def test_empty_dispatch_result(self) -> None:
        dispatch = DispatchResult()
        assert dispatch.results == []
        assert dispatch.total_findings == 0
        assert dispatch.agents_dispatched == 0
        assert dispatch.unique_findings == []

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DispatchResult(extra="data")  # type: ignore[call-arg]
