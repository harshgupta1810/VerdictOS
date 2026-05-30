"""Tests for SpecialistAgent and create_specialist_agents factory."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base_agent import RelevanceCheckResult, _AnalysisOutput, _RawFinding
from src.agents.planner_agent import SPECIALIST_REGISTRY
from src.agents.schemas import ActiveSpecialistManifest, AgentName, Finding
from src.agents.specialist_agent import DOMAIN_DESCRIPTIONS, DOMAIN_INSTRUCTIONS, SpecialistAgent, create_specialist_agents
from src.common.exceptions import LLMClientError
from src.common.models import ClauseType
from src.llm.schemas import LLMResponse
from src.search.schemas import SearchResult


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _ip_definition():
    """Return the IP specialist definition from the registry."""
    return next(d for d in SPECIALIST_REGISTRY if d.agent_name == AgentName.IP)


def _mock_search_result(
    text: str = "All intellectual property rights shall be assigned.",
    chunk_id: str = "doc1:chunk:1",
    clause_type: ClauseType = ClauseType.IP_ASSIGNMENT,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=5.0,
        document_name="agreement.pdf",
        text=text,
        section_id="Section 4.2",
        absolute_page=12,
        clause_type=clause_type,
        references_sections=[],
        highlights=[],
    )


def _make_agent(
    search_results: list[SearchResult] | None = None,
    relevance_result: RelevanceCheckResult | None = None,
    analysis_output: _AnalysisOutput | None = None,
    generate_with_schema_side_effect: list | None = None,
) -> tuple[SpecialistAgent, MagicMock, AsyncMock]:
    """Create an IP SpecialistAgent with mocked search + LLM."""

    mock_search = MagicMock()
    mock_search.search = MagicMock(return_value=search_results or [])

    mock_llm = AsyncMock()
    mock_llm.default_model = "llama3"

    if generate_with_schema_side_effect:
        mock_llm.generate_with_schema = AsyncMock(
            side_effect=generate_with_schema_side_effect,
        )
    else:
        # Default: relevance → True, analysis → one finding
        default_relevance = relevance_result or RelevanceCheckResult(relevant=True, reason="matches")
        default_analysis = analysis_output or _AnalysisOutput(
            findings=[
                _RawFinding(
                    claim="Patent assignment clause found",
                    citation="All intellectual property rights shall be assigned.",
                    confidence=0.85,
                )
            ]
        )
        mock_llm.generate_with_schema = AsyncMock(
            side_effect=[default_relevance, default_analysis],
        )

    agent = SpecialistAgent(_ip_definition(), mock_search, mock_llm)
    return agent, mock_search, mock_llm


# ---------------------------------------------------------------------------
# Domain descriptions
# ---------------------------------------------------------------------------


class TestDomainDescriptions:
    """Verify domain descriptions and M&A instructions cover all 16 agents."""

    def test_all_agents_have_descriptions(self) -> None:
        for agent_name in AgentName:
            assert agent_name in DOMAIN_DESCRIPTIONS
        assert len(DOMAIN_DESCRIPTIONS) == 16

    def test_all_agents_have_domain_instructions(self) -> None:
        for agent_name in AgentName:
            assert agent_name in DOMAIN_INSTRUCTIONS, f"{agent_name} missing domain instructions"
            assert len(DOMAIN_INSTRUCTIONS[agent_name]) > 50, f"{agent_name} instructions too short"
        assert len(DOMAIN_INSTRUCTIONS) == 16

    def test_domain_instructions_injected_into_system_prompt(self) -> None:
        agent, _, _ = _make_agent()
        prompt = agent.build_system_prompt()
        assert "DOMAIN FOCUS" in prompt
        assert "RED FLAGS" in prompt
        # IP-specific red flags should appear
        assert "open-source" in prompt.lower() or "ownership" in prompt.lower()


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    """Verify system prompt includes required elements."""

    def test_contains_relevance_check_instruction(self) -> None:
        agent, _, _ = _make_agent()
        prompt = agent.build_system_prompt()
        assert "RELEVANCE CHECK" in prompt
        assert "discard" in prompt.lower()

    def test_contains_strict_json_instruction(self) -> None:
        agent, _, _ = _make_agent()
        prompt = agent.build_system_prompt()
        assert "JSON" in prompt
        assert "markdown" in prompt.lower()

    def test_contains_citation_mandatory_instruction(self) -> None:
        agent, _, _ = _make_agent()
        prompt = agent.build_system_prompt()
        assert "citation" in prompt.lower()
        assert "exact quote" in prompt.lower()

    def test_contains_untrusted_source_instruction(self) -> None:
        agent, _, _ = _make_agent()
        prompt = agent.build_system_prompt()
        assert "<untrusted_source>" in prompt


# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------


class TestRelevancePrompt:
    """Verify relevance prompt structure."""

    def test_contains_untrusted_source_tags_with_metadata(self) -> None:
        agent, _, _ = _make_agent()
        chunk = _mock_search_result()
        prompt = agent.build_relevance_prompt(chunk)

        assert '<untrusted_source doc_id="agreement.pdf"' in prompt
        assert 'section="Section 4.2"' in prompt
        assert 'page="12"' in prompt
        assert "</untrusted_source>" in prompt
        assert chunk.text in prompt

    def test_requests_json_with_relevant_and_reason_fields(self) -> None:
        agent, _, _ = _make_agent()
        chunk = _mock_search_result()
        prompt = agent.build_relevance_prompt(chunk)

        assert '"relevant"' in prompt
        assert '"reason"' in prompt

    def test_references_agent_domain_in_question(self) -> None:
        agent, _, _ = _make_agent()
        chunk = _mock_search_result()
        prompt = agent.build_relevance_prompt(chunk)

        # Should mention the domain description so the LLM knows what to check against
        assert "intellectual property" in prompt.lower()


class TestAnalysisPrompt:
    """Verify analysis prompt wraps chunks in XML tags."""

    def test_wraps_chunk_in_untrusted_source_tags(self) -> None:
        agent, _, _ = _make_agent()
        chunk = _mock_search_result()
        prompt = agent.build_analysis_prompt(chunk)

        assert '<untrusted_source doc_id="agreement.pdf"' in prompt
        assert 'section="Section 4.2"' in prompt
        assert 'page="12"' in prompt
        assert "</untrusted_source>" in prompt
        assert chunk.text in prompt


# ---------------------------------------------------------------------------
# Relevance filter
# ---------------------------------------------------------------------------


class TestRelevanceFilter:
    """Verify relevance-check discard gate."""

    @pytest.mark.asyncio
    async def test_irrelevant_chunks_discarded(self) -> None:
        chunk = _mock_search_result()
        agent, mock_search, mock_llm = _make_agent(
            search_results=[chunk],
            generate_with_schema_side_effect=[
                RelevanceCheckResult(relevant=False, reason="not IP related"),
            ],
        )

        result = await agent.analyze()
        assert result.chunks_retrieved == 1
        assert result.chunks_relevant == 0
        assert result.findings == []

    @pytest.mark.asyncio
    async def test_relevant_chunks_kept(self) -> None:
        chunk = _mock_search_result()
        agent, mock_search, mock_llm = _make_agent(
            search_results=[chunk],
            generate_with_schema_side_effect=[
                RelevanceCheckResult(relevant=True, reason="IP related"),
                _AnalysisOutput(
                    findings=[
                        _RawFinding(
                            claim="Patent found",
                            citation="All intellectual property rights shall be assigned.",
                            confidence=0.9,
                        )
                    ]
                ),
            ],
        )

        result = await agent.analyze()
        assert result.chunks_retrieved == 1
        assert result.chunks_relevant == 1
        assert len(result.findings) == 1


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------


class TestAnalyzePipeline:
    """Test the full analyze() pipeline."""

    @pytest.mark.asyncio
    async def test_produces_finding_with_mandatory_fields(self) -> None:
        chunk = _mock_search_result()
        agent, _, _ = _make_agent(search_results=[chunk])
        result = await agent.analyze()

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert isinstance(finding, Finding)
        assert finding.claim == "Patent assignment clause found"
        assert finding.citation == "All intellectual property rights shall be assigned."
        assert finding.citation_chunk_id == "doc1:chunk:1"
        assert finding.source_agent == AgentName.IP
        assert finding.section_id == "Section 4.2"
        assert finding.absolute_page == 12
        assert finding.confidence == 0.85

    @pytest.mark.asyncio
    async def test_no_search_results_returns_empty(self) -> None:
        agent, _, _ = _make_agent(search_results=[])
        result = await agent.analyze()

        assert result.chunks_retrieved == 0
        assert result.chunks_relevant == 0
        assert result.findings == []
        assert result.error is None

    @pytest.mark.asyncio
    async def test_llm_timeout_on_analysis_produces_empty_findings(self) -> None:
        """Chunk-level LLM timeout is logged as warning, findings are empty."""
        chunk = _mock_search_result()
        agent, mock_search, mock_llm = _make_agent(
            search_results=[chunk],
            generate_with_schema_side_effect=[
                # Relevance check: timeout → conservative include
                LLMClientError("Ollama timed out"),
                # Analysis: timeout → chunk skipped
                LLMClientError("Ollama timed out"),
            ],
        )

        result = await agent.analyze()
        # Agent succeeds but with no findings due to chunk-level failures
        assert result.findings == []
        assert result.chunks_retrieved == 1
        assert result.error is None  # Only top-level failures set error

    @pytest.mark.asyncio
    async def test_document_name_filter_applied(self) -> None:
        chunk = _mock_search_result()
        agent, mock_search, _ = _make_agent(search_results=[chunk])
        await agent.analyze(document_name="target.pdf")

        query = mock_search.search.call_args[0][0]
        assert query.filters.document_name == "target.pdf"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestCreateSpecialistAgents:
    """Test create_specialist_agents factory."""

    def test_creates_only_active_agents(self) -> None:
        manifest = ActiveSpecialistManifest(
            active_agents=[AgentName.IP, AgentName.TAX],
        )
        mock_search = MagicMock()
        mock_llm = AsyncMock()

        agents = create_specialist_agents(manifest, mock_search, mock_llm)

        assert len(agents) == 2
        names = {a.agent_name for a in agents}
        assert names == {AgentName.IP, AgentName.TAX}

    def test_creates_all_16_on_fallback(self) -> None:
        manifest = ActiveSpecialistManifest(
            active_agents=list(AgentName),
            used_fallback=True,
        )
        mock_search = MagicMock()
        mock_llm = AsyncMock()

        agents = create_specialist_agents(manifest, mock_search, mock_llm)
        assert len(agents) == 16
