"""Phase 7: Final Verdict Generation.

Synthesizes Go/No-Go briefs, Human Escalation Lists, and Evidence Gap
Reports from settled debate states and judge synthesized results.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import JudgeSynthesisResult, JudgeVerdictStatus
from src.db.models import Deal, DebateArg, DimensionStateRecord, Finding, InvalidStateTransitionError
from src.debate.schemas import DimensionState
from src.verdict.schemas import (
    EscalationArgument,
    EscalationItem,
    EvidenceGapItem,
    EvidenceGapReport,
    GoNoGoBrief,
    GoNoGoFinding,
    HumanEscalationList,
    VerdictOutput,
)

logger = logging.getLogger(__name__)

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}

CONFIDENCE_RANK = {
    "high": 3,
    "medium": 2,
    "speculative": 1
}

class VerdictAssembler:
    """Assembles the final structured verdict and persists it."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    async def generate_verdict(
        self,
        deal_id: str,
        judge_results: dict[str, JudgeSynthesisResult] | None = None,
    ) -> VerdictOutput:
        """Generate the complete Verdict JSON and transition deal state."""
        judge_results = judge_results or {}

        # 1. Fetch Findings, Dimension States, and Debate Arguments
        findings_query = await self.db.execute(select(Finding).where(Finding.deal_id == deal_id))
        findings = findings_query.scalars().all()

        states_query = await self.db.execute(select(DimensionStateRecord).where(DimensionStateRecord.deal_id == deal_id))
        dimension_states = states_query.scalars().all()
        dim_state_map = {ds.dimension: ds.state for ds in dimension_states}

        # 2. Build Go/No-Go Brief
        go_no_go_findings = []
        for f in findings:
            state = dim_state_map.get(f.dimension, DimensionState.ACTIVE.value)
            is_settled = (state == DimensionState.SETTLED.value)
            
            # Or if it's confirmed by judge
            judge_res = judge_results.get(f.finding_id)
            is_judge_confirmed = (judge_res and judge_res.status == JudgeVerdictStatus.CONFIRMED)

            if is_settled or is_judge_confirmed:
                conf = judge_res.calibrated_confidence if judge_res else 1.0 # fallback
                go_no_go_findings.append(
                    GoNoGoFinding(
                        finding_id=f.finding_id,
                        claim=f.claim,
                        severity=f.severity,
                        confidence=conf,
                        dimension=f.dimension,
                        section_citation=f.citation,
                        clause_type=f.clause_type,
                    )
                )

        # Rank by severity (descending) then confidence (descending)
        go_no_go_findings.sort(
            key=lambda x: (SEVERITY_RANK.get(x.severity.lower(), 0), x.confidence),
            reverse=True
        )
        brief = GoNoGoBrief(findings=go_no_go_findings)

        # 3. Build Human Escalation List
        escalations = []
        for f in findings:
            state = dim_state_map.get(f.dimension, DimensionState.ACTIVE.value)
            if state in (DimensionState.CONTESTED.value, DimensionState.UNRESOLVED.value):
                # Fetch debate args for this finding
                args_query = await self.db.execute(
                    select(DebateArg)
                    .where(DebateArg.finding_id == f.finding_id)
                    .order_by(DebateArg.round_number)
                )
                args = args_query.scalars().all()

                esc_args = []
                has_contradictions = False
                has_dropouts = False

                for arg in args:
                    esc_args.append(
                        EscalationArgument(
                            persona=arg.persona_name,
                            stance=arg.stance,
                            argument=arg.argument,
                            calibrated_confidence=arg.calibrated_confidence,
                        )
                    )
                    if arg.contradiction_flag:
                        has_contradictions = True
                    if arg.dropout_flag:
                        has_dropouts = True

                judge_res = judge_results.get(f.finding_id)
                escalations.append(
                    EscalationItem(
                        finding_id=f.finding_id,
                        claim=f.claim,
                        dimension=f.dimension,
                        arguments=esc_args,
                        has_contradictions=has_contradictions,
                        has_dropouts=has_dropouts,
                        judge_override=judge_res.judge_override_flag if judge_res else False,
                        judge_notes=judge_res.synthesis_rationale if judge_res else "",
                    )
                )

        escalation_list = HumanEscalationList(escalations=escalations)

        # 4. Build Evidence Gap Report
        # Any dimensions that were 'skip' (not tracked or 0 findings)
        from src.agents.schemas import FindingDimension
        all_dims = {d.value for d in FindingDimension}
        tracked_dims = set(dim_state_map.keys())
        skipped_dims = list(all_dims - tracked_dims)

        gap_items = []
        # Find claims marked EVIDENCE_NOT_FOUND
        missing_claims_by_dim = {}
        for f in findings:
            judge_res = judge_results.get(f.finding_id)
            if judge_res and judge_res.status == JudgeVerdictStatus.EVIDENCE_NOT_FOUND:
                missing_claims_by_dim.setdefault(f.dimension, []).append(f.claim)

        # Also identify unconfirmed entities from notes/cross_refs if applicable
        # (For Phase 7, we'll placeholder remedies unless explicitly provided)
        for dim, missing in missing_claims_by_dim.items():
            gap_items.append(
                EvidenceGapItem(
                    dimension=dim,
                    missing_claims=missing,
                    unconfirmed_entities=[],  # placeholder: GraphRAG integration in future phase
                    suggested_remedies=["Request updated document from seller", "Submit manual verification request"],
                )
            )

        gap_report = EvidenceGapReport(
            skipped_dimensions=skipped_dims,
            gaps=gap_items,
        )

        # 5. Assemble final Output
        verdict = VerdictOutput(
            deal_id=deal_id,
            brief=brief,
            escalation_list=escalation_list,
            evidence_gap_report=gap_report,
        )

        # 6. Persist JSON to Deal and transition state
        # In SQLAlchemy 2.0 async, use update() returning nothing or deal object
        deal_query = await self.db.execute(select(Deal).where(Deal.deal_id == deal_id))
        deal = deal_query.scalar_one_or_none()
        
        if deal:
            if deal.status != "complete":
                # Ensure valid transition via model event (judging -> complete)
                # Note: If it's currently something else, this might raise InvalidStateTransitionError
                deal.status = "complete"
                
            metadata = deal.metadata_json or {}
            metadata["verdict"] = verdict.model_dump(mode="json")
            deal.metadata_json = metadata
            
            self.db.add(deal)
            await self.db.commit()
            logger.info("Verdict generated and persisted for deal_id %s", deal_id)
        else:
            logger.warning("Deal %s not found while generating verdict.", deal_id)

        return verdict
