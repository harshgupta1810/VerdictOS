"""SQLAlchemy ORM Models.

Defines database tables: deals, findings, debate_args,
audit_records, escalations, disputes. Implements append-only
integrity constraints for audit and debate logs.

Engines: PostgreSQL (production), SQLite (local fallback).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class Deal(Base):
    """Represents a M&A deal transaction and its files manifest."""

    __tablename__ = "deals"

    deal_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created")
    metadata_json: Mapped[Any] = mapped_column("metadata", JSON, nullable=True)


class Finding(Base):
    """Represents a discovered contract/operational finding by an agent."""

    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[str] = mapped_column(String(500), nullable=False)
    section_id: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    cross_refs: Mapped[Any] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pyrefly: ignore [deprecated]
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DebateArg(Base):
    """Represents an individual debate argument in DebateOS. Append-only."""

    __tablename__ = "debate_args"

    argument_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.finding_id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    persona_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    stance: Mapped[str] = mapped_column(String(50), nullable=False)
    steelman: Mapped[str] = mapped_column(Text, nullable=False)
    argument: Mapped[str] = mapped_column(Text, nullable=False)
    citations_array: Mapped[Any] = mapped_column(JSON, nullable=True)
    calibrated_confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    contradiction_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    bm25_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    dropout_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[Any] = mapped_column(JSON, nullable=True)


class DimensionStateRecord(Base):
    """Persists per-dimension debate state between rounds."""

    __tablename__ = "dimension_states"

    record_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # pyrefly: ignore [deprecated]
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditRecord(Base):
    """Represents an immutable transaction audit log entry. Append-only."""

    __tablename__ = "audit_records"

    audit_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    # pyrefly: ignore [deprecated]
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Escalation(Base):
    """Represents an issue escalated to human experts for verification."""

    __tablename__ = "escalations"

    escalation_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    finding_id: Mapped[str | None] = mapped_column(
        ForeignKey("findings.finding_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # pyrefly: ignore [deprecated]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Dispute(Base):
    """Represents an end-user dispute filed against a finding."""

    __tablename__ = "disputes"

    dispute_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.finding_id"), nullable=False
    )
    dispute_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pyrefly: ignore [deprecated]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeltaRun(Base):
    """Represents a delta analysis execution run for index updates."""

    __tablename__ = "delta_runs"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.deal_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="started")
    # pyrefly: ignore [deprecated]
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[Any] = mapped_column("metadata", JSON, nullable=True)


class InvalidStateTransitionError(ValueError):
    """Raised when an invalid deal status transition is attempted."""
    pass


VALID_TRANSITIONS = {
    "created": {"indexing", "error"},
    "indexing": {"analyzing", "error"},
    "analyzing": {"debating", "error"},
    "debating": {"judging", "error"},
    "judging": {"complete", "error"},
    "complete": {"indexing", "error"},
    "error": {"indexing", "created"}
}


def validate_state_transition(current_state: str, new_state: str) -> None:
    """Validate transition from current_state to new_state."""
    if current_state == new_state:
        return
    if new_state not in VALID_TRANSITIONS.get(current_state, set()):
        raise InvalidStateTransitionError(
            f"Invalid transition from state '{current_state}' to '{new_state}'"
        )


@event.listens_for(Deal.status, "set")
def validate_deal_status_transition(target: Deal, value: str, oldvalue: str, initiator: Any) -> None:
    from sqlalchemy.orm.attributes import NO_VALUE
    if oldvalue is not None and oldvalue is not NO_VALUE:
        validate_state_transition(oldvalue, value)


# Append-Only Event Listeners
@event.listens_for(DebateArg, "before_update")
@event.listens_for(DebateArg, "before_delete")
@event.listens_for(AuditRecord, "before_update")
@event.listens_for(AuditRecord, "before_delete")
def block_modifications(mapper: Any, connection: Any, target: Any) -> None:
    """Enforces append-only constraints by raising an exception on modify/delete."""
    raise PermissionError("Table is append-only. Modification and deletion of records is blocked.")

