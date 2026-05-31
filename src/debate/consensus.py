"""Deterministic Consensus Mapper (Phase 5).

Aggregates final debate persona stances using local majority-rule
counting (no LLM calls). Categorizes findings into:
Settled, Contested, or Unresolved.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from src.debate.schemas import DebateArgument, DimensionState

if TYPE_CHECKING:
    from src.agents.schemas import FindingDimension
    from src.debate.state_tracker import DimensionStateTracker

logger = logging.getLogger(__name__)


def evaluate_finding_consensus(arguments: list[DebateArgument]) -> DimensionState:
    """Evaluate the consensus state for a single debated finding.
    
    Rules:
    - Settled: 4+/6 personas agree with BM25-verified evidence.
    - Contested: Personas split with verified evidence on both sides.
    - Unresolved: No BM25 source evidence, or fallback.
    """
    if not arguments:
        return DimensionState.UNRESOLVED

    # Use the latest argument per persona for this finding
    latest_args_by_persona: dict[str, DebateArgument] = {}
    for arg in arguments:
        persona_val = arg.persona.value
        if persona_val not in latest_args_by_persona:
            latest_args_by_persona[persona_val] = arg
        else:
            if arg.round > latest_args_by_persona[persona_val].round:
                latest_args_by_persona[persona_val] = arg

    final_arguments = list(latest_args_by_persona.values())
    
    stance_counts = Counter(arg.stance.value for arg in final_arguments)
    total_personas = len(final_arguments)
    
    has_verified_support = any(
        a.bm25_verified for a in final_arguments if a.stance.value == "support"
    )
    has_verified_oppose = any(
        a.bm25_verified for a in final_arguments if a.stance.value == "oppose"
    )

    # Contested: personas split with verified evidence on both sides
    if has_verified_support and has_verified_oppose:
        return DimensionState.CONTESTED

    # Settled: 4+/6 personas agree, and that stance has BM25-verified evidence
    for stance, count in stance_counts.items():
        if count >= 4 and total_personas >= 4:
            has_verified = any(
                a.bm25_verified for a in final_arguments if a.stance.value == stance
            )
            if has_verified:
                return DimensionState.SETTLED

    # Unresolved: no BM25 source evidence, or no consensus reached
    return DimensionState.UNRESOLVED


def aggregate_dimension_state(finding_states: list[DimensionState]) -> DimensionState:
    """Determine the overall dimension state from its constituent finding states.
    
    - If any finding is CONTESTED, the dimension is CONTESTED.
    - Else if any finding is UNRESOLVED, the dimension is UNRESOLVED.
    - Else if all findings are SETTLED, the dimension is SETTLED.
    - Default to ACTIVE if empty (though in Phase 5 it should be skipped/unresolved).
    """
    if not finding_states:
        return DimensionState.UNRESOLVED

    if DimensionState.CONTESTED in finding_states:
        return DimensionState.CONTESTED
    if DimensionState.UNRESOLVED in finding_states:
        return DimensionState.UNRESOLVED
    
    # Check if all are settled
    if all(state == DimensionState.SETTLED for state in finding_states):
        return DimensionState.SETTLED

    return DimensionState.UNRESOLVED


def run_consensus_mapping(
    all_arguments: list[DebateArgument],
    state_tracker: DimensionStateTracker,
) -> None:
    """Execute Phase 5: Consensus Mapping.
    
    Calculates finding-level consensus and updates the dimension state tracker
    with the rolled-up results before persistence.
    """
    logger.info("Executing Phase 5: Consensus Mapping...")
    
    # 1. Group arguments by dimension and finding_id
    args_by_dim_finding: dict[FindingDimension, dict[str, list[DebateArgument]]] = {}
    
    for arg in all_arguments:
        dim = arg.dimension
        fid = arg.finding_id
        if dim not in args_by_dim_finding:
            args_by_dim_finding[dim] = {}
        if fid not in args_by_dim_finding[dim]:
            args_by_dim_finding[dim][fid] = []
        args_by_dim_finding[dim][fid].append(arg)

    # 2. Evaluate consensus and update state tracker
    active_dims = state_tracker.get_all_states().keys()
    
    for dim in active_dims:
        finding_groups = args_by_dim_finding.get(dim, {})
        if not finding_groups:
            # If there were no arguments for this dimension, it remains in its previous state or becomes UNRESOLVED.
            # But let's check if it was explicitly skipped/settled earlier.
            if state_tracker.get_state(dim) == DimensionState.ACTIVE:
                state_tracker.update_state(dim, DimensionState.UNRESOLVED, state_tracker.get_round_number(dim))
            continue
            
        finding_states = []
        for fid, f_args in finding_groups.items():
            f_state = evaluate_finding_consensus(f_args)
            finding_states.append(f_state)
            
        final_dim_state = aggregate_dimension_state(finding_states)
        
        # Update the tracker with the final consensus state.
        # We don't change the round_number, just the state.
        current_round = state_tracker.get_round_number(dim)
        state_tracker.update_state(dim, final_dim_state, current_round)
        
        logger.info(
            "Consensus mapping for dimension %s -> %s (from %d findings)",
            dim.value,
            final_dim_state.value,
            len(finding_states)
        )
