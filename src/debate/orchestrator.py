"""DebateOS Multi-Agent Orchestrator (Steps 57-58).

Coordinates the asyncio debate lifecycle across active dimensions:
- Handles dimension threshold gate (full activation vs limited mode).
- Runs debates for active dimensions concurrently.
- Applies context compression between rounds.
- Evaluates round exit conditions.
- Enforces a hard 3-round cap.
- Persists all results to the database and immutable audit store.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from src.agents.schemas import Finding, FindingDimension
from src.debate.audit import persist_round_transcript
from src.debate.compressor import compress_round_context, serialize_round_summary
from src.debate.consensus import run_consensus_mapping
from src.debate.executor import execute_dimension_debate
from src.debate.schemas import DebateArgument, DebatePersona, DimensionState
from src.debate.state_tracker import DimensionStateTracker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.llm.client import LLMClientProtocol
    from src.search.search_engine import SparseSearchEngine

logger = logging.getLogger(__name__)

# Core questions mapped to each of the 8 dimensions
DIMENSION_QUESTIONS: dict[FindingDimension, str] = {
    FindingDimension.RISK_EXPOSURE: (
        "What are the primary risk exposures, liabilities, and potential legal/financial "
        "downsides identified in the transaction documents?"
    ),
    FindingDimension.VALUATION_FAIRNESS: (
        "Is the deal valuation and purchase price justified based on the financial terms, "
        "assets, and liabilities found?"
    ),
    FindingDimension.STRATEGIC_FIT: (
        "How well does the target company align with the acquirer's strategic objectives "
        "and business model?"
    ),
    FindingDimension.SYNERGY_VALIDITY: (
        "Are the projected synergies, cost savings, and operational benefits realistic "
        "and supported by the contract terms?"
    ),
    FindingDimension.INTEGRATION_COMPLEXITY: (
        "What are the main post-merger integration challenges, system compatibilities, "
        "and operational risks?"
    ),
    FindingDimension.MARKET_TIMING: (
        "Is the timing of this transaction optimal given the market conditions, "
        "regulatory trends, and industry developments?"
    ),
    FindingDimension.REGULATORY_APPROVAL: (
        "What are the antitrust, compliance, and regulatory hurdles required to close "
        "this transaction?"
    ),
    FindingDimension.EXIT_SCENARIO: (
        "What exit options, termination rights, and transition provisions exist for "
        "the parties if the deal fails or after completion?"
    ),
}

# The 6 personas for full debate
FULL_DEBATE_PERSONAS = [
    DebatePersona.PROPONENT,
    DebatePersona.CRITIC,
    DebatePersona.DEVILS_ADVOCATE,
    DebatePersona.VALUATION_SKEPTIC,
    DebatePersona.INTEGRATION_REALIST,
    DebatePersona.REGULATORS_EYE,
]

# The 3 core personas for limited mode (1-2 findings)
LIMITED_DEBATE_PERSONAS = [
    DebatePersona.PROPONENT,
    DebatePersona.CRITIC,
    DebatePersona.DEVILS_ADVOCATE,
]


def check_exit_conditions(
    dimension_states: dict[FindingDimension, DimensionState],
    round_count: int,
) -> bool:
    """Check if the debate loop should continue or exit.

    Exit conditions:
    (a) All dimensions are settled -> exit (return False).
    (b) round_count >= 3 -> exit (return False).
    (c) No active dimensions left -> exit (return False).

    Returns:
        True if the debate should continue, False if it should exit.
    """
    if round_count >= 3:
        logger.info("Exit condition met: round count limit (3) reached.")
        return False

    if not dimension_states:
        return False

    # Check if all dimensions are settled
    all_settled = all(
        state == DimensionState.SETTLED for state in dimension_states.values()
    )
    if all_settled:
        logger.info("Exit condition met: all dimensions are SETTLED.")
        return False

    # Check if there are any active dimensions left
    has_active = any(
        state == DimensionState.ACTIVE for state in dimension_states.values()
    )
    if not has_active:
        logger.info("Exit condition met: no dimensions are ACTIVE.")
        return False

    return True


async def run_debate_loop(
    deal_id: str,
    findings: list[Finding],
    llm_client: LLMClientProtocol,
    search_engine: SparseSearchEngine,
    db_session: AsyncSession,
    model: str = "llama3.2:1b",
) -> tuple[dict[FindingDimension, DimensionState], list[DebateArgument]]:
    """Top-level async orchestrator that executes the adversarial debate loops.

    1. Groups findings by dimension.
    2. Determines dimension activation mode (threshold gate).
    3. Runs active dimension debates concurrently per round.
    4. Applies context compression between rounds.
    5. Enforces hard 3-round cap or early exit on consensus.
    6. Writes full transcripts to the immutable audit store.
    7. Returns final states and all debate arguments.
    """
    logger.info("Initializing DebateOS orchestrator for deal %s.", deal_id)

    # 1. Group findings by dimension
    dimension_findings: dict[FindingDimension, list[Finding]] = {
        dim: [] for dim in FindingDimension
    }
    for f in findings:
        dimension_findings[f.dimension].append(f)

    # Determine activation & counts
    active_dimensions: list[FindingDimension] = []
    findings_counts: dict[FindingDimension, int] = {}
    dimension_modes: dict[FindingDimension, str] = {}  # "full", "limited", or "skip"

    for dim, f_list in dimension_findings.items():
        count = len(f_list)
        findings_counts[dim] = count
        if count >= 3:
            active_dimensions.append(dim)
            dimension_modes[dim] = "full"
        elif 1 <= count <= 2:
            active_dimensions.append(dim)
            dimension_modes[dim] = "limited"
        else:
            dimension_modes[dim] = "skip"
            # In Phase 7 or elsewhere, an evidence gap record is written if skipped

    # Initialize dimension state tracker
    state_tracker = DimensionStateTracker(deal_id)
    state_tracker.initialize(active_dimensions, findings_counts)

    all_debate_arguments: list[DebateArgument] = []
    round_number = 1

    # Keep track of arguments per dimension across rounds to detect contradictions/context
    history_by_dim: dict[FindingDimension, list[DebateArgument]] = {
        dim: [] for dim in active_dimensions
    }
    context_by_dim: dict[FindingDimension, str] = {
        dim: "" for dim in active_dimensions
    }

    # Main debate loop
    while True:
        # Determine exit conditions before starting the round
        current_states = state_tracker.get_all_states()
        if not check_exit_conditions(current_states, round_number - 1):
            break

        logger.info("--- Starting Debate Round %d ---", round_number)
        round_tasks = []

        # Gather tasks for all active dimensions concurrently
        active_dims_this_round = [
            dim for dim in active_dimensions
            if state_tracker.get_state(dim) == DimensionState.ACTIVE
        ]

        if not active_dims_this_round:
            logger.info("No active dimensions remaining to debate this round.")
            break

        for dim in active_dims_this_round:
            mode = dimension_modes[dim]
            # Limited mode only runs in Round 1
            if mode == "limited" and round_number > 1:
                # Mark as settled or unresolved if 1 round complete
                state_tracker.update_state(dim, DimensionState.SETTLED, round_number - 1)
                continue

            # Debate all findings in this dimension
            for finding in dimension_findings[dim]:
                personas = (
                    FULL_DEBATE_PERSONAS if mode == "full" else LIMITED_DEBATE_PERSONAS
                )
                core_q = DIMENSION_QUESTIONS.get(
                    dim, "What are the key implications of this finding?"
                )

                task = execute_dimension_debate(
                    dimension=dim,
                    finding_id=finding.id,
                    finding_claim=finding.claim,
                    finding_citation=finding.citation,
                    finding_confidence=finding.confidence.value,
                    core_question=core_q,
                    round_number=round_number,
                    active_personas=personas,
                    llm_client=llm_client,
                    search_engine=search_engine,
                    previous_arguments=history_by_dim[dim],
                    previous_context=context_by_dim[dim],
                    model=model,
                )
                round_tasks.append((dim, task))

        if not round_tasks:
            break

        # Execute concurrent debates for this round
        dims_list = [t[0] for t in round_tasks]
        futures = [t[1] for t in round_tasks]
        results = await asyncio.gather(*futures, return_exceptions=True)

        # Process round results
        round_arguments: list[DebateArgument] = []
        arguments_by_dim_this_round: dict[FindingDimension, list[DebateArgument]] = {
            dim: [] for dim in active_dimensions
        }

        for dim, res in zip(dims_list, results):
            if isinstance(res, BaseException):
                logger.error(
                    "Error executing debate for dimension %s in round %d: %s",
                    dim.value,
                    round_number,
                    res,
                )
                continue

            validated_args, new_state = res
            round_arguments.extend(validated_args)
            arguments_by_dim_this_round[dim].extend(validated_args)

            # Update state in tracker
            state_tracker.update_state(dim, new_state, round_number)

        # Persist round transcript to DB (Step 53 / 58)
        if round_arguments:
            await persist_round_transcript(
                deal_id=deal_id,
                round_number=round_number,
                arguments=round_arguments,
                db_session=db_session,
            )
            all_debate_arguments.extend(round_arguments)

        # Apply Context Compression for next round (Step 52)
        for dim in active_dimensions:
            if arguments_by_dim_this_round[dim]:
                history_by_dim[dim].extend(arguments_by_dim_this_round[dim])
                # Compress context
                comp_summary = compress_round_context(
                    arguments=arguments_by_dim_this_round[dim],
                    round_number=round_number,
                    dimension_state=state_tracker.get_state(dim),
                )
                context_by_dim[dim] = serialize_round_summary(comp_summary)

        round_number += 1

    # Phase 5: Consensus Mapping (run before persistence)
    run_consensus_mapping(all_debate_arguments, state_tracker)

    # Persist final states to database
    await state_tracker.persist(db_session)

    final_states = state_tracker.get_all_states()
    logger.info(
        "DebateOS orchestrator finished. Final states: %s, Total arguments: %d.",
        {dim.value: state.value for dim, state in final_states.items()},
        len(all_debate_arguments),
    )

    return final_states, all_debate_arguments
