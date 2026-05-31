"""Unit tests for Step 52 — Context Compressor."""

from __future__ import annotations

import uuid

import pytest

from typing import Any

from src.agents.schemas import Confidence, FindingDimension
from src.debate.compressor import (
    _estimate_tokens,
    _extract_key_claim,
    compress_round_context,
    estimate_token_reduction,
    serialize_round_summary,
)
from src.debate.schemas import (
    DebateArgument,
    DebatePersona,
    DebateStance,
    DimensionState,
)


def _make_arg(
    persona: str = "proponent",
    argument: str = "This is a very long and detailed argument about the risk. " * 20,
    notes: str = "Important verbatim note that must be preserved exactly.",
    **overrides: object,
) -> DebateArgument:
    """Create a verbose DebateArgument for compression testing."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": persona,
        "round": 1,
        "dimension": "risk_exposure",
        "stance": "support",
        "steelman": "The opposing view is reasonable because of data quality issues. " * 5,
        "argument": argument,
        "citations": ["chunk-1", "chunk-2", "chunk-3"],
        "confidence": "high",
        "notes": notes,
    }
    base.update(overrides)
    return DebateArgument.model_validate(base)


class TestCompressRoundContext:
    def test_produces_valid_round_summary(self) -> None:
        args = [
            _make_arg(persona="proponent"),
            _make_arg(persona="critic", stance="oppose"),
            _make_arg(persona="devils_advocate", stance="oppose"),
        ]
        summary = compress_round_context(args, round_number=1)
        assert summary.round_number == 1
        assert summary.dimension == FindingDimension.RISK_EXPOSURE
        assert len(summary.persona_summaries) == 3

    def test_notes_preserved_verbatim(self) -> None:
        original_notes = "Exact verbatim text: special chars !@#$% and numbers 12345."
        args = [_make_arg(notes=original_notes)]
        summary = compress_round_context(args, round_number=1)
        assert summary.persona_summaries[0].notes == original_notes

    def test_key_claim_truncated(self) -> None:
        long_arg = "A" * 500
        args = [_make_arg(argument=long_arg)]
        summary = compress_round_context(args, round_number=1)
        assert len(summary.persona_summaries[0].key_claim) <= 203  # 200 + "..."

    def test_stance_preserved(self) -> None:
        args = [_make_arg(stance="oppose")]
        summary = compress_round_context(args, round_number=1)
        assert summary.persona_summaries[0].stance == DebateStance.OPPOSE

    def test_dimension_state_passed_through(self) -> None:
        args = [_make_arg()]
        summary = compress_round_context(
            args, round_number=2, dimension_state=DimensionState.CONTESTED
        )
        assert summary.dimension_state == DimensionState.CONTESTED

    def test_dropout_flag_preserved(self) -> None:
        args = [_make_arg(dropout_flag=True)]
        summary = compress_round_context(args, round_number=1)
        assert summary.persona_summaries[0].dropout_flag is True

    def test_contradiction_flag_preserved(self) -> None:
        args = [_make_arg(contradiction_flag=True)]
        summary = compress_round_context(args, round_number=1)
        assert summary.persona_summaries[0].contradiction_flag is True


class TestTokenReduction:
    def test_achieves_significant_reduction(self) -> None:
        # Create verbose arguments
        args = [
            _make_arg(persona="proponent"),
            _make_arg(persona="critic", stance="oppose"),
            _make_arg(persona="devils_advocate", stance="oppose"),
            _make_arg(persona="valuation_skeptic", stance="oppose"),
            _make_arg(persona="integration_realist", stance="neutral"),
            _make_arg(persona="regulators_eye", stance="oppose"),
        ]
        summary = compress_round_context(args, round_number=1)
        reduction = estimate_token_reduction(args, summary)
        # Should achieve at least 50% reduction on verbose arguments
        assert reduction >= 0.5, f"Token reduction was only {reduction:.1%}"

    def test_empty_arguments_zero_reduction(self) -> None:
        # Edge case: single tiny argument won't compress much
        args = [_make_arg(argument="Short.", notes="")]
        summary = compress_round_context(args, round_number=1)
        reduction = estimate_token_reduction(args, summary)
        assert 0.0 <= reduction <= 1.0


class TestSerializeRoundSummary:
    def test_produces_valid_json(self) -> None:
        args = [_make_arg()]
        summary = compress_round_context(args, round_number=1)
        json_str = serialize_round_summary(summary)
        import json
        parsed = json.loads(json_str)
        assert parsed["round_number"] == 1
        assert len(parsed["persona_summaries"]) == 1


class TestExtractKeyClaim:
    def test_extracts_first_sentence(self) -> None:
        text = "This is the key claim. And this is more detail."
        result = _extract_key_claim(text)
        assert result == "This is the key claim."

    def test_truncates_long_text(self) -> None:
        text = "A" * 500
        result = _extract_key_claim(text)
        assert len(result) <= 203

    def test_short_text_unchanged(self) -> None:
        text = "Short claim."
        result = _extract_key_claim(text)
        assert result == "Short claim."


class TestEstimateTokens:
    def test_nonzero_for_any_text(self) -> None:
        assert _estimate_tokens("hello") >= 1
        assert _estimate_tokens("") >= 1

    def test_scales_with_length(self) -> None:
        assert _estimate_tokens("a" * 400) > _estimate_tokens("a" * 40)
