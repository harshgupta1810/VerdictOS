"""Unit tests for Step 53 — Immutable Audit Store Writer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from typing import Any

from src.agents.schemas import Confidence, FindingDimension
from src.debate.audit import (
    append_debate_audit,
    persist_debate_argument,
    persist_round_transcript,
)
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance


def _make_arg(**overrides: object) -> DebateArgument:
    """Create a valid DebateArgument."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": "proponent",
        "round": 1,
        "dimension": "risk_exposure",
        "stance": "support",
        "steelman": "Opposing view is valid because...",
        "argument": "Risk is documented.",
        "citations": ["chunk-1"],
        "confidence": "high",
    }
    base.update(overrides)
    return DebateArgument.model_validate(base)


class TestAppendDebateAudit:
    @pytest.mark.asyncio
    async def test_writes_audit_record(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        await append_debate_audit(
            deal_id="deal-1",
            event_type="debate_started",
            description="Debate engine started for 3 dimensions.",
            raw_payload={"dimensions": 3},
            db_session=mock_session,
        )

        mock_session.add.assert_called_once()
        record = mock_session.add.call_args[0][0]
        assert record.deal_id == "deal-1"
        assert record.event_type == "debate_started"
        assert record.actor == "debate_engine"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_on_error(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await append_debate_audit(
                deal_id="deal-1",
                event_type="test",
                description="test",
                raw_payload=None,
                db_session=mock_session,
            )

        mock_session.rollback.assert_called_once()


class TestPersistDebateArgument:
    @pytest.mark.asyncio
    async def test_persists_argument(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        arg = _make_arg()
        await persist_debate_argument("deal-1", arg, mock_session)

        mock_session.add.assert_called_once()
        db_record = mock_session.add.call_args[0][0]
        assert db_record.argument_id == arg.id
        assert db_record.finding_id == "finding-1"
        assert db_record.persona_name == "proponent"
        assert db_record.stance == "support"
        assert db_record.calibrated_confidence == "high"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_preserves_dropout_flag(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        arg = _make_arg(dropout_flag=True)
        await persist_debate_argument("deal-1", arg, mock_session)

        db_record = mock_session.add.call_args[0][0]
        assert db_record.dropout_flag is True


class TestPersistRoundTranscript:
    @pytest.mark.asyncio
    async def test_persists_all_arguments_plus_audit(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        args = [
            _make_arg(id="arg-1", persona="proponent"),
            _make_arg(id="arg-2", persona="critic", stance="oppose"),
            _make_arg(id="arg-3", persona="devils_advocate", stance="oppose"),
        ]

        await persist_round_transcript("deal-1", 1, args, mock_session)

        # 3 debate args + 1 audit record = 4 add calls
        assert mock_session.add.call_count == 4
        mock_session.commit.assert_called_once()

        # The last add should be the audit record
        last_record = mock_session.add.call_args_list[-1][0][0]
        assert last_record.event_type == "debate_round_complete"
        assert "Round 1 complete" in last_record.description

    @pytest.mark.asyncio
    async def test_audit_payload_captures_dropouts(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        args = [
            _make_arg(persona="proponent"),
            _make_arg(persona="critic", dropout_flag=True),
        ]

        await persist_round_transcript("deal-1", 2, args, mock_session)

        audit_record = mock_session.add.call_args_list[-1][0][0]
        assert "critic" in audit_record.raw_payload["dropouts"]

    @pytest.mark.asyncio
    async def test_rollback_on_commit_failure(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit.side_effect = Exception("DB failure")

        with pytest.raises(Exception, match="DB failure"):
            await persist_round_transcript(
                "deal-1", 1, [_make_arg()], mock_session
            )

        mock_session.rollback.assert_called_once()
