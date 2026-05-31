"""Unit tests for Step 54 — Per-Dimension Debate Executor."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from typing import Any

from src.agents.schemas import Confidence, FindingDimension
from src.common.exceptions import PersonaDropoutError, SchemaRetryExhaustedError
from src.debate.executor import (
    _determine_dimension_state,
    execute_dimension_debate,
)
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState
from src.search.schemas import SearchResult
from src.common.models import ClauseType


def _make_arg(**overrides: object) -> DebateArgument:
    """Create a valid DebateArgument."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": "proponent",
        "round": 1,
        "dimension": "risk_exposure",
        "stance": "support",
        "steelman": "Valid opposing point.",
        "argument": "Risk is real and documented.",
        "citations": ["chunk-1"],
        "confidence": "high",
        "bm25_verified": True,
    }
    base.update(overrides)
    return DebateArgument.model_validate(base)


def _mock_search_engine() -> MagicMock:
    """Create a mock search engine that verifies all citations."""
    engine = MagicMock()
    result = SearchResult(
        chunk_id="chunk-1",
        score=1.0,
        document_name="test.pdf",
        text="Risk is real and documented in the contract clause about liability.",
        section_id="Section 1",
        absolute_page=1,
        clause_type=ClauseType.GENERAL,
    )
    engine.resolve_section_reference.return_value = [result]
    engine.fetch_sections.return_value = [result]
    return engine


class TestExecuteDimensionDebate:
    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        mock_client = AsyncMock()
        # Each persona generates a valid argument
        mock_client.generate_with_schema.side_effect = [
            _make_arg(id="a1", persona="proponent", stance="support"),
            _make_arg(id="a2", persona="critic", stance="oppose"),
            _make_arg(id="a3", persona="devils_advocate", stance="oppose"),
        ]

        args, state = await execute_dimension_debate(
            dimension=FindingDimension.RISK_EXPOSURE,
            finding_id="finding-1",
            finding_claim="Risk identified",
            finding_citation="Section 4.2",
            finding_confidence="high",
            core_question="How severe?",
            round_number=1,
            active_personas=[
                DebatePersona.PROPONENT,
                DebatePersona.CRITIC,
                DebatePersona.DEVILS_ADVOCATE,
            ],
            llm_client=mock_client,
            search_engine=_mock_search_engine(),
            previous_arguments=[],
        )

        assert len(args) == 3
        assert all(isinstance(a, DebateArgument) for a in args)

    @pytest.mark.asyncio
    async def test_handles_persona_dropout(self) -> None:
        mock_client = AsyncMock()
        # First persona succeeds, second drops out (SchemaRetryExhausted)
        mock_client.generate_with_schema.side_effect = [
            _make_arg(id="a1", persona="proponent"),
            SchemaRetryExhaustedError("Failed"),
        ]

        args, state = await execute_dimension_debate(
            dimension=FindingDimension.RISK_EXPOSURE,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            core_question="Q?",
            round_number=1,
            active_personas=[
                DebatePersona.PROPONENT,
                DebatePersona.CRITIC,
            ],
            llm_client=mock_client,
            search_engine=_mock_search_engine(),
            previous_arguments=[],
        )

        # Both should appear — one valid, one dropout
        assert len(args) == 2
        dropout_args = [a for a in args if a.dropout_flag]
        assert len(dropout_args) == 1

    @pytest.mark.asyncio
    async def test_unexpected_exception_logged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _mock_gate_a(*args: Any, **kwargs: Any) -> DebateArgument:
            if kwargs.get("persona") == DebatePersona.CRITIC:
                raise ValueError("Random error")
            return _make_arg(persona="proponent")
            
        monkeypatch.setattr("src.debate.executor.gate_a_argument_generator", _mock_gate_a)

        args, state = await execute_dimension_debate(
            dimension=FindingDimension.RISK_EXPOSURE,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            core_question="Q?",
            round_number=1,
            active_personas=[
                DebatePersona.PROPONENT,
                DebatePersona.CRITIC,
            ],
            llm_client=AsyncMock(),
            search_engine=_mock_search_engine(),
            previous_arguments=[],
        )

        assert len(args) == 1

    @pytest.mark.asyncio
    async def test_all_personas_fail_returns_unresolved(self) -> None:
        mock_client = AsyncMock()
        mock_client.generate_with_schema.side_effect = RuntimeError("All fail")

        args, state = await execute_dimension_debate(
            dimension=FindingDimension.RISK_EXPOSURE,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            core_question="Q?",
            round_number=1,
            active_personas=[DebatePersona.PROPONENT],
            llm_client=mock_client,
            search_engine=_mock_search_engine(),
            previous_arguments=[],
        )

        assert len(args) == 0
        assert state == DimensionState.UNRESOLVED

    @pytest.mark.asyncio
    async def test_gates_applied_to_all_arguments(self) -> None:
        mock_client = AsyncMock()
        mock_client.generate_with_schema.return_value = _make_arg(
            citations=["chunk-1"], bm25_verified=False
        )

        engine = _mock_search_engine()
        args, _ = await execute_dimension_debate(
            dimension=FindingDimension.RISK_EXPOSURE,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            core_question="Q?",
            round_number=1,
            active_personas=[DebatePersona.PROPONENT],
            llm_client=mock_client,
            search_engine=engine,
            previous_arguments=[],
        )

        # Gate B should have been called (resolve_section_reference)
        engine.resolve_section_reference.assert_called()


class TestDetermineDimensionState:
    def test_supermajority_settles(self) -> None:
        # 4+ same stance out of 5
        args = [
            _make_arg(stance="support"),
            _make_arg(stance="support"),
            _make_arg(stance="support"),
            _make_arg(stance="support"),
            _make_arg(stance="oppose"),
        ]
        assert _determine_dimension_state(args) == DimensionState.SETTLED

    def test_evidenced_disagreement_contested(self) -> None:
        args = [
            _make_arg(stance="support", bm25_verified=True),
            _make_arg(stance="oppose", bm25_verified=True),
            _make_arg(stance="support", bm25_verified=False),
        ]
        assert _determine_dimension_state(args) == DimensionState.CONTESTED

    def test_no_clear_majority_stays_active(self) -> None:
        args = [
            _make_arg(stance="support", bm25_verified=False),
            _make_arg(stance="oppose", bm25_verified=False),
            _make_arg(stance="neutral", bm25_verified=False),
        ]
        assert _determine_dimension_state(args) == DimensionState.ACTIVE

    def test_empty_arguments_unresolved(self) -> None:
        assert _determine_dimension_state([]) == DimensionState.UNRESOLVED
