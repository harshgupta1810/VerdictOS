"""Unit tests for Steps 57 & 58 — Debate Loop Orchestrator."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Any

from src.agents.schemas import AgentName, Confidence, Finding, FindingDimension, Severity
from src.common.models import ClauseType
from src.debate.orchestrator import check_exit_conditions, run_debate_loop
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState


def _make_finding(dim: FindingDimension, **overrides: object) -> Finding:
    """Helper to construct a valid Finding."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "claim": "Test finding claim",
        "citation": "Section 1",
        "citation_chunk_id": "chunk-1",
        "source_agent": AgentName.IP,
        "section_id": "Section 1",
        "absolute_page": 1,
        "confidence": "high",
        "dimension": dim,
        "domain": "test",
        "severity": Severity.MEDIUM,
        "clause_type": ClauseType.GENERAL,
        "verified": True,
        "cross_refs": [],
        "notes": "some notes",
    }
    base.update(overrides)
    return Finding.model_validate(base)


def _make_arg(dim: FindingDimension, round_num: int, **overrides: object) -> DebateArgument:
    """Helper to construct a valid DebateArgument."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": DebatePersona.PROPONENT,
        "round": round_num,
        "dimension": dim,
        "stance": DebateStance.SUPPORT,
        "steelman": "Valid opposing point.",
        "argument": "Valid proponent point.",
        "citations": ["chunk-1"],
        "confidence": Confidence.HIGH,
        "bm25_verified": True,
    }
    base.update(overrides)
    return DebateArgument.model_validate(base)


class TestExitConditions:
    """Validate check_exit_conditions helper logic."""

    def test_continues_when_active_and_below_round_limit(self) -> None:
        states = {
            FindingDimension.RISK_EXPOSURE: DimensionState.ACTIVE,
            FindingDimension.VALUATION_FAIRNESS: DimensionState.SETTLED,
        }
        # Below limit (rounds 0, 1, 2 should continue)
        assert check_exit_conditions(states, 0) is True
        assert check_exit_conditions(states, 1) is True
        assert check_exit_conditions(states, 2) is True

    def test_exits_when_round_limit_reached(self) -> None:
        states = {FindingDimension.RISK_EXPOSURE: DimensionState.ACTIVE}
        assert check_exit_conditions(states, 3) is False
        assert check_exit_conditions(states, 4) is False

    def test_exits_when_all_dimensions_settled(self) -> None:
        states = {
            FindingDimension.RISK_EXPOSURE: DimensionState.SETTLED,
            FindingDimension.VALUATION_FAIRNESS: DimensionState.SETTLED,
        }
        assert check_exit_conditions(states, 1) is False

    def test_exits_when_no_active_dimensions_left(self) -> None:
        states = {
            FindingDimension.RISK_EXPOSURE: DimensionState.CONTESTED,
            FindingDimension.VALUATION_FAIRNESS: DimensionState.UNRESOLVED,
        }
        assert check_exit_conditions(states, 1) is False


class TestDebateLoopOrchestrator:
    """Validate full orchestrator execution loop."""

    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_skip_threshold_gate(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Verify that dimensions with 0 findings are skipped entirely."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        # Mock result for state tracker persist to avoid AttributeError
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        # Empty findings
        states, args = await run_debate_loop("deal-1", [], llm, search, db)

        assert len(args) == 0
        # Skipped dimensions are not even initialized in state tracker
        assert len(states) == 0
        mock_execute.assert_not_called()
        mock_persist.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_limited_mode_gate(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Verify 1-2 findings activates limited mode (1 round, 3 personas)."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        # Mock result for state tracker persist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        dim = FindingDimension.RISK_EXPOSURE
        findings = [_make_finding(dim)]

        # Mock debate executor to return validated arguments and settled state
        mock_arg = _make_arg(dim, round_num=1)
        mock_execute.return_value = ([mock_arg], DimensionState.SETTLED)

        states, args = await run_debate_loop("deal-1", findings, llm, search, db)

        # Should run exactly 1 round
        assert len(args) == 1
        assert states[dim] == DimensionState.SETTLED
        mock_execute.assert_called_once()
        # Verify it used limited personas (3 personas)
        called_personas = mock_execute.call_args[1]["active_personas"]
        assert len(called_personas) == 3
        assert DebatePersona.VALUATION_SKEPTIC not in called_personas

    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_full_activation_gate(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Verify >= 3 findings activates full mode (up to 3 rounds, 6 personas)."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        # Mock result for state tracker persist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        dim = FindingDimension.RISK_EXPOSURE
        # 3 findings
        findings = [_make_finding(dim), _make_finding(dim), _make_finding(dim)]

        # Mock round 1: ACTIVE state (3 calls)
        # Mock round 2: SETTLED state (3 calls)
        mock_arg_1 = _make_arg(dim, round_num=1)
        mock_arg_2 = _make_arg(dim, round_num=2)
        mock_execute.side_effect = [
            ([mock_arg_1], DimensionState.ACTIVE),
            ([mock_arg_1], DimensionState.ACTIVE),
            ([mock_arg_1], DimensionState.ACTIVE),
            ([mock_arg_2], DimensionState.SETTLED),
            ([mock_arg_2], DimensionState.SETTLED),
            ([mock_arg_2], DimensionState.SETTLED),
        ]

        states, args = await run_debate_loop("deal-1", findings, llm, search, db)

        # Should execute 2 rounds before settling early
        assert mock_execute.call_count == 6  # 3 findings * 2 rounds
        assert len(args) == 6
        assert states[dim] == DimensionState.SETTLED

        # Verify it used all 6 personas in the call
        called_personas = mock_execute.call_args[1]["active_personas"]
        assert len(called_personas) == 6

    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_limited_mode_exits_after_one_round(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Verify limited mode forces SETTLED and breaks in round 2 if still ACTIVE."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        dim = FindingDimension.RISK_EXPOSURE
        findings = [_make_finding(dim)]

        mock_arg = _make_arg(dim, round_num=1)
        # Round 1 returns ACTIVE. 
        mock_execute.side_effect = [
            ([mock_arg], DimensionState.ACTIVE),
        ]

        states, args = await run_debate_loop("deal-1", findings, llm, search, db)

        # In round 2, it hits line 212-213, updates state to SETTLED, and `round_tasks` is empty so it hits line 242 and breaks.
        assert states[dim] == DimensionState.SETTLED
        assert mock_execute.call_count == 1
        
    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_execute_dimension_debate_raises_exception(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Verify that exceptions from execute_dimension_debate are caught and logged."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        dim = FindingDimension.RISK_EXPOSURE
        findings = [_make_finding(dim), _make_finding(dim), _make_finding(dim)]

        # Raise exception
        mock_execute.side_effect = Exception("Debate crashed")

        states, args = await run_debate_loop("deal-1", findings, llm, search, db)

        # Dimension state remains ACTIVE because the round failed, but since we reach the end of round 1, loop continues until round 3 and exits.
        assert mock_execute.call_count == 9  # 3 findings * 3 rounds
        assert len(args) == 0

    @pytest.mark.asyncio
    @patch("src.debate.orchestrator.run_consensus_mapping")
    @patch("src.debate.orchestrator.execute_dimension_debate")
    @patch("src.debate.orchestrator.persist_round_transcript")
    async def test_no_active_dims_this_round_break(
        self,
        mock_persist: AsyncMock,
        mock_execute: AsyncMock,
        mock_consensus: MagicMock,
    ) -> None:
        """Trigger lines 204-205 by mocking state tracker behavior."""
        llm = AsyncMock()
        search = MagicMock()
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        dim = FindingDimension.RISK_EXPOSURE
        findings = [_make_finding(dim), _make_finding(dim), _make_finding(dim)]

        with patch("src.debate.orchestrator.DimensionStateTracker") as mock_tracker_cls:
            mock_tracker = mock_tracker_cls.return_value
            mock_tracker.persist = AsyncMock()
            # For check_exit_conditions, return ACTIVE so it doesn't exit
            mock_tracker.get_all_states.return_value = {dim: DimensionState.ACTIVE}
            # For the active_dims_this_round check, return SETTLED so it's empty
            mock_tracker.get_state.return_value = DimensionState.SETTLED

            await run_debate_loop("deal-1", findings, llm, search, db)
