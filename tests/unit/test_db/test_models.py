import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import AuditRecord, Base, Deal, DebateArg, Dispute, Escalation, Finding, DeltaRun, InvalidStateTransitionError, validate_state_transition

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Fixture to set up and tear down an in-memory SQLite database session."""
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_retrieve_deal(db_session: AsyncSession) -> None:
    """Verifies that a Deal model can be inserted and retrieved successfully."""
    deal = Deal(client_id="client-123", status="created", metadata_json={"manifest": []})
    db_session.add(deal)
    await db_session.commit()

    result = await db_session.execute(select(Deal).filter_by(client_id="client-123"))
    retrieved = result.scalar_one()
    assert retrieved.deal_id is not None
    assert retrieved.status == "created"
    assert retrieved.metadata_json == {"manifest": []}


@pytest.mark.asyncio
async def test_create_and_retrieve_finding(db_session: AsyncSession) -> None:
    """Verifies that a Finding model can be inserted and retrieved successfully."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    finding = Finding(
        deal_id=deal.deal_id,
        claim="Claim",
        citation="Sec 1",
        section_id="1",
        confidence="high",
        dimension="Fit",
        agent_name="Agent",
        severity="low",
        clause_type="general",
    )
    db_session.add(finding)
    await db_session.commit()

    result = await db_session.execute(select(Finding).filter_by(claim="Claim"))
    retrieved = result.scalar_one()
    assert retrieved.finding_id is not None
    assert retrieved.deal_id == deal.deal_id
    assert retrieved.confidence == "high"


@pytest.mark.asyncio
async def test_append_only_debate_arg_blocks_updates_and_deletes(
    db_session: AsyncSession,
) -> None:
    """Verifies that updates or deletes on DebateArg raise a PermissionError."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    finding = Finding(
        deal_id=deal.deal_id,
        claim="Claim",
        citation="Sec 1",
        section_id="1",
        confidence="high",
        dimension="Fit",
        agent_name="Agent",
        severity="low",
        clause_type="general",
    )
    db_session.add(finding)
    await db_session.commit()

    arg = DebateArg(
        finding_id=finding.finding_id,
        round_number=1,
        persona_name="Critic",
        stance="against",
        steelman="Steelman",
        argument="Arg",
        calibrated_confidence="high",
    )
    db_session.add(arg)
    await db_session.commit()

    # Try updating
    arg.argument = "Updated Arg"
    with pytest.raises(PermissionError) as exc_info:
        await db_session.commit()
    assert "blocked" in str(exc_info.value)
    await db_session.rollback()

    # Try deleting
    await db_session.delete(arg)
    with pytest.raises(PermissionError) as exc_info:
        await db_session.commit()
    assert "blocked" in str(exc_info.value)
    await db_session.rollback()


@pytest.mark.asyncio
async def test_append_only_audit_record_blocks_updates_and_deletes(
    db_session: AsyncSession,
) -> None:
    """Verifies that updates or deletes on AuditRecord raise a PermissionError."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    record = AuditRecord(
        deal_id=deal.deal_id,
        event_type="pipeline_started",
        actor="system",
        description="Started",
    )
    db_session.add(record)
    await db_session.commit()

    # Try updating
    record.description = "Updated description"
    with pytest.raises(PermissionError) as exc_info:
        await db_session.commit()
    assert "blocked" in str(exc_info.value)
    await db_session.rollback()

    # Try deleting
    await db_session.delete(record)
    with pytest.raises(PermissionError) as exc_info:
        await db_session.commit()
    assert "blocked" in str(exc_info.value)
    await db_session.rollback()


@pytest.mark.asyncio
async def test_create_and_retrieve_delta_run(db_session: AsyncSession) -> None:
    """Verifies that a DeltaRun model can be inserted and retrieved successfully."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    run = DeltaRun(
        deal_id=deal.deal_id,
        status="started",
        metadata_json={"new_files": ["doc2.pdf"]}
    )
    db_session.add(run)
    await db_session.commit()

    result = await db_session.execute(select(DeltaRun).filter_by(deal_id=deal.deal_id))
    retrieved = result.scalar_one()
    assert retrieved.run_id is not None
    assert retrieved.status == "started"
    assert retrieved.metadata_json == {"new_files": ["doc2.pdf"]}


@pytest.mark.asyncio
async def test_valid_deal_status_transitions(db_session: AsyncSession) -> None:
    """Verifies that valid state transitions succeed."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    # created -> indexing
    deal.status = "indexing"
    await db_session.commit()
    assert deal.status == "indexing"

    # indexing -> analyzing
    deal.status = "analyzing"
    await db_session.commit()
    assert deal.status == "analyzing"


@pytest.mark.asyncio
async def test_invalid_deal_status_transitions(db_session: AsyncSession) -> None:
    """Verifies that invalid state transitions raise InvalidStateTransitionError."""
    deal = Deal(client_id="client-123", status="created")
    db_session.add(deal)
    await db_session.commit()

    # created -> debating is invalid
    with pytest.raises(InvalidStateTransitionError):
        deal.status = "debating"

def test_same_state_transition() -> None:
    # should not raise
    validate_state_transition("created", "created")
