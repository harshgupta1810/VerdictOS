"""Unit tests for Steps 45–50 — Reliability Gates A–E and Dropout Rule."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from typing import Any

from src.agents.schemas import Confidence, FindingDimension
from src.common.exceptions import PersonaDropoutError, SchemaRetryExhaustedError
from src.debate.gates import (
    _token_overlap_ratio,
    apply_dropout_settled_rule,
    gate_a_argument_generator,
    gate_b_citation_verifier,
    gate_c_passage_accuracy,
    gate_d_confidence_calibrator,
    gate_e_contradiction_detector,
)
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState
from src.search.schemas import SearchResult
from src.common.models import ClauseType


def _make_arg(**overrides: object) -> DebateArgument:
    """Create a valid DebateArgument with optional overrides."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": "proponent",
        "round": 1,
        "dimension": "risk_exposure",
        "stance": "support",
        "steelman": "The opposing view has merit because of data quality.",
        "argument": "The risk is clearly documented in the contract clause.",
        "citations": ["chunk-1"],
        "confidence": "high",
    }
    base.update(overrides)
    return DebateArgument.model_validate(base)


def _make_search_result(chunk_id: str = "chunk-1", text: str = "sample text") -> SearchResult:
    """Create a mock SearchResult."""
    return SearchResult(
        chunk_id=chunk_id,
        score=1.0,
        document_name="test.pdf",
        text=text,
        section_id="Section 1",
        absolute_page=1,
        clause_type=ClauseType.GENERAL,
    )


def _mock_search_engine(
    resolve_returns: list[SearchResult] | None = None,
    fetch_returns: list[SearchResult] | None = None,
) -> MagicMock:
    """Create a mock SparseSearchEngine."""
    engine = MagicMock()
    engine.resolve_section_reference.return_value = resolve_returns or []
    engine.fetch_sections.return_value = fetch_returns or []
    return engine


# ---------------------------------------------------------------------------
# Step 45: Gate B — BM25 Citation Verifier
# ---------------------------------------------------------------------------

class TestGateBCitationVerifier:
    def test_valid_citation_passes(self) -> None:
        arg = _make_arg(citations=["chunk-1"])
        engine = _mock_search_engine(
            resolve_returns=[_make_search_result("chunk-1")]
        )
        result = gate_b_citation_verifier(arg, engine)
        assert result.bm25_verified is True
        assert result.citations == ["chunk-1"]

    def test_invalid_citation_dropped(self) -> None:
        arg = _make_arg(citations=["chunk-1", "chunk-invalid"])
        engine = _mock_search_engine()
        # Only chunk-1 found via fetch_sections
        engine.resolve_section_reference.return_value = []
        engine.fetch_sections.side_effect = lambda ids: (
            [_make_search_result("chunk-1")] if "chunk-1" in ids else []
        )
        result = gate_b_citation_verifier(arg, engine)
        assert result.bm25_verified is True
        assert "chunk-1" in result.citations
        assert "chunk-invalid" not in result.citations

    def test_all_citations_invalid_marks_unverified(self) -> None:
        arg = _make_arg(citations=["chunk-bad"])
        engine = _mock_search_engine()  # Empty returns
        result = gate_b_citation_verifier(arg, engine)
        assert result.bm25_verified is False
        assert result.citations == []

    def test_no_citations_marks_unverified(self) -> None:
        arg = _make_arg(citations=[])
        engine = _mock_search_engine()
        result = gate_b_citation_verifier(arg, engine)
        assert result.bm25_verified is False

    def test_section_reference_resolved(self) -> None:
        arg = _make_arg(citations=["Section 4.2"])
        engine = _mock_search_engine(
            resolve_returns=[_make_search_result("Section 4.2", "Section text")]
        )
        result = gate_b_citation_verifier(arg, engine)
        assert result.bm25_verified is True
        assert "Section 4.2" in result.citations


# ---------------------------------------------------------------------------
# Step 46: Gate C — Passage Accuracy Checker
# ---------------------------------------------------------------------------

class TestGateCPassageAccuracy:
    def test_accurate_argument_passes(self) -> None:
        # Argument text overlaps heavily with cited passage
        arg = _make_arg(
            argument="The risk is clearly documented in the contract clause about liability.",
            citations=["chunk-1"],
            bm25_verified=True,
            confidence="high",
        )
        engine = _mock_search_engine(
            fetch_returns=[_make_search_result(
                "chunk-1",
                "The risk is clearly documented in the contract clause about liability cap."
            )]
        )
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.HIGH  # Not downgraded

    def test_misquotation_downgrades_confidence(self) -> None:
        # Argument makes claims with very low overlap to the source text
        arg = _make_arg(
            argument="xyz abc totally different content here nothing matches",
            citations=["chunk-1"],
            bm25_verified=True,
            confidence="high",
        )
        engine = _mock_search_engine(
            fetch_returns=[_make_search_result(
                "chunk-1",
                "The company has maintained compliance with all regulatory requirements."
            )]
        )
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.SPECULATIVE

    def test_skips_when_not_bm25_verified(self) -> None:
        arg = _make_arg(bm25_verified=False, confidence="high")
        engine = _mock_search_engine()
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.HIGH  # Unchanged

    def test_skips_when_no_citations(self) -> None:
        arg = _make_arg(citations=[], bm25_verified=True, confidence="high")
        engine = _mock_search_engine()
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.HIGH

    def test_passage_resolved_via_section_reference(self) -> None:
        arg = _make_arg(
            argument="The risk is clearly documented in the contract clause.",
            citations=["Section 4.2"],
            bm25_verified=True,
            confidence="high",
        )
        engine = _mock_search_engine(
            fetch_returns=[],  # fetch fails
            resolve_returns=[_make_search_result("Section 4.2", "The risk is clearly documented in the contract clause.")]
        )
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.HIGH

    def test_passage_not_found_skips_citation(self) -> None:
        arg = _make_arg(
            argument="The risk is clearly documented in the contract clause.",
            citations=["chunk-1"],
            bm25_verified=True,
            confidence="high",
        )
        engine = _mock_search_engine(
            fetch_returns=[],
            resolve_returns=[]
        )
        result = gate_c_passage_accuracy(arg, engine)
        assert result.confidence == Confidence.HIGH


class TestTokenOverlapRatio:
    def test_identical_strings(self) -> None:
        assert _token_overlap_ratio("hello world", "hello world") == 1.0

    def test_no_overlap(self) -> None:
        assert _token_overlap_ratio("abc def", "xyz uvw") == 0.0

    def test_partial_overlap(self) -> None:
        ratio = _token_overlap_ratio("hello world foo", "hello world bar")
        assert 0.5 < ratio < 1.0

    def test_empty_text_a(self) -> None:
        assert _token_overlap_ratio("", "some text") == 0.0


# ---------------------------------------------------------------------------
# Step 47: Gate D — Confidence Calibrator
# ---------------------------------------------------------------------------

class TestGateDConfidenceCalibrator:
    def test_single_source_high_downgraded_to_medium(self) -> None:
        arg = _make_arg(id="arg-1", citations=["chunk-1"], confidence="high")
        # No other arguments cite the same chunk
        others = [
            _make_arg(id="arg-2", persona="critic", citations=["chunk-2"]),
        ]
        result = gate_d_confidence_calibrator(arg, [arg] + others)
        assert result.confidence == Confidence.MEDIUM

    def test_corroborated_high_stays_high(self) -> None:
        arg = _make_arg(id="arg-1", persona="proponent", citations=["chunk-1"], confidence="high")
        corroborator = _make_arg(id="arg-2", persona="critic", citations=["chunk-1"], confidence="medium")
        result = gate_d_confidence_calibrator(arg, [arg, corroborator])
        assert result.confidence == Confidence.HIGH

    def test_medium_confidence_not_affected(self) -> None:
        arg = _make_arg(confidence="medium")
        result = gate_d_confidence_calibrator(arg, [arg])
        assert result.confidence == Confidence.MEDIUM

    def test_same_persona_not_counted_as_corroboration(self) -> None:
        arg = _make_arg(id="arg-1", persona="proponent", citations=["chunk-1"], confidence="high")
        same_persona = _make_arg(id="arg-2", persona="proponent", citations=["chunk-1"], confidence="high")
        result = gate_d_confidence_calibrator(arg, [arg, same_persona])
        assert result.confidence == Confidence.MEDIUM  # Same persona doesn't count


# ---------------------------------------------------------------------------
# Step 48: Gate E — Contradiction Detector
# ---------------------------------------------------------------------------

class TestGateEContradictionDetector:
    def test_no_previous_rounds_no_contradiction(self) -> None:
        arg = _make_arg(round=1)
        result = gate_e_contradiction_detector(arg, [])
        assert result.contradiction_flag is False

    def test_consistent_stance_no_contradiction(self) -> None:
        prev = _make_arg(
            id="prev-1", persona="proponent", round=1,
            stance="support", finding_id="finding-1",
        )
        current = _make_arg(
            id="cur-1", persona="proponent", round=2,
            stance="support", finding_id="finding-1",
        )
        result = gate_e_contradiction_detector(current, [prev])
        assert result.contradiction_flag is False

    def test_unexplained_reversal_sets_flag(self) -> None:
        prev = _make_arg(
            id="prev-1", persona="proponent", round=1,
            stance="support", finding_id="finding-1",
        )
        current = _make_arg(
            id="cur-1", persona="proponent", round=2,
            stance="oppose", finding_id="finding-1",
            notes="",
        )
        result = gate_e_contradiction_detector(current, [prev])
        assert result.contradiction_flag is True

    def test_explained_reversal_no_flag(self) -> None:
        prev = _make_arg(
            id="prev-1", persona="proponent", round=1,
            stance="support", finding_id="finding-1",
        )
        current = _make_arg(
            id="cur-1", persona="proponent", round=2,
            stance="oppose", finding_id="finding-1",
            notes="New evidence from Section 7 changes my position significantly.",
        )
        result = gate_e_contradiction_detector(current, [prev])
        assert result.contradiction_flag is False

    def test_different_persona_ignored(self) -> None:
        prev_critic = _make_arg(
            id="prev-1", persona="critic", round=1,
            stance="oppose", finding_id="finding-1",
        )
        current_proponent = _make_arg(
            id="cur-1", persona="proponent", round=2,
            stance="support", finding_id="finding-1",
        )
        result = gate_e_contradiction_detector(current_proponent, [prev_critic])
        assert result.contradiction_flag is False

    def test_different_finding_ignored(self) -> None:
        prev = _make_arg(
            id="prev-1", persona="proponent", round=1,
            stance="support", finding_id="finding-1",
        )
        current = _make_arg(
            id="cur-1", persona="proponent", round=2,
            stance="oppose", finding_id="finding-2",
        )
        result = gate_e_contradiction_detector(current, [prev])
        assert result.contradiction_flag is False


# ---------------------------------------------------------------------------
# Step 49: Gate A — Persona Argument Generator
# ---------------------------------------------------------------------------

class TestGateAArgumentGenerator:
    @pytest.mark.asyncio
    async def test_successful_generation(self) -> None:
        mock_client = AsyncMock()
        expected_arg = _make_arg(persona="proponent")
        mock_client.generate_with_schema.return_value = expected_arg

        result = await gate_a_argument_generator(
            persona=DebatePersona.PROPONENT,
            finding_id="finding-1",
            finding_claim="Risk identified",
            finding_citation="Section 4.2",
            finding_confidence="high",
            dimension=FindingDimension.RISK_EXPOSURE,
            core_question="How severe?",
            round_number=1,
            llm_client=mock_client,
        )

        assert result.persona == DebatePersona.PROPONENT
        assert result.dropout_flag is False
        mock_client.generate_with_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_retry_exhausted_produces_dropout(self) -> None:
        mock_client = AsyncMock()
        mock_client.generate_with_schema.side_effect = SchemaRetryExhaustedError("Failed")

        result = await gate_a_argument_generator(
            persona=DebatePersona.CRITIC,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            dimension=FindingDimension.RISK_EXPOSURE,
            core_question="How severe?",
            round_number=1,
            llm_client=mock_client,
        )

        assert result.dropout_flag is True
        assert result.persona == DebatePersona.CRITIC
        assert result.stance == DebateStance.NEUTRAL
        assert "DROPOUT" in result.argument

    @pytest.mark.asyncio
    async def test_unexpected_error_raises_persona_dropout(self) -> None:
        mock_client = AsyncMock()
        mock_client.generate_with_schema.side_effect = RuntimeError("Network down")

        with pytest.raises(PersonaDropoutError):
            await gate_a_argument_generator(
                persona=DebatePersona.PROPONENT,
                finding_id="finding-1",
                finding_claim="Risk",
                finding_citation="Section 1",
                finding_confidence="medium",
                dimension=FindingDimension.RISK_EXPOSURE,
                core_question="Q?",
                round_number=1,
                llm_client=mock_client,
            )

    @pytest.mark.asyncio
    async def test_uses_correct_model(self) -> None:
        mock_client = AsyncMock()
        mock_client.generate_with_schema.return_value = _make_arg()

        await gate_a_argument_generator(
            persona=DebatePersona.PROPONENT,
            finding_id="finding-1",
            finding_claim="Risk",
            finding_citation="Section 1",
            finding_confidence="medium",
            dimension=FindingDimension.RISK_EXPOSURE,
            core_question="Q?",
            round_number=1,
            llm_client=mock_client,
            model="llama3.2:1b",
        )

        call_args = mock_client.generate_with_schema.call_args
        request = call_args[0][0]
        assert request.model == "llama3.2:1b"


# ---------------------------------------------------------------------------
# Step 50: Dropout-Aware Settled Rule
# ---------------------------------------------------------------------------

class TestDropoutAwareSettledRule:
    def test_settled_with_no_dropout_stays_settled(self) -> None:
        args = [_make_arg(persona="critic", dropout_flag=False)]
        result = apply_dropout_settled_rule(DimensionState.SETTLED, args)
        assert result == DimensionState.SETTLED

    def test_settled_with_critic_dropout_reclassified(self) -> None:
        args = [_make_arg(persona="critic", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.SETTLED, args)
        assert result == DimensionState.CONTESTED

    def test_settled_with_devils_advocate_dropout_reclassified(self) -> None:
        args = [_make_arg(persona="devils_advocate", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.SETTLED, args)
        assert result == DimensionState.CONTESTED

    def test_settled_with_valuation_skeptic_dropout_reclassified(self) -> None:
        args = [_make_arg(persona="valuation_skeptic", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.SETTLED, args)
        assert result == DimensionState.CONTESTED

    def test_settled_with_proponent_dropout_stays_settled(self) -> None:
        # Proponent is NOT an opposing persona
        args = [_make_arg(persona="proponent", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.SETTLED, args)
        assert result == DimensionState.SETTLED

    def test_active_state_not_affected(self) -> None:
        args = [_make_arg(persona="critic", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.ACTIVE, args)
        assert result == DimensionState.ACTIVE

    def test_contested_state_not_affected(self) -> None:
        args = [_make_arg(persona="critic", dropout_flag=True)]
        result = apply_dropout_settled_rule(DimensionState.CONTESTED, args)
        assert result == DimensionState.CONTESTED
