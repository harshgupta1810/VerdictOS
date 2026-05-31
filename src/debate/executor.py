"""Per-Dimension Debate Executor (Step 54).

Runs all active personas concurrently for a single dimension in a single
debate round. Applies Gates B–E to every persona output. Enforces the
dropout-aware Settled rule.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from src.agents.schemas import Confidence, FindingDimension
from src.common.exceptions import PersonaDropoutError
from src.debate.gates import (
    apply_dropout_settled_rule,
    gate_a_argument_generator,
    gate_b_citation_verifier,
    gate_c_passage_accuracy,
    gate_d_confidence_calibrator,
    gate_e_contradiction_detector,
)
from src.debate.schemas import DebateArgument, DebatePersona, DimensionState

if TYPE_CHECKING:
    from src.llm.client import LLMClientProtocol
    from src.search.search_engine import SparseSearchEngine

logger = logging.getLogger(__name__)


async def execute_dimension_debate(
    dimension: FindingDimension,
    finding_id: str,
    finding_claim: str,
    finding_citation: str,
    finding_confidence: str,
    core_question: str,
    round_number: int,
    active_personas: list[DebatePersona],
    llm_client: LLMClientProtocol,
    search_engine: SparseSearchEngine,
    previous_arguments: list[DebateArgument],
    previous_context: str = "",
    model: str = "llama3.2:1b",
) -> tuple[list[DebateArgument], DimensionState]:
    """Execute a single debate round for one dimension.

    1. Generates arguments for all active personas concurrently (Gate A).
    2. Applies Gates B–E sequentially to each argument.
    3. Applies the dropout-aware Settled rule.
    4. Determines the resulting dimension state.

    Returns:
        Tuple of (validated_arguments, new_dimension_state).
    """
    logger.info(
        "Executing debate round %d for dimension %s with %d personas.",
        round_number,
        dimension.value,
        len(active_personas),
    )

    # ── Gate A: Generate arguments concurrently ──────────────────────────
    generation_tasks = [
        gate_a_argument_generator(
            persona=persona,
            finding_id=finding_id,
            finding_claim=finding_claim,
            finding_citation=finding_citation,
            finding_confidence=finding_confidence,
            dimension=dimension,
            core_question=core_question,
            round_number=round_number,
            llm_client=llm_client,
            model=model,
            previous_context=previous_context,
        )
        for persona in active_personas
    ]

    raw_arguments: list[DebateArgument] = []
    results = await asyncio.gather(*generation_tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, DebateArgument):
            raw_arguments.append(result)
        elif isinstance(result, PersonaDropoutError):
            logger.warning(
                "Persona %s dropped out: %s",
                active_personas[i].value,
                result,
            )
        elif isinstance(result, Exception):
            logger.error(
                "Unexpected error generating argument for persona %s: %s",
                active_personas[i].value,
                result,
            )

    if not raw_arguments:
        logger.warning(
            "No arguments generated for dimension %s round %d — marking unresolved.",
            dimension.value,
            round_number,
        )
        return [], DimensionState.UNRESOLVED

    # ── Gates B–E: Apply reliability gates to each argument ──────────────

    validated_arguments: list[DebateArgument] = []

    for arg in raw_arguments:
        # Gate B: BM25 Citation Verification
        arg = gate_b_citation_verifier(arg, search_engine)

        # Gate C: Passage Accuracy Check
        arg = gate_c_passage_accuracy(arg, search_engine)

        # Gate E: Contradiction Detection (needs prior round history)
        arg = gate_e_contradiction_detector(arg, previous_arguments)

        validated_arguments.append(arg)

    # Gate D: Confidence Calibration (needs all arguments in this round)
    for i, arg in enumerate(validated_arguments):
        validated_arguments[i] = gate_d_confidence_calibrator(arg, validated_arguments)

    # ── Determine dimension state ────────────────────────────────────────
    new_state = _determine_dimension_state(validated_arguments)

    # ── Apply dropout-aware Settled rule ─────────────────────────────────
    new_state = apply_dropout_settled_rule(new_state, validated_arguments)

    logger.info(
        "Dimension %s round %d complete: %d arguments, state=%s.",
        dimension.value,
        round_number,
        len(validated_arguments),
        new_state.value,
    )

    return validated_arguments, new_state


def _determine_dimension_state(arguments: list[DebateArgument]) -> DimensionState:
    """Determine the dimension state based on persona stances.

    Heuristic:
    - If 4+/6 personas agree on a stance → SETTLED
    - If there is disagreement with BM25-verified evidence → CONTESTED
    - Otherwise → ACTIVE (still in play for more rounds)
    """
    if not arguments:
        return DimensionState.UNRESOLVED

    # Count stances
    from collections import Counter
    stance_counts = Counter(arg.stance.value for arg in arguments)
    total = len(arguments)

    # Check for supermajority (4+ out of 6)
    for stance, count in stance_counts.items():
        if count >= 4 and total >= 4:
            return DimensionState.SETTLED

    # Check for strong disagreement with evidence
    has_bm25_support = any(
        a.bm25_verified for a in arguments if a.stance.value == "support"
    )
    has_bm25_oppose = any(
        a.bm25_verified for a in arguments if a.stance.value == "oppose"
    )
    if has_bm25_support and has_bm25_oppose:
        return DimensionState.CONTESTED

    # Still active — needs more rounds
    return DimensionState.ACTIVE
