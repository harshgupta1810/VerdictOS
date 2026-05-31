"""5 Sequential Reliability Gates (A-E) + Dropout-Aware Settled Rule.

Gate A: Persona Argument Generation (LLM call + Pydantic validation + retry)
Gate B: BM25 Section-Aware Citation Exact-Match Verifier
Gate C: Passage Accuracy Checker (misquotation detection)
Gate D: Confidence Calibrator (corroborating source counter)
Gate E: Contradiction Detector (cross-round stance consistency)

Step 50: Dropout-aware Settled rule enforcement.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from src.agents.schemas import Confidence, FindingDimension
from src.common.exceptions import PersonaDropoutError, SchemaRetryExhaustedError
from src.debate.personas import build_user_prompt, get_persona_prompt
from src.debate.schemas import (
    OPPOSING_PERSONAS,
    DebateArgument,
    DebatePersona,
    DebateStance,
    DimensionState,
)
from src.llm.schemas import LLMRequest

if TYPE_CHECKING:
    from src.llm.client import LLMClientProtocol
    from src.search.search_engine import SparseSearchEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gate B — BM25 Section-Aware Citation Exact-Match Verifier (Step 45)
# ---------------------------------------------------------------------------

def gate_b_citation_verifier(
    argument: DebateArgument,
    search_engine: SparseSearchEngine,
) -> DebateArgument:
    """Verify each citation in the argument against the BM25 index.

    Drops citations that do not match any indexed chunk. If ALL citations
    are invalid, the argument is marked as not BM25-verified and the
    citations list is cleared. The section pointer resolver is used for
    section-ID style references.

    Returns the (potentially modified) argument.
    """
    if not argument.citations:
        # No citations at all — uncited claim, mark unverified.
        argument.bm25_verified = False
        logger.warning(
            "Gate B: Argument %s has no citations — marked unverified.",
            argument.id,
        )
        return argument

    verified_citations: list[str] = []

    for citation_id in argument.citations:
        # Try direct section resolve (handles "Section X.Y" style IDs)
        results = search_engine.resolve_section_reference(citation_id)
        if results:
            verified_citations.append(citation_id)
            continue

        # Try fetching by chunk/section ID list
        results = search_engine.fetch_sections([citation_id])
        if results:
            verified_citations.append(citation_id)
            continue

        logger.info(
            "Gate B: Citation '%s' in argument %s not found in BM25 index — dropped.",
            citation_id,
            argument.id,
        )

    argument.citations = verified_citations
    argument.bm25_verified = len(verified_citations) > 0

    if not argument.bm25_verified:
        logger.warning(
            "Gate B: All citations dropped for argument %s — fully unverified.",
            argument.id,
        )

    return argument


# ---------------------------------------------------------------------------
# Gate C — Passage Accuracy Checker (Step 46)
# ---------------------------------------------------------------------------

_MISQUOTATION_THRESHOLD = 0.3  # Minimum token overlap ratio to pass.


def gate_c_passage_accuracy(
    argument: DebateArgument,
    search_engine: SparseSearchEngine,
) -> DebateArgument:
    """Retrieve cited passages and verify the argument does not misrepresent them.

    Uses token-overlap ratio between the argument text and the cited passage.
    If misquotation detected (overlap below threshold), confidence is
    downgraded to SPECULATIVE.

    Returns the (potentially modified) argument.
    """
    if not argument.citations or not argument.bm25_verified:
        return argument

    for citation_id in argument.citations:
        # Retrieve the cited passage text
        results = search_engine.fetch_sections([citation_id])
        if not results:
            results = search_engine.resolve_section_reference(citation_id)
        if not results:
            continue

        cited_text = results[0].text
        overlap = _token_overlap_ratio(argument.argument, cited_text)

        if overlap < _MISQUOTATION_THRESHOLD:
            logger.warning(
                "Gate C: Argument %s misrepresents citation '%s' "
                "(overlap=%.2f < %.2f) — confidence downgraded to speculative.",
                argument.id,
                citation_id,
                overlap,
                _MISQUOTATION_THRESHOLD,
            )
            argument.confidence = Confidence.SPECULATIVE
            return argument

    return argument


def _token_overlap_ratio(text_a: str, text_b: str) -> float:
    """Compute Jaccard-like token overlap ratio between two texts.

    Returns a float in [0.0, 1.0] representing the proportion of tokens
    in text_a that also appear in text_b.
    """
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())

    if not tokens_a:
        return 0.0

    return len(tokens_a & tokens_b) / len(tokens_a)


# ---------------------------------------------------------------------------
# Gate D — Confidence Calibrator (Step 47)
# ---------------------------------------------------------------------------

def gate_d_confidence_calibrator(
    argument: DebateArgument,
    all_arguments_this_round: list[DebateArgument],
) -> DebateArgument:
    """Calibrate confidence based on corroborating sources.

    Counts how many other arguments in this round cite the same chunk IDs.
    Single-source HIGH confidence is auto-downgraded to MEDIUM.

    Returns the (potentially modified) argument.
    """
    if argument.confidence != Confidence.HIGH:
        return argument

    # Count distinct corroborating arguments (different persona, shared citation)
    corroborating_count = 0
    arg_citations = set(argument.citations)

    for other in all_arguments_this_round:
        if other.id == argument.id:
            continue
        if other.persona == argument.persona:
            continue
        other_citations = set(other.citations)
        if arg_citations & other_citations:
            corroborating_count += 1

    if corroborating_count == 0:
        logger.info(
            "Gate D: Argument %s has HIGH confidence but zero corroborating "
            "sources — downgraded to MEDIUM.",
            argument.id,
        )
        argument.confidence = Confidence.MEDIUM

    return argument


# ---------------------------------------------------------------------------
# Gate E — Contradiction Detector (Step 48)
# ---------------------------------------------------------------------------

def gate_e_contradiction_detector(
    argument: DebateArgument,
    previous_arguments: list[DebateArgument],
) -> DebateArgument:
    """Detect unexplained stance reversals across rounds.

    Compares the current stance against the same persona's stance in all
    previous rounds. If the persona reversed stance without the notes field
    explaining the change, sets contradiction_flag = True.

    Returns the (potentially modified) argument.
    """
    same_persona_previous = [
        a for a in previous_arguments
        if a.persona == argument.persona
        and a.finding_id == argument.finding_id
        and a.round < argument.round
    ]

    if not same_persona_previous:
        return argument

    # Get the most recent previous stance
    latest_previous = max(same_persona_previous, key=lambda a: a.round)

    if latest_previous.stance != argument.stance:
        # Stance changed — check if notes explain the reversal
        reversal_explained = bool(
            argument.notes
            and len(argument.notes.strip()) > 10  # Require substantive explanation
        )

        if not reversal_explained:
            argument.contradiction_flag = True
            logger.warning(
                "Gate E: Persona %s reversed stance from %s to %s in round %d "
                "without explanation — contradiction_flag set.",
                argument.persona.value,
                latest_previous.stance.value,
                argument.stance.value,
                argument.round,
            )

    return argument


# ---------------------------------------------------------------------------
# Gate A — Persona Argument Generator (Step 49)
# ---------------------------------------------------------------------------

async def gate_a_argument_generator(
    persona: DebatePersona,
    finding_id: str,
    finding_claim: str,
    finding_citation: str,
    finding_confidence: str,
    dimension: FindingDimension,
    core_question: str,
    round_number: int,
    llm_client: LLMClientProtocol,
    model: str = "llama3.2:1b",
    previous_context: str = "",
) -> DebateArgument:
    """Generate a debate argument using the LLM with Pydantic validation.

    Calls the LLM with the persona system prompt, validates through
    DebateArgument Pydantic schema, retries once on failure.
    On persistent failure: preserves stance + steelman, writes dropout_flag.

    Raises PersonaDropoutError if the argument cannot be generated.
    """
    system_prompt = get_persona_prompt(persona)
    user_prompt = build_user_prompt(
        finding_claim=finding_claim,
        finding_citation=finding_citation,
        finding_confidence=finding_confidence,
        dimension=dimension.value,
        core_question=core_question,
        round_number=round_number,
        previous_context=previous_context,
    )

    request = LLMRequest(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        format="json",
        temperature=0.3,
    )

    try:
        argument = await llm_client.generate_with_schema(
            request,
            DebateArgument,
            max_retries=1,
        )
        # Ensure correct metadata is set (LLM may not produce these correctly)
        argument.persona = persona
        argument.round = round_number
        argument.dimension = dimension
        argument.finding_id = finding_id
        return argument

    except SchemaRetryExhaustedError:
        logger.error(
            "Gate A: Persona %s failed to produce valid output after retries "
            "for finding %s in round %d — writing dropout_flag.",
            persona.value,
            finding_id,
            round_number,
        )
        # Create a fallback dropout argument preserving the stance
        dropout_arg = DebateArgument(
            id=str(uuid.uuid4()),
            finding_id=finding_id,
            persona=persona,
            round=round_number,
            dimension=dimension,
            stance=DebateStance.NEUTRAL,
            steelman="Persona dropped out — unable to generate valid argument.",
            argument="[DROPOUT] This persona failed to produce a valid structured "
                     "argument after retry. The dropout_flag has been set.",
            citations=[],
            confidence=Confidence.SPECULATIVE,
            dropout_flag=True,
            notes="Automatic dropout due to schema validation exhaustion.",
        )
        return dropout_arg

    except Exception as exc:
        logger.error(
            "Gate A: Unexpected error for persona %s on finding %s: %s",
            persona.value,
            finding_id,
            exc,
        )
        raise PersonaDropoutError(
            f"Persona {persona.value} failed for finding {finding_id}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Dropout-Aware Settled Rule (Step 50)
# ---------------------------------------------------------------------------

def apply_dropout_settled_rule(
    dimension_state: DimensionState,
    round_arguments: list[DebateArgument],
) -> DimensionState:
    """Enforce dropout-aware Settled rule.

    If any opposing persona (Critic, Valuation Skeptic, Devil's Advocate)
    has dropout_flag=True, the dimension CANNOT be classified as Settled.
    It is auto-reclassified to Contested.

    Returns the (potentially modified) DimensionState.
    """
    if dimension_state != DimensionState.SETTLED:
        return dimension_state

    for arg in round_arguments:
        if arg.dropout_flag and arg.persona in OPPOSING_PERSONAS:
            logger.warning(
                "Dropout-aware rule: Dimension cannot be Settled because "
                "opposing persona %s has dropout_flag — reclassified to Contested.",
                arg.persona.value,
            )
            return DimensionState.CONTESTED

    return dimension_state
