"""Unit tests for Step 51 — Debate Dimension State Tracker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.schemas import FindingDimension
from src.debate.schemas import DimensionState
from src.debate.state_tracker import DimensionStateTracker


class TestDimensionStateTrackerInit:
    def test_initialize_sets_active_state(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([
            FindingDimension.RISK_EXPOSURE,
            FindingDimension.VALUATION_FAIRNESS,
        ])
        assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.ACTIVE
        assert tracker.get_state(FindingDimension.VALUATION_FAIRNESS) == DimensionState.ACTIVE

    def test_initialize_with_findings_counts(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize(
            [FindingDimension.RISK_EXPOSURE],
            findings_counts={FindingDimension.RISK_EXPOSURE: 5},
        )
        assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.ACTIVE

    def test_deal_id_property(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-42")
        assert tracker.deal_id == "deal-42"


class TestDimensionStateTrackerOperations:
    def test_update_state(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([FindingDimension.RISK_EXPOSURE])
        tracker.update_state(
            FindingDimension.RISK_EXPOSURE,
            DimensionState.SETTLED,
            round_number=2,
        )
        assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.SETTLED
        assert tracker.get_round_number(FindingDimension.RISK_EXPOSURE) == 2

    def test_is_settled(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([FindingDimension.RISK_EXPOSURE])
        assert tracker.is_settled(FindingDimension.RISK_EXPOSURE) is False

        tracker.update_state(
            FindingDimension.RISK_EXPOSURE,
            DimensionState.SETTLED,
            round_number=1,
        )
        assert tracker.is_settled(FindingDimension.RISK_EXPOSURE) is True

    def test_get_active_dimensions(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([
            FindingDimension.RISK_EXPOSURE,
            FindingDimension.VALUATION_FAIRNESS,
            FindingDimension.EXIT_SCENARIO,
        ])
        tracker.update_state(
            FindingDimension.RISK_EXPOSURE,
            DimensionState.SETTLED,
            round_number=1,
        )
        active = tracker.get_active_dimensions()
        assert FindingDimension.RISK_EXPOSURE not in active
        assert FindingDimension.VALUATION_FAIRNESS in active
        assert FindingDimension.EXIT_SCENARIO in active

    def test_get_all_states(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([
            FindingDimension.RISK_EXPOSURE,
            FindingDimension.STRATEGIC_FIT,
        ])
        tracker.update_state(
            FindingDimension.STRATEGIC_FIT,
            DimensionState.CONTESTED,
            round_number=3,
        )
        states = tracker.get_all_states()
        assert states[FindingDimension.RISK_EXPOSURE] == DimensionState.ACTIVE
        assert states[FindingDimension.STRATEGIC_FIT] == DimensionState.CONTESTED

    def test_unknown_dimension_returns_active(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        assert tracker.get_state(FindingDimension.MARKET_TIMING) == DimensionState.ACTIVE

    def test_get_round_number_default_zero(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        assert tracker.get_round_number(FindingDimension.RISK_EXPOSURE) == 0


class TestDimensionStateTrackerPersistence:
    @pytest.mark.asyncio
    async def test_persist_inserts_new_records(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([FindingDimension.RISK_EXPOSURE])

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        # Simulate no existing record found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        await tracker.persist(mock_session)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        added_record = mock_session.add.call_args[0][0]
        assert added_record.deal_id == "deal-1"
        assert added_record.dimension == "risk_exposure"
        assert added_record.state == "active"

    @pytest.mark.asyncio
    async def test_persist_updates_existing_records(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([FindingDimension.RISK_EXPOSURE])
        tracker.update_state(
            FindingDimension.RISK_EXPOSURE,
            DimensionState.CONTESTED,
            round_number=2,
        )

        # Simulate existing record found
        existing_record = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_record
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        await tracker.persist(mock_session)

        assert existing_record.state == "contested"
        assert existing_record.round_number == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_populates_from_db(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")

        mock_record = MagicMock()
        mock_record.dimension = "risk_exposure"
        mock_record.state = "settled"
        mock_record.round_number = 3
        mock_record.findings_count = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        await tracker.load(mock_session)

        assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.SETTLED
        assert tracker.get_round_number(FindingDimension.RISK_EXPOSURE) == 3


    @pytest.mark.asyncio
    async def test_persist_rolls_back_on_commit_error(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        tracker.initialize([FindingDimension.RISK_EXPOSURE])
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.commit.side_effect = Exception("DB error")
        
        with pytest.raises(Exception, match="DB error"):
            await tracker.persist(mock_session)
            
        mock_session.rollback.assert_called_once()


    @pytest.mark.asyncio
    async def test_load_skips_unknown_dimension_or_state(self) -> None:
        tracker = DimensionStateTracker(deal_id="deal-1")
        
        mock_record = MagicMock()
        mock_record.dimension = "unknown_dim"
        mock_record.state = "unknown_state"
        mock_record.round_number = 3
        mock_record.findings_count = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        
        await tracker.load(mock_session)
        assert len(tracker.get_all_states()) == 0
