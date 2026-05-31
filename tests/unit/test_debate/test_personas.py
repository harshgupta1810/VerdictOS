"""Unit tests for Step 44 — Debate Persona System Prompts."""

from __future__ import annotations

import pytest

from src.debate.personas import (
    PERSONA_SYSTEM_PROMPTS,
    build_user_prompt,
    get_persona_prompt,
)
from src.debate.schemas import DebatePersona


class TestPersonaPrompts:
    """Verify all 6 persona prompts are defined and structurally correct."""

    def test_all_six_personas_have_prompts(self) -> None:
        assert len(PERSONA_SYSTEM_PROMPTS) == 6
        for persona in DebatePersona:
            assert persona in PERSONA_SYSTEM_PROMPTS

    @pytest.mark.parametrize("persona", list(DebatePersona))
    def test_prompt_contains_steelman_instruction(self, persona: DebatePersona) -> None:
        prompt = get_persona_prompt(persona)
        assert "STEELMAN" in prompt.upper()
        assert "steelman" in prompt.lower()

    @pytest.mark.parametrize("persona", list(DebatePersona))
    def test_prompt_contains_json_format(self, persona: DebatePersona) -> None:
        prompt = get_persona_prompt(persona)
        assert "JSON" in prompt
        assert '"stance"' in prompt
        assert '"steelman"' in prompt
        assert '"argument"' in prompt
        assert '"citations"' in prompt

    @pytest.mark.parametrize("persona", list(DebatePersona))
    def test_prompt_enforces_citation_requirement(self, persona: DebatePersona) -> None:
        prompt = get_persona_prompt(persona)
        assert "cite" in prompt.lower() or "citation" in prompt.lower()

    def test_proponent_argues_in_favor(self) -> None:
        prompt = get_persona_prompt(DebatePersona.PROPONENT)
        assert "IN FAVOR" in prompt or "favor" in prompt.lower()

    def test_critic_challenges_evidence(self) -> None:
        prompt = get_persona_prompt(DebatePersona.CRITIC)
        assert "CHALLENGE" in prompt or "challenge" in prompt.lower()

    def test_devils_advocate_is_contrarian(self) -> None:
        prompt = get_persona_prompt(DebatePersona.DEVILS_ADVOCATE)
        assert "CONTRARIAN" in prompt or "contrarian" in prompt.lower()

    def test_valuation_skeptic_questions_financials(self) -> None:
        prompt = get_persona_prompt(DebatePersona.VALUATION_SKEPTIC)
        assert "QUESTION" in prompt or "valuation" in prompt.lower()

    def test_integration_realist_focuses_on_post_merger(self) -> None:
        prompt = get_persona_prompt(DebatePersona.INTEGRATION_REALIST)
        assert "POST-MERGER" in prompt or "integration" in prompt.lower()

    def test_regulators_eye_evaluates_compliance(self) -> None:
        prompt = get_persona_prompt(DebatePersona.REGULATORS_EYE)
        assert "REGULATORY" in prompt or "compliance" in prompt.lower()

    def test_get_persona_prompt_raises_on_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_persona_prompt("nonexistent_persona")  # type: ignore[arg-type]


class TestBuildUserPrompt:
    """Verify the user prompt builder produces expected structure."""

    def test_basic_prompt_structure(self) -> None:
        prompt = build_user_prompt(
            finding_claim="IP assignment clause is vague",
            finding_citation="Section 4.2: 'all intellectual property...'",
            finding_confidence="high",
            dimension="risk_exposure",
            core_question="How severe are the risks?",
            round_number=1,
        )
        assert "risk_exposure" in prompt
        assert "How severe are the risks?" in prompt
        assert "ROUND: 1" in prompt
        assert "IP assignment clause is vague" in prompt
        assert "Section 4.2" in prompt

    def test_prompt_includes_previous_context(self) -> None:
        prompt = build_user_prompt(
            finding_claim="Tax exposure",
            finding_citation="Section 7",
            finding_confidence="medium",
            dimension="valuation_fairness",
            core_question="Is the price justified?",
            round_number=2,
            previous_context="Round 1 summary: Proponent supported, Critic opposed.",
        )
        assert "PREVIOUS ROUND CONTEXT" in prompt
        assert "Round 1 summary" in prompt

    def test_prompt_omits_context_when_empty(self) -> None:
        prompt = build_user_prompt(
            finding_claim="Claim",
            finding_citation="Citation",
            finding_confidence="medium",
            dimension="risk_exposure",
            core_question="Q?",
            round_number=1,
        )
        assert "PREVIOUS ROUND CONTEXT" not in prompt
