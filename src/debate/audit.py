"""Immutable Audit Store Writer (Step 53).

Append-only writer for debate audit records and arguments.
Writes to the ``audit_records`` and ``debate_args`` tables.
No UPDATE or DELETE permitted (enforced by SQLAlchemy event listeners
on these tables in ``src/db/models.py``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.db.models import AuditRecord, DebateArg
from src.debate.schemas import DebateArgument

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def append_debate_audit(
    deal_id: str,
    event_type: str,
    description: str,
    raw_payload: dict | list | None,
    db_session: AsyncSession,
) -> None:
    """Append an immutable audit record for debate events.

    Writes to the ``audit_records`` table which is append-only
    (UPDATE and DELETE are blocked by ORM event listeners).
    """
    record = AuditRecord(
        deal_id=deal_id,
        event_type=event_type,
        actor="debate_engine",
        description=description,
        raw_payload=raw_payload,
    )
    db_session.add(record)
    try:
        await db_session.commit()
        logger.info(
            "Audit record written: deal=%s event=%s",
            deal_id,
            event_type,
        )
    except Exception as exc:
        await db_session.rollback()
        logger.error("Failed to write audit record: %s", exc)
        raise


async def persist_debate_argument(
    deal_id: str,
    argument: DebateArgument,
    db_session: AsyncSession,
) -> None:
    """Persist a single debate argument to the ``debate_args`` table.

    Converts a Pydantic DebateArgument to the ORM DebateArg model.
    The table is append-only (UPDATE/DELETE blocked by ORM listeners).
    """
    db_record = DebateArg(
        argument_id=argument.id,
        finding_id=argument.finding_id,
        round_number=argument.round,
        persona_name=argument.persona.value,
        dimension=argument.dimension.value,
        stance=argument.stance.value,
        steelman=argument.steelman,
        argument=argument.argument,
        citations_array=argument.citations,
        calibrated_confidence=argument.confidence.value,
        contradiction_flag=argument.contradiction_flag,
        bm25_verified=argument.bm25_verified,
        dropout_flag=argument.dropout_flag,
        raw_payload=argument.model_dump(mode="json"),
    )
    db_session.add(db_record)
    try:
        await db_session.commit()
        logger.debug(
            "Debate argument persisted: id=%s persona=%s round=%d",
            argument.id,
            argument.persona.value,
            argument.round,
        )
    except Exception as exc:
        await db_session.rollback()
        logger.error("Failed to persist debate argument %s: %s", argument.id, exc)
        raise


async def persist_round_transcript(
    deal_id: str,
    round_number: int,
    arguments: list[DebateArgument],
    db_session: AsyncSession,
) -> None:
    """Persist all arguments from a single debate round.

    Writes each argument to ``debate_args`` and a summary audit record
    to ``audit_records``.
    """
    # Persist individual arguments
    for arg in arguments:
        db_record = DebateArg(
            argument_id=arg.id,
            finding_id=arg.finding_id,
            round_number=arg.round,
            persona_name=arg.persona.value,
            dimension=arg.dimension.value,
            stance=arg.stance.value,
            steelman=arg.steelman,
            argument=arg.argument,
            citations_array=arg.citations,
            calibrated_confidence=arg.confidence.value,
            contradiction_flag=arg.contradiction_flag,
            bm25_verified=arg.bm25_verified,
            dropout_flag=arg.dropout_flag,
            raw_payload=arg.model_dump(mode="json"),
        )
        db_session.add(db_record)

    # Write round summary audit record
    summary_payload = {
        "round_number": round_number,
        "argument_count": len(arguments),
        "personas": [a.persona.value for a in arguments],
        "stances": {a.persona.value: a.stance.value for a in arguments},
        "dropouts": [a.persona.value for a in arguments if a.dropout_flag],
        "contradictions": [a.persona.value for a in arguments if a.contradiction_flag],
    }
    audit_record = AuditRecord(
        deal_id=deal_id,
        event_type="debate_round_complete",
        actor="debate_engine",
        description=f"Round {round_number} complete: {len(arguments)} arguments recorded.",
        raw_payload=summary_payload,
    )
    db_session.add(audit_record)

    try:
        await db_session.commit()
        logger.info(
            "Round %d transcript persisted for deal %s: %d arguments.",
            round_number,
            deal_id,
            len(arguments),
        )
    except Exception as exc:
        await db_session.rollback()
        logger.error(
            "Failed to persist round %d transcript for deal %s: %s",
            round_number,
            deal_id,
            exc,
        )
        raise
