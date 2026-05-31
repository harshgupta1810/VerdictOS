"""Pydantic V2 schemas for the Adversarial Debate Engine (Phase 4).

Enforces data contracts for debate inputs, outputs, persona responses,
and the Steelman Rule validation constraint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agents.schemas import Confidence, FindingDimension


class DebatePersona(str, Enum):
    """The 6 adversarial debate personas."""

    PROPONENT = "proponent"
    CRITIC = "critic"
    DEVILS_ADVOCATE = "devils_advocate"
    VALUATION_SKEPTIC = "valuation_skeptic"
    INTEGRATION_REALIST = "integration_realist"
    REGULATORS_EYE = "regulators_eye"


# Personas whose dropout invalidates a Settled classification.
OPPOSING_PERSONAS: frozenset[DebatePersona] = frozenset({
    DebatePersona.CRITIC,
    DebatePersona.VALUATION_SKEPTIC,
    DebatePersona.DEVILS_ADVOCATE,
})


class DebateStance(str, Enum):
    """Possible stances a persona can take on a finding."""

    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"


class DimensionState(str, Enum):
    """Lifecycle states for a debate dimension across rounds."""

    ACTIVE = "active"
    SETTLED = "settled"
    CONTESTED = "contested"
    UNRESOLVED = "unresolved"


class DebateArgument(BaseModel):
    """Structured argument produced by a debate persona in a single round.

    Steelman rule: every argument MUST include a steelman of the
    opposing position.  The model_validator enforces this.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    finding_id: str = Field(min_length=1)
    persona: DebatePersona
    round: int = Field(ge=1, le=3)
    dimension: FindingDimension
    stance: DebateStance
    steelman: str = Field(min_length=1)
    argument: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    contradiction_flag: bool = False
    bm25_verified: bool = False
    dropout_flag: bool = False
    notes: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def enforce_steelman_rule(cls, data: Any) -> Any:
        """Reject arguments that omit the steelman field."""
        if isinstance(data, dict):
            steelman = data.get("steelman", "")
            if not steelman or (isinstance(steelman, str) and not steelman.strip()):
                raise ValueError(
                    "Steelman field is mandatory — every debate argument must "
                    "include a steelman of the opposing position."
                )
        return data

    @model_validator(mode="before")
    @classmethod
    def coerce_confidence(cls, data: Any) -> Any:
        """Convert float confidence to categorical (mirrors Finding coercion)."""
        if isinstance(data, dict) and "confidence" in data:
            conf = data["confidence"]
            if isinstance(conf, (int, float)):
                if not (0.0 <= conf <= 1.0):
                    raise ValueError("confidence must be between 0.0 and 1.0")
                if conf >= 0.8:
                    data["confidence"] = "high"
                elif conf >= 0.5:
                    data["confidence"] = "medium"
                else:
                    data["confidence"] = "speculative"
        return data


class RoundSummary(BaseModel):
    """Compressed summary of a single debate round for context window management."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(ge=1, le=3)
    dimension: FindingDimension
    persona_summaries: list[PersonaRoundSummary] = Field(default_factory=list)
    dimension_state: DimensionState = DimensionState.ACTIVE


class PersonaRoundSummary(BaseModel):
    """Per-persona compressed summary preserving notes verbatim."""

    model_config = ConfigDict(extra="forbid")

    persona: DebatePersona
    stance: DebateStance
    key_claim: str = ""
    citation_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    contradiction_flag: bool = False
    dropout_flag: bool = False
    notes: str = ""  # Preserved verbatim from original argument.


# Rebuild RoundSummary to resolve forward reference to PersonaRoundSummary.
RoundSummary.model_rebuild()
