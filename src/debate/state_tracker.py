"""Debate Dimension State Tracker (Step 51).

Manages per-dimension lifecycle states (active / settled / contested / unresolved)
across debate rounds. Persists state to the database between rounds.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.agents.schemas import FindingDimension
from src.db.models import DimensionStateRecord
from src.debate.schemas import DimensionState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DimensionStateTracker:
    """Track and persist dimension states across debate rounds.

    Maintains an in-memory cache of dimension states that is synchronized
    with the database at each round boundary.
    """

    def __init__(self, deal_id: str) -> None:
        self._deal_id = deal_id
        self._states: dict[FindingDimension, DimensionState] = {}
        self._round_numbers: dict[FindingDimension, int] = {}
        self._findings_counts: dict[FindingDimension, int] = {}

    @property
    def deal_id(self) -> str:
        return self._deal_id

    def initialize(
        self,
        active_dimensions: list[FindingDimension],
        findings_counts: dict[FindingDimension, int] | None = None,
    ) -> None:
        """Initialize all active dimensions to ACTIVE state at round 0.

        Called once before the debate loop begins.
        """
        for dim in active_dimensions:
            self._states[dim] = DimensionState.ACTIVE
            self._round_numbers[dim] = 0
            self._findings_counts[dim] = (
                findings_counts.get(dim, 0) if findings_counts else 0
            )

        logger.info(
            "DimensionStateTracker initialized for deal %s with %d active dimensions.",
            self._deal_id,
            len(active_dimensions),
        )

    def get_state(self, dimension: FindingDimension) -> DimensionState:
        """Get the current state of a dimension."""
        return self._states.get(dimension, DimensionState.ACTIVE)

    def get_all_states(self) -> dict[FindingDimension, DimensionState]:
        """Return a copy of all current dimension states."""
        return dict(self._states)

    def update_state(
        self,
        dimension: FindingDimension,
        new_state: DimensionState,
        round_number: int,
    ) -> None:
        """Update a dimension's state after a debate round."""
        old_state = self._states.get(dimension, DimensionState.ACTIVE)
        self._states[dimension] = new_state
        self._round_numbers[dimension] = round_number

        if old_state != new_state:
            logger.info(
                "Dimension %s transitioned %s -> %s at round %d.",
                dimension.value,
                old_state.value,
                new_state.value,
                round_number,
            )

    def is_settled(self, dimension: FindingDimension) -> bool:
        """Check if a dimension has reached SETTLED state."""
        return self._states.get(dimension) == DimensionState.SETTLED

    def get_active_dimensions(self) -> list[FindingDimension]:
        """Return dimensions that are still in ACTIVE state."""
        return [
            dim for dim, state in self._states.items()
            if state == DimensionState.ACTIVE
        ]

    def get_round_number(self, dimension: FindingDimension) -> int:
        """Get the last completed round number for a dimension."""
        return self._round_numbers.get(dimension, 0)

    async def persist(self, db_session: AsyncSession) -> None:
        """Write all current dimension states to the database.

        Uses upsert-like semantics: checks for existing records by
        (deal_id, dimension) and updates them, or inserts new records.
        """
        for dim, state in self._states.items():
            # Check for existing record
            stmt = select(DimensionStateRecord).where(
                DimensionStateRecord.deal_id == self._deal_id,
                DimensionStateRecord.dimension == dim.value,
            )
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                # DimensionStateRecord is NOT append-only, so updates are permitted
                existing.state = state.value
                existing.round_number = self._round_numbers.get(dim, 0)
                existing.findings_count = self._findings_counts.get(dim, 0)
            else:
                record = DimensionStateRecord(
                    deal_id=self._deal_id,
                    dimension=dim.value,
                    state=state.value,
                    round_number=self._round_numbers.get(dim, 0),
                    findings_count=self._findings_counts.get(dim, 0),
                )
                db_session.add(record)

        try:
            await db_session.commit()
            logger.info(
                "Persisted %d dimension states for deal %s.",
                len(self._states),
                self._deal_id,
            )
        except Exception as exc:
            await db_session.rollback()
            logger.error("Failed to persist dimension states: %s", exc)
            raise

    async def load(self, db_session: AsyncSession) -> None:
        """Load dimension states from the database.

        Populates the in-memory cache from persisted records.
        """
        stmt = select(DimensionStateRecord).where(
            DimensionStateRecord.deal_id == self._deal_id
        )
        result = await db_session.execute(stmt)
        records = result.scalars().all()

        for record in records:
            try:
                dim = FindingDimension(record.dimension)
                state = DimensionState(record.state)
                self._states[dim] = state
                self._round_numbers[dim] = record.round_number
                self._findings_counts[dim] = record.findings_count
            except ValueError:
                logger.warning(
                    "Skipping unknown dimension/state in DB: %s/%s",
                    record.dimension,
                    record.state,
                )

        logger.info(
            "Loaded %d dimension states for deal %s from database.",
            len(records),
            self._deal_id,
        )
