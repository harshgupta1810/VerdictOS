"""Tests for ParallelDispatcher and run_parallel_analysis."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base_agent import RelevanceCheckResult, _AnalysisOutput, _RawFinding
from src.agents.dispatcher import ParallelDispatcher, deduplicate_findings, run_parallel_analysis
from src.agents.planner_agent import SPECIALIST_REGISTRY
from src.agents.schemas import (
    ActiveSpecialistManifest,
    AgentAnalysisResult,
    AgentName,
    DispatchResult,
    Finding,
    FindingDimension,
    Severity,
)
from src.agents.specialist_agent import SpecialistAgent
from src.common.exceptions import LLMClientError
from src.common.models import ClauseType
from src.search.schemas import SearchResult


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _mock_search_result(text: str = "Sample clause text.") -> SearchResult:
    return SearchResult(
        chunk_id="doc1:chunk:1",
        score=5.0,
        document_name="agreement.pdf",
        text=text,
        section_id="Section 1",
        absolute_page=0,
        clause_type=ClauseType.GENERAL,
        references_sections=[],
        highlights=[],
    )


def _make_agent(
    agent_name: AgentName,
    findings_count: int = 1,
    error: str | None = None,
) -> SpecialistAgent:
    """Create a SpecialistAgent with mocked internals.

    Citations are unique per agent so findings from different agents
    are not deduplicated in tests that check raw total_findings counts.
    """
    defn = next(d for d in SPECIALIST_REGISTRY if d.agent_name == agent_name)
    mock_search = MagicMock()

    if error:
        mock_search.search = MagicMock(return_value=[_mock_search_result()])
        mock_llm = AsyncMock()
        mock_llm.default_model = "llama3"
        mock_llm.generate_with_schema = AsyncMock(
            side_effect=LLMClientError(error),
        )
    elif findings_count > 0:
        mock_search.search = MagicMock(return_value=[_mock_search_result()])
        mock_llm = AsyncMock()
        mock_llm.default_model = "llama3"
        findings = [
            _RawFinding(
                claim=f"Finding {i}",
                citation=f"Quote from {agent_name.value} finding {i}.",
                confidence=0.8,
            )
            for i in range(findings_count)
        ]
        mock_llm.generate_with_schema = AsyncMock(
            side_effect=[
                RelevanceCheckResult(relevant=True, reason="matches"),
                _AnalysisOutput(findings=findings),
            ],
        )
    else:
        mock_search.search = MagicMock(return_value=[])
        mock_llm = AsyncMock()
        mock_llm.default_model = "llama3"

    return SpecialistAgent(defn, mock_search, mock_llm)


def _make_finding(
    source_agent: AgentName,
    citation: str,
    section_id: str = "Section 1",
    confidence: float = 0.8,
) -> Finding:
    return Finding(
        id=str(uuid.uuid4()),
        claim="Test claim",
        citation=citation,
        citation_chunk_id="chunk-1",
        source_agent=source_agent,
        section_id=section_id,
        absolute_page=0,
        confidence=confidence,
        dimension=FindingDimension.LEGAL,
        domain="intellectual_property",
        severity=Severity.HIGH,
        clause_type=ClauseType.IP_ASSIGNMENT,
    )


# ---------------------------------------------------------------------------
# ParallelDispatcher tests
# ---------------------------------------------------------------------------


class TestParallelDispatcher:
    """Test parallel dispatch execution."""

    @pytest.mark.asyncio
    async def test_dispatches_all_agents(self) -> None:
        agents = [
            _make_agent(AgentName.IP, findings_count=1),
            _make_agent(AgentName.TAX, findings_count=2),
        ]
        dispatcher = ParallelDispatcher(agents)
        result = await dispatcher.dispatch()

        assert isinstance(result, DispatchResult)
        assert result.agents_dispatched == 2
        assert result.total_findings == 3  # 1 + 2
        assert result.agents_failed == 0
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_individual_agent_failure_does_not_crash_dispatch(self) -> None:
        agents = [
            _make_agent(AgentName.IP, findings_count=1),
            _make_agent(AgentName.LITIGATION, error="LLM timeout"),
        ]
        dispatcher = ParallelDispatcher(agents)
        result = await dispatcher.dispatch()

        assert result.agents_dispatched == 2
        assert result.agents_failed == 0  # Error captured at chunk level, not agent level
        assert result.total_findings == 1  # IP found 1, Litigation had error

    @pytest.mark.asyncio
    async def test_empty_agents_list(self) -> None:
        dispatcher = ParallelDispatcher([])
        result = await dispatcher.dispatch()

        assert result.agents_dispatched == 0
        assert result.total_findings == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_no_search_results_produces_empty_findings(self) -> None:
        agents = [_make_agent(AgentName.ESG, findings_count=0)]
        dispatcher = ParallelDispatcher(agents)
        result = await dispatcher.dispatch()

        assert result.agents_dispatched == 1
        assert result.total_findings == 0
        assert result.agents_failed == 0

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self) -> None:
        """Verify semaphore throttles concurrent execution."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        original_analyze = SpecialistAgent.analyze

        async def _tracked_analyze(self, document_name=None):  # type: ignore[no-untyped-def]
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)  # Simulate work
            async with lock:
                current_concurrent -= 1
            return await original_analyze(self, document_name)

        # Create 4 agents, limit concurrency to 2
        agents = [_make_agent(AgentName.IP, findings_count=0) for _ in range(4)]
        dispatcher = ParallelDispatcher(agents, max_concurrency=2)

        # Patch analyze on each agent
        for agent in agents:
            agent.analyze = lambda self=agent, dn=None: _tracked_analyze(self, dn)  # type: ignore[method-assign]

        await dispatcher.dispatch()
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_document_name_passed_to_agents(self) -> None:
        agent = _make_agent(AgentName.IP, findings_count=0)
        agent.analyze = AsyncMock(  # type: ignore[method-assign]
            return_value=AgentAnalysisResult(
                agent_name=AgentName.IP,
                findings=[],
                error=None,
                chunks_retrieved=0,
                chunks_relevant=0,
                duration_ms=0,
            ),
        )
        dispatcher = ParallelDispatcher([agent])
        await dispatcher.dispatch(document_name="target.pdf")

        agent.analyze.assert_called_once_with("target.pdf")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# run_parallel_analysis convenience function
# ---------------------------------------------------------------------------


class TestRunParallelAnalysis:
    """Test the end-to-end convenience function."""

    @pytest.mark.asyncio
    async def test_creates_agents_from_manifest_and_dispatches(self) -> None:
        manifest = ActiveSpecialistManifest(
            active_agents=[AgentName.IP, AgentName.TAX],
        )

        mock_preflight = MagicMock()
        mock_preflight.specialist_manifest = manifest

        mock_search = MagicMock()
        mock_search.search = MagicMock(return_value=[])

        mock_llm = AsyncMock()
        mock_llm.default_model = "llama3"

        result = await run_parallel_analysis(
            mock_preflight, mock_search, mock_llm,
        )

        assert isinstance(result, DispatchResult)
        assert result.agents_dispatched == 2
        assert result.total_findings == 0


# ---------------------------------------------------------------------------
# deduplicate_findings
# ---------------------------------------------------------------------------


class TestDeduplicateFindings:
    """Finding deduplication by (section_id, citation) key."""

    def test_same_citation_same_section_merged(self) -> None:
        f1 = _make_finding(AgentName.IP, "Same exact quote.", "Section 1", confidence=0.9)
        f2 = _make_finding(AgentName.GOVERNANCE, "Same exact quote.", "Section 1", confidence=0.7)

        result = deduplicate_findings([f1, f2])

        assert len(result) == 1
        assert result[0].source_agent == AgentName.IP  # higher confidence kept
        assert AgentName.GOVERNANCE.value in result[0].cross_refs

    def test_lower_confidence_duplicate_kept_when_first(self) -> None:
        f1 = _make_finding(AgentName.IP, "Same exact quote.", "Section 1", confidence=0.5)
        f2 = _make_finding(AgentName.TAX, "Same exact quote.", "Section 1", confidence=0.9)

        result = deduplicate_findings([f1, f2])

        assert len(result) == 1
        assert result[0].source_agent == AgentName.TAX  # higher confidence wins
        assert AgentName.IP.value in result[0].cross_refs

    def test_different_citations_not_merged(self) -> None:
        f1 = _make_finding(AgentName.IP, "Quote A.", "Section 1")
        f2 = _make_finding(AgentName.IP, "Quote B.", "Section 1")

        result = deduplicate_findings([f1, f2])

        assert len(result) == 2

    def test_same_citation_different_sections_not_merged(self) -> None:
        f1 = _make_finding(AgentName.IP, "Same quote.", "Section 1")
        f2 = _make_finding(AgentName.TAX, "Same quote.", "Section 2")

        result = deduplicate_findings([f1, f2])

        assert len(result) == 2

    def test_empty_input_returns_empty(self) -> None:
        assert deduplicate_findings([]) == []

    def test_single_finding_unchanged(self) -> None:
        f = _make_finding(AgentName.IP, "Unique citation.")
        result = deduplicate_findings([f])
        assert len(result) == 1
        assert result[0].id == f.id

    @pytest.mark.asyncio
    async def test_dispatch_populates_unique_findings(self) -> None:
        agents = [_make_agent(AgentName.IP, findings_count=1)]
        dispatcher = ParallelDispatcher(agents)
        result = await dispatcher.dispatch()

        assert isinstance(result.unique_findings, list)
        assert len(result.unique_findings) == result.total_findings
