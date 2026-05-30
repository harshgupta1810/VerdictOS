"""Parallel Dispatcher for specialist agent execution.

Runs all activated specialist agents concurrently via asyncio.gather()
with semaphore throttling. Individual agent failures are captured
per-agent and do not crash the entire dispatch.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Sequence

from src.agents.schemas import AgentAnalysisResult, DispatchResult, Finding
from src.agents.specialist_agent import create_specialist_agents

if TYPE_CHECKING:
    from src.agents.base_agent import BaseSpecialistAgent
    from src.llm.client import LLMClientProtocol
    from src.preflight import PreflightResult
    from src.search.search_engine import SparseSearchEngine

logger = logging.getLogger(__name__)


class ParallelDispatcher:
    """Run specialist agents in parallel with concurrency control.

    All activated agents execute concurrently via ``asyncio.gather()``.
    A ``Semaphore`` throttles simultaneous LLM calls to avoid
    overwhelming the local Ollama instance.
    """

    def __init__(
        self,
        agents: Sequence[BaseSpecialistAgent],
        *,
        max_concurrency: int = 16,
    ) -> None:
        self._agents = agents
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def dispatch(self, document_name: str | None = None) -> DispatchResult:
        """Run all agents in parallel and aggregate results.

        Individual agent failures are captured in their respective
        ``AgentAnalysisResult.error`` field — they do not propagate.
        """

        start_ms = _now_ms()

        async def _guarded_analyze(agent: BaseSpecialistAgent) -> AgentAnalysisResult:
            async with self._semaphore:
                try:
                    return await agent.analyze(document_name)
                except Exception as exc:
                    logger.error(
                        "Unexpected error in agent %s: %s",
                        agent.agent_name.value,
                        exc,
                    )
                    return AgentAnalysisResult(
                        agent_name=agent.agent_name,
                        error=str(exc),
                    )

        tasks = [_guarded_analyze(agent) for agent in self._agents]
        results: list[AgentAnalysisResult] = list(await asyncio.gather(*tasks))

        total_findings = sum(len(r.findings) for r in results)
        agents_failed = sum(1 for r in results if r.error is not None)

        all_findings = [f for r in results for f in r.findings]
        unique = deduplicate_findings(all_findings)

        return DispatchResult(
            results=results,
            total_findings=total_findings,
            unique_findings=unique,
            agents_dispatched=len(self._agents),
            agents_failed=agents_failed,
            duration_ms=_now_ms() - start_ms,
        )


async def run_parallel_analysis(
    preflight_result: PreflightResult,
    search_engine: SparseSearchEngine,
    llm_client: LLMClientProtocol,
    *,
    max_concurrency: int = 16,
    document_name: str | None = None,
) -> DispatchResult:
    """Convenience function: create agents from manifest and dispatch.

    Parameters
    ----------
    preflight_result:
        Output from Phase 1 pre-flight pipeline.
    search_engine:
        Injected Elasticsearch BM25 search engine.
    llm_client:
        Injected LLM client (Ollama or mock).
    max_concurrency:
        Maximum parallel agents (default 16 — one per agent).
    document_name:
        Optional filter to restrict analysis to a single document.
    """

    agents = create_specialist_agents(
        preflight_result.specialist_manifest,
        search_engine,
        llm_client,
    )

    if not agents:
        return DispatchResult()

    dispatcher = ParallelDispatcher(agents, max_concurrency=max_concurrency)
    return await dispatcher.dispatch(document_name)


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Merge findings from different agents that cite the same text in the same section.

    Dedup key: (section_id, citation) — two findings quoting the same passage
    from the same section are considered the same issue regardless of which
    agent surfaced it.  The higher-confidence finding is kept; the other
    agent's name is appended to cross_refs so the provenance is preserved.
    """
    seen: dict[tuple[str, str], Finding] = {}

    for finding in findings:
        key = (finding.section_id, finding.citation)
        if key not in seen:
            seen[key] = finding
        else:
            existing = seen[key]
            if finding.confidence > existing.confidence:
                merged = list({
                    *finding.cross_refs,
                    *existing.cross_refs,
                    existing.source_agent.value,
                })
                seen[key] = finding.model_copy(update={"cross_refs": merged})
            else:
                merged = list({*existing.cross_refs, finding.source_agent.value})
                seen[key] = existing.model_copy(update={"cross_refs": merged})

    return list(seen.values())


def _now_ms() -> int:
    """Return current time in milliseconds."""
    return int(time.monotonic() * 1000)
