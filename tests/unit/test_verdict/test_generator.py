"""Unit tests for Phase 7 Verdict Generation."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from src.db.models import Base, Deal, Finding, DebateArg, DimensionStateRecord
from src.verdict.generator import VerdictAssembler
from src.agents.schemas import JudgeSynthesisResult, JudgeVerdictStatus
from src.debate.schemas import DimensionState

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    """Fixture to set up and tear down an in-memory SQLite database session."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
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
async def test_verdict_assembler_generates_correct_json(db_session: AsyncSession) -> None:
    # 1. Setup Deal
    deal = Deal(client_id="test_client", status="judging", metadata_json={})
    db_session.add(deal)
    await db_session.commit()

    # 2. Setup Findings
    f1 = Finding(
        deal_id=deal.deal_id,
        claim="Critical IP Assignment risk",
        citation="Section 4.1",
        section_id="sec-4.1",
        confidence="high",
        dimension="risk_exposure",
        agent_name="ip_agent",
        severity="critical",
        clause_type="ip_assignment"
    )
    f2 = Finding(
        deal_id=deal.deal_id,
        claim="Missing data privacy addendum",
        citation="Section 9.0",
        section_id="sec-9.0",
        confidence="medium",
        dimension="integration_complexity",
        agent_name="privacy_agent",
        severity="high",
        clause_type="data_protection"
    )
    db_session.add_all([f1, f2])
    await db_session.commit()

    # 3. Setup Dimension States
    # Make risk_exposure SETTLED (should go to brief)
    # Make integration_complexity CONTESTED (should go to escalation)
    ds1 = DimensionStateRecord(
        deal_id=deal.deal_id,
        dimension="risk_exposure",
        state=DimensionState.SETTLED.value,
        round_number=2,
        findings_count=1
    )
    ds2 = DimensionStateRecord(
        deal_id=deal.deal_id,
        dimension="integration_complexity",
        state=DimensionState.CONTESTED.value,
        round_number=3,
        findings_count=1
    )
    db_session.add_all([ds1, ds2])
    await db_session.commit()

    # 4. Setup Debate Args for Contested
    arg1 = DebateArg(
        finding_id=f2.finding_id,
        round_number=1,
        persona_name="proponent",
        stance="agree",
        steelman="It is missing.",
        argument="The addendum is legally required.",
        calibrated_confidence="high",
        contradiction_flag=False,
        dropout_flag=False,
        bm25_verified=True
    )
    db_session.add(arg1)
    await db_session.commit()

    # 5. Judge outputs
    judge_results = {
        f2.finding_id: JudgeSynthesisResult(
            finding_id=f2.finding_id,
            status=JudgeVerdictStatus.OVERRIDDEN,
            judge_override_flag=True,
            synthesis_rationale="Overriding consensus because risk is existential.",
            calibrated_confidence=0.8
        )
    }

    # 6. Assemble Verdict
    assembler = VerdictAssembler(db_session)
    verdict = await assembler.generate_verdict(deal.deal_id, judge_results)

    # 7. Assertions
    assert verdict.deal_id == deal.deal_id
    
    # Brief should contain f1
    assert len(verdict.brief.findings) == 1
    assert verdict.brief.findings[0].finding_id == f1.finding_id
    assert verdict.brief.findings[0].severity == "critical"

    # Escalation should contain f2
    assert len(verdict.escalation_list.escalations) == 1
    esc = verdict.escalation_list.escalations[0]
    assert esc.finding_id == f2.finding_id
    assert esc.judge_override is True
    assert "existential" in esc.judge_notes
    assert len(esc.arguments) == 1
    
    # Gap Report should have skipped dimensions
    # Total dimensions is 8, 2 are tracked, 6 should be skipped
    assert len(verdict.evidence_gap_report.skipped_dimensions) == 6

    # Verify state transition and persistence
    refreshed_deal = await db_session.execute(select(Deal).where(Deal.deal_id == deal.deal_id))
    refreshed_deal = refreshed_deal.scalar_one()
    assert refreshed_deal.status == "complete"
    assert "verdict" in refreshed_deal.metadata_json
