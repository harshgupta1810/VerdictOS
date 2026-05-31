"""Judge Agent (Phase 6: Context-Filtered Synthesis).

Processes only Contested/Unresolved findings, synthesizes final
verdicts, and appends calibrated confidence indexes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.agents.schemas import (
    Finding,
    JudgeSynthesisResult,
    JudgeVerdictStatus,
)
from src.debate.schemas import DebateArgument, DimensionState
from src.debate.aggregation import CONFIDENCE_WEIGHTS
from src.llm.schemas import LLMRequest
from src.search.schemas import SearchQuery, SearchFilters

if TYPE_CHECKING:
    from src.llm.client import LLMClientProtocol
    from src.search.search_engine import SparseSearchEngine

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM_PROMPT = """\
You are the Chief Due Diligence Judge. Your task is to resolve contested or unresolved findings from M&A due diligence.

You will be provided with:
1. The original finding claim and its citation.
2. Filtered debate arguments from various personas.
3. The finding's current state.

You MUST produce ONLY a single valid JSON object representing your final verdict.
Required JSON structure:
{
  "finding_id": "<the finding ID>",
  "status": "<confirmed | evidence_not_found | overridden>",
  "judge_override_flag": <true|false>,
  "synthesis_rationale": "<your detailed reasoning for the final verdict>"
}

RULES:
- If you disagree with the implicit consensus or find the debate lacking, set judge_override_flag to true.
- Explain your reasoning clearly in synthesis_rationale.
- Output ONLY valid JSON — no markdown, no explanation, no preamble.
"""

class _JudgeLLMOutput(JudgeSynthesisResult):
    """Wrapper for LLM output matching JudgeSynthesisResult."""
    pass


class JudgeAgent:
    """Phase 6: Judge Synthesis Agent."""

    def __init__(
        self,
        search_engine: SparseSearchEngine,
        llm_client: LLMClientProtocol,
    ) -> None:
        self._search_engine = search_engine
        self._llm_client = llm_client

    async def synthesize(
        self,
        finding: Finding,
        arguments: list[DebateArgument],
        state: DimensionState,
    ) -> JudgeSynthesisResult:
        """Run Phase 6 Judge synthesis on a single finding."""
        if state == DimensionState.SETTLED:
            # Settled findings are excluded from judge context. This shouldn't be called,
            # but we return a default confirmed if it is.
            return JudgeSynthesisResult(
                finding_id=finding.id,
                status=JudgeVerdictStatus.CONFIRMED,
                synthesis_rationale="Finding was already SETTLED.",
            )

        # 1. Context Filter
        # Remove dropout arguments
        filtered_args = [arg for arg in arguments if not arg.dropout_flag]
        
        # Calculate calibrated confidence score
        valid_confidences = [
            CONFIDENCE_WEIGHTS.get(arg.confidence, 0.5)
            for arg in filtered_args
        ]
        calibrated_score = (
            sum(valid_confidences) / len(valid_confidences)
            if valid_confidences else 0.5
        )

        # 2. Exact Match BM25 Pass for UNRESOLVED
        if state == DimensionState.UNRESOLVED:
            # Section-aware pass, let's use the finding's section_id if possible
            # We construct a query searching for the exact citation or claim text
            query_text = finding.citation if finding.citation else finding.claim
            query = SearchQuery(
                text=query_text,
                size=5,
                filters=SearchFilters(
                    clause_types=[finding.clause_type]
                )
            )
            # Add section reference search format if available
            if finding.section_id:
                 query.text = f"{finding.section_id} {query_text}"

            results = self._search_engine.search(query)
            if not results:
                # evidence not found label — never infer
                return JudgeSynthesisResult(
                    finding_id=finding.id,
                    status=JudgeVerdictStatus.EVIDENCE_NOT_FOUND,
                    judge_override_flag=False,
                    synthesis_rationale="Evidence not found during final exact-match pass.",
                    calibrated_confidence=calibrated_score,
                )

        # 3. LLM Synthesis
        args_context = []
        for arg in filtered_args:
            args_context.append(
                f"Persona: {arg.persona.value} | Stance: {arg.stance.value}\n"
                f"Contradiction: {arg.contradiction_flag}\n"
                f"Argument: {arg.argument}"
            )
        
        user_prompt = (
            f"FINDING ID: {finding.id}\n"
            f"CLAIM: {finding.claim}\n"
            f"CITATION: {finding.citation}\n"
            f"STATE: {state.value}\n\n"
            "FILTERED DEBATE ARGUMENTS:\n"
            + "\n---\n".join(args_context)
        )

        request = LLMRequest(
            model="llama3.1:1b",
            system_prompt=_JUDGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        try:
            output = await self._llm_client.generate_with_schema(
                request, _JudgeLLMOutput
            )
            # Ensure the output matches our context
            output.finding_id = finding.id
            output.calibrated_confidence = calibrated_score
            return output
        except Exception as exc:
            logger.error("Judge LLM failed for finding %s: %s", finding.id, exc)
            return JudgeSynthesisResult(
                finding_id=finding.id,
                status=JudgeVerdictStatus.OVERRIDDEN,
                judge_override_flag=True,
                synthesis_rationale=f"LLM failure: {exc}",
                calibrated_confidence=calibrated_score,
            )
