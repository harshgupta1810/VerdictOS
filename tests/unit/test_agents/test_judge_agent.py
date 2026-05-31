"""Unit tests for the Judge Agent (Phase 6)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.judge_agent import JudgeAgent, _JudgeLLMOutput
from src.agents.schemas import (
    AgentName,
    Confidence,
    Finding,
    FindingDimension,
    JudgeVerdictStatus,
)
from src.common.models import ClauseType
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState
from src.search.schemas import SearchResult


@pytest.fixture
def finding() -> Finding:
    return Finding(
        id="f-123",
        claim="The patent is unassigned.",
        citation="Section 4.1 Patent Assignment",
        citation_chunk_id="chunk-1",
        source_agent=AgentName.IP,
        section_id="Section 4.1",
        absolute_page=4,
        confidence=Confidence.MEDIUM,
        dimension=FindingDimension.RISK_EXPOSURE,
        clause_type=ClauseType.IP_ASSIGNMENT,
    )


@pytest.fixture
def arguments() -> list[DebateArgument]:
    return [
        DebateArgument(
            id="arg-1",
            finding_id="f-123",
            persona=DebatePersona.PROPONENT,
            round=1,
            dimension=FindingDimension.RISK_EXPOSURE,
            stance=DebateStance.SUPPORT,
            steelman="The patent might be assigned elsewhere.",
            argument="The patent is clearly unassigned.",
            citations=["chunk-1"],
            confidence=Confidence.HIGH,
            dropout_flag=False,
            contradiction_flag=False,
        ),
        DebateArgument(
            id="arg-2",
            finding_id="f-123",
            persona=DebatePersona.CRITIC,
            round=1,
            dimension=FindingDimension.RISK_EXPOSURE,
            stance=DebateStance.OPPOSE,
            steelman="It is unassigned.",
            argument="No, it is assigned in schedule 2.",
            citations=["chunk-2"],
            confidence=Confidence.MEDIUM,
            dropout_flag=False,
            contradiction_flag=True,
        ),
        DebateArgument(
            id="arg-3",
            finding_id="f-123",
            persona=DebatePersona.DEVILS_ADVOCATE,
            round=1,
            dimension=FindingDimension.RISK_EXPOSURE,
            stance=DebateStance.OPPOSE,
            steelman="It is unassigned.",
            argument="I am dropping out.",
            citations=["chunk-2"],
            confidence=Confidence.SPECULATIVE,
            dropout_flag=True,  # Should be filtered out
            contradiction_flag=False,
        )
    ]


@pytest.fixture
def mock_search_engine() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    client = AsyncMock()
    client.default_model = "llama3"
    return client


@pytest.mark.asyncio
async def test_judge_returns_confirmed_for_settled(
    finding: Finding, arguments: list[DebateArgument], mock_search_engine: MagicMock, mock_llm_client: AsyncMock
) -> None:
    agent = JudgeAgent(search_engine=mock_search_engine, llm_client=mock_llm_client)
    result = await agent.synthesize(finding, arguments, DimensionState.SETTLED)

    assert result.finding_id == "f-123"
    assert result.status == JudgeVerdictStatus.CONFIRMED
    assert result.synthesis_rationale == "Finding was already SETTLED."
    mock_search_engine.search.assert_not_called()
    mock_llm_client.generate_with_schema.assert_not_called()


@pytest.mark.asyncio
async def test_judge_unresolved_evidence_not_found(
    finding: Finding, arguments: list[DebateArgument], mock_search_engine: MagicMock, mock_llm_client: AsyncMock
) -> None:
    agent = JudgeAgent(search_engine=mock_search_engine, llm_client=mock_llm_client)
    mock_search_engine.search.return_value = []

    result = await agent.synthesize(finding, arguments, DimensionState.UNRESOLVED)

    assert result.finding_id == "f-123"
    assert result.status == JudgeVerdictStatus.EVIDENCE_NOT_FOUND
    # Confidence weight for High (0.9) and Medium (0.5), avg is 0.7
    assert result.calibrated_confidence == 0.7
    mock_search_engine.search.assert_called_once()
    mock_llm_client.generate_with_schema.assert_not_called()


@pytest.mark.asyncio
async def test_judge_contested_llm_synthesis(
    finding: Finding, arguments: list[DebateArgument], mock_search_engine: MagicMock, mock_llm_client: AsyncMock
) -> None:
    agent = JudgeAgent(search_engine=mock_search_engine, llm_client=mock_llm_client)
    
    mock_llm_client.generate_with_schema.return_value = _JudgeLLMOutput(
        finding_id="f-123",
        status=JudgeVerdictStatus.OVERRIDDEN,
        judge_override_flag=True,
        synthesis_rationale="Overriding due to contradiction.",
        calibrated_confidence=0.0
    )

    result = await agent.synthesize(finding, arguments, DimensionState.CONTESTED)

    assert result.finding_id == "f-123"
    assert result.status == JudgeVerdictStatus.OVERRIDDEN
    assert result.judge_override_flag is True
    assert result.calibrated_confidence == 0.7  # should be overridden by the agent
    
    # Contested should skip the search engine BM25 pass
    mock_search_engine.search.assert_not_called()
    
    # Check that LLM was called with the right model
    mock_llm_client.generate_with_schema.assert_called_once()
    req = mock_llm_client.generate_with_schema.call_args[0][0]
    assert req.model == "llama3.1:1b"
    assert "Section 4.1 Patent Assignment" in req.user_prompt
    # Dropout arg should be missing
    assert "I am dropping out." not in req.user_prompt


@pytest.mark.asyncio
async def test_judge_unresolved_with_evidence_llm_synthesis(
    finding: Finding, arguments: list[DebateArgument], mock_search_engine: MagicMock, mock_llm_client: AsyncMock
) -> None:
    agent = JudgeAgent(search_engine=mock_search_engine, llm_client=mock_llm_client)
    
    # Mock search to return something
    mock_search_engine.search.return_value = [SearchResult(
        chunk_id="c1", score=1.0, document_name="doc.pdf", text="text", section_id="s1", absolute_page=1, clause_type=ClauseType.GENERAL
    )]
    
    mock_llm_client.generate_with_schema.return_value = _JudgeLLMOutput(
        finding_id="f-123",
        status=JudgeVerdictStatus.CONFIRMED,
        judge_override_flag=False,
        synthesis_rationale="Evidence found, confirms finding.",
        calibrated_confidence=0.0
    )

    result = await agent.synthesize(finding, arguments, DimensionState.UNRESOLVED)

    assert result.finding_id == "f-123"
    assert result.status == JudgeVerdictStatus.CONFIRMED
    assert result.judge_override_flag is False
    assert result.calibrated_confidence == 0.7
    
    mock_search_engine.search.assert_called_once()
    mock_llm_client.generate_with_schema.assert_called_once()


@pytest.mark.asyncio
async def test_judge_llm_failure_fallback(
    finding: Finding, arguments: list[DebateArgument], mock_search_engine: MagicMock, mock_llm_client: AsyncMock
) -> None:
    agent = JudgeAgent(search_engine=mock_search_engine, llm_client=mock_llm_client)
    
    mock_llm_client.generate_with_schema.side_effect = Exception("LLM connection error")

    result = await agent.synthesize(finding, arguments, DimensionState.CONTESTED)

    assert result.finding_id == "f-123"
    assert result.status == JudgeVerdictStatus.OVERRIDDEN
    assert result.judge_override_flag is True
    assert "LLM connection error" in result.synthesis_rationale
    assert result.calibrated_confidence == 0.7
