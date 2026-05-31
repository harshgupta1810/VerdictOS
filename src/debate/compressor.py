"""Context Compressor (Step 52).

Compresses full debate round transcripts into structured JSON summaries
for context window management between debate rounds.

Preserves all ``notes`` fields verbatim. Targets ~90% token reduction
by extracting only stance, key claim, citation IDs, confidence, and notes.
"""

from __future__ import annotations

import json
import logging

from src.debate.schemas import (
    DebateArgument,
    DimensionState,
    PersonaRoundSummary,
    RoundSummary,
)

logger = logging.getLogger(__name__)


def compress_round_context(
    arguments: list[DebateArgument],
    round_number: int,
    dimension_state: DimensionState = DimensionState.ACTIVE,
) -> RoundSummary:
    """Compress a full round transcript into a structured summary.

    Extracts only essential fields from each persona's argument:
    - stance, key_claim (first 200 chars of argument), citation_ids,
      confidence, contradiction_flag, dropout_flag, notes (verbatim).

    The resulting summary is ~90% smaller in token count than the
    full transcript.
    """
    if not arguments:
        raise ValueError("Cannot compress empty round")

    dimension = arguments[0].dimension

    persona_summaries: list[PersonaRoundSummary] = []
    for arg in arguments:
        summary = PersonaRoundSummary(
            persona=arg.persona,
            stance=arg.stance,
            key_claim=_extract_key_claim(arg.argument),
            citation_ids=list(arg.citations),
            confidence=arg.confidence,
            contradiction_flag=arg.contradiction_flag,
            dropout_flag=arg.dropout_flag,
            notes=arg.notes,  # Preserved verbatim — NEVER truncated.
        )
        persona_summaries.append(summary)

    round_summary = RoundSummary(
        round_number=round_number,
        dimension=dimension,
        persona_summaries=persona_summaries,
        dimension_state=dimension_state,
    )

    logger.info(
        "Compressed round %d for dimension %s: %d arguments -> %d persona summaries.",
        round_number,
        dimension.value,
        len(arguments),
        len(persona_summaries),
    )

    return round_summary


def serialize_round_summary(summary: RoundSummary) -> str:
    """Serialize a RoundSummary to a JSON string for LLM context injection.

    Used by the debate orchestrator to pass compressed prior-round context
    to persona prompts in subsequent rounds.
    """
    return summary.model_dump_json(indent=None)


def estimate_token_reduction(
    original_arguments: list[DebateArgument],
    compressed_summary: RoundSummary,
) -> float:
    """Estimate the token reduction ratio achieved by compression.

    Returns a float in [0.0, 1.0] representing the proportion of tokens saved.
    E.g., 0.90 means 90% reduction.
    """
    original_tokens = sum(
        _estimate_tokens(arg.model_dump_json()) for arg in original_arguments
    )
    compressed_tokens = _estimate_tokens(compressed_summary.model_dump_json())

    if original_tokens == 0:
        return 0.0

    return 1.0 - (compressed_tokens / original_tokens)


def _extract_key_claim(argument_text: str, max_length: int = 200) -> str:
    """Extract the first sentence or up to max_length chars of the argument."""
    # Try to find the first sentence boundary
    for sep in (". ", ".\n", "! ", "? "):
        idx = argument_text.find(sep)
        if 0 < idx < max_length:
            return argument_text[: idx + 1]

    # Fall back to truncation
    if len(argument_text) <= max_length:
        return argument_text
    return argument_text[:max_length].rstrip() + "..."


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token (GPT-family heuristic)."""
    return max(1, len(text) // 4)
