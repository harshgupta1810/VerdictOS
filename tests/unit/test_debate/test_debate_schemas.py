"""Unit tests for Step 43 — Debate Argument Pydantic V2 Schema."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from typing import Any, cast

from src.agents.schemas import Confidence, FindingDimension
from src.debate.schemas import (
    OPPOSING_PERSONAS,
    DebateArgument,
    DebatePersona,
    DebateStance,
    DimensionState,
    PersonaRoundSummary,
    RoundSummary,
)


def _make_argument(**overrides: object) -> dict:
    """Return a valid DebateArgument dict with optional overrides."""
    base: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "finding_id": "finding-1",
        "persona": "proponent",
        "round": 1,
        "dimension": "risk_exposure",
        "stance": "support",
        "steelman": "The opposing view has merit because...",
        "argument": "This finding clearly shows risk.",
        "citations": ["chunk-1"],
        "confidence": "high",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------

class TestDebatePersonaEnum:
    def test_all_six_personas_defined(self) -> None:
        assert len(DebatePersona) == 6

    def test_persona_values(self) -> None:
        assert DebatePersona.PROPONENT.value == "proponent"
        assert DebatePersona.CRITIC.value == "critic"
        assert DebatePersona.DEVILS_ADVOCATE.value == "devils_advocate"
        assert DebatePersona.VALUATION_SKEPTIC.value == "valuation_skeptic"
        assert DebatePersona.INTEGRATION_REALIST.value == "integration_realist"
        assert DebatePersona.REGULATORS_EYE.value == "regulators_eye"


class TestDebateStanceEnum:
    def test_all_stances(self) -> None:
        assert len(DebateStance) == 3
        assert set(s.value for s in DebateStance) == {"support", "oppose", "neutral"}


class TestDimensionStateEnum:
    def test_all_states(self) -> None:
        assert len(DimensionState) == 4
        assert set(s.value for s in DimensionState) == {
            "active", "settled", "contested", "unresolved"
        }


class TestOpposingPersonas:
    def test_contains_critic_skeptic_advocate(self) -> None:
        assert DebatePersona.CRITIC in OPPOSING_PERSONAS
        assert DebatePersona.VALUATION_SKEPTIC in OPPOSING_PERSONAS
        assert DebatePersona.DEVILS_ADVOCATE in OPPOSING_PERSONAS
        assert DebatePersona.PROPONENT not in OPPOSING_PERSONAS


# ---------------------------------------------------------------------------
# DebateArgument schema validation
# ---------------------------------------------------------------------------

class TestDebateArgument:
    def test_valid_argument(self) -> None:
        arg = DebateArgument.model_validate(_make_argument())
        assert arg.persona == DebatePersona.PROPONENT
        assert arg.stance == DebateStance.SUPPORT
        assert arg.dimension == FindingDimension.RISK_EXPOSURE
        assert arg.confidence == Confidence.HIGH
        assert arg.bm25_verified is False
        assert arg.contradiction_flag is False
        assert arg.dropout_flag is False

    def test_steelman_mandatory_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="[Ss]teelman"):
            DebateArgument.model_validate(_make_argument(steelman=""))

    def test_steelman_mandatory_rejects_whitespace(self) -> None:
        with pytest.raises(ValidationError, match="[Ss]teelman"):
            DebateArgument.model_validate(_make_argument(steelman="   "))

    def test_steelman_mandatory_rejects_missing(self) -> None:
        data = _make_argument()
        del data["steelman"]
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(data)

    def test_round_clamped_1_to_3(self) -> None:
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(_make_argument(round=0))
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(_make_argument(round=4))

    def test_float_confidence_coercion(self) -> None:
        arg_high = DebateArgument.model_validate(_make_argument(confidence=0.85))
        assert arg_high.confidence == Confidence.HIGH

        arg_med = DebateArgument.model_validate(_make_argument(confidence=0.55))
        assert arg_med.confidence == Confidence.MEDIUM

        arg_spec = DebateArgument.model_validate(_make_argument(confidence=0.3))
        assert arg_spec.confidence == Confidence.SPECULATIVE

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            DebateArgument.model_validate(_make_argument(confidence=1.5))

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(_make_argument(unknown_field="x"))

    def test_invalid_persona_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(_make_argument(persona="judge"))

    def test_invalid_stance_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DebateArgument.model_validate(_make_argument(stance="maybe"))

    def test_all_fields_present_in_output(self) -> None:
        arg = DebateArgument.model_validate(_make_argument())
        dumped = arg.model_dump()
        expected_keys = {
            "id", "finding_id", "persona", "round", "dimension",
            "stance", "steelman", "argument", "citations", "confidence",
            "contradiction_flag", "bm25_verified", "dropout_flag",
            "notes", "timestamp",
        }
        assert expected_keys == set(dumped.keys())


# ---------------------------------------------------------------------------
# RoundSummary & PersonaRoundSummary
# ---------------------------------------------------------------------------

class TestRoundSummary:
    def test_valid_round_summary(self) -> None:
        summary = RoundSummary(
            round_number=1,
            dimension=FindingDimension.RISK_EXPOSURE,
            persona_summaries=[
                PersonaRoundSummary(
                    persona=DebatePersona.PROPONENT,
                    stance=DebateStance.SUPPORT,
                    key_claim="Risk is real",
                    notes="verbatim note",
                )
            ],
            dimension_state=DimensionState.ACTIVE,
        )
        assert summary.round_number == 1
        assert len(summary.persona_summaries) == 1
        assert summary.persona_summaries[0].notes == "verbatim note"

    def test_round_summary_rejects_round_zero(self) -> None:
        with pytest.raises(ValidationError):
            RoundSummary(
                round_number=cast(int, 0),
                dimension=FindingDimension.RISK_EXPOSURE,
            )
