"""Planner Agent (Phase 2: Smart Dispatch).

Evaluates file manifests and selectively activates only the
domain-specific specialist agents needed, saving 30-60% on tokens.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.search.schemas import SearchResult
    from src.search.search_engine import SparseSearchEngine

from pydantic import BaseModel, Field

from src.agents.schemas import ActiveSpecialistManifest, AgentName, SpecialistDefinition
from src.common.models import ClauseType
from src.ingestion.schemas import DocumentChunk
from src.search.schemas import SearchFilters, SearchQuery

logger = logging.getLogger(__name__)

CORRECT_AGENT_IDS = [
    "ip_agent",
    "litigation_agent",
    "regulatory_agent",
    "privacy_agent",
    "finance_agent",
    "tax_agent",
    "insurance_agent",
    "hr_agent",
    "governance_agent",
    "related_party_agent",
    "cyber_agent",
    "assets_agent",
    "supplier_agent",
    "customer_agent",
    "reputation_agent",
    "esg_agent",
]

_BASE_REGISTRY = [
    SpecialistDefinition(
        agent_name=AgentName.IP,
        routing_terms=[
            "intellectual property",
            "ip assignment",
            "patent",
            "trademark",
            "copyright",
            "invention",
            "license",
        ],
        clause_types=[ClauseType.IP_ASSIGNMENT],
    ),
    SpecialistDefinition(
        agent_name=AgentName.LITIGATION,
        routing_terms=["litigation", "lawsuit", "claim", "arbitration", "dispute", "settlement", "judgment"],
        clause_types=[ClauseType.INDEMNIFICATION],
    ),
    SpecialistDefinition(
        agent_name=AgentName.REGULATORY,
        routing_terms=[
            "permit",
            "regulator",
            "compliance",
            "antitrust",
            "merger control",
            "hsr",
            "sanction",
            "change of control",
        ],
        clause_types=[ClauseType.CHANGE_OF_CONTROL],
    ),
    SpecialistDefinition(
        agent_name=AgentName.PRIVACY,
        routing_terms=[
            "personal data",
            "privacy",
            "gdpr",
            "ccpa",
            "data processing",
            "breach obligation",
            "data protection",
        ],
        clause_types=[ClauseType.DATA_PROTECTION],
    ),
    SpecialistDefinition(
        agent_name=AgentName.FINANCE,
        routing_terms=[
            "p&l",
            "income statement",
            "cash",
            "balance sheet",
            "debt",
            "lien",
            "covenant",
            "foreign exchange",
            "hedging",
        ],
        clause_types=[ClauseType.FX_HEDGING, ClauseType.LIABILITY_CAP],
    ),
    SpecialistDefinition(
        agent_name=AgentName.TAX,
        routing_terms=["tax", "tax return", "withholding", "vat", "sales tax", "tax audit"],
        clause_types=[ClauseType.TAX_PROVISION],
    ),
    SpecialistDefinition(
        agent_name=AgentName.INSURANCE,
        routing_terms=["insurance", "policy", "coverage", "premium", "insurer", "insured"],
        clause_types=[ClauseType.INSURANCE_POLICY],
    ),
    SpecialistDefinition(
        agent_name=AgentName.HR,
        routing_terms=["employee", "employment", "compensation", "benefits", "severance", "non-compete"],
        clause_types=[ClauseType.EMPLOYMENT_TERM],
    ),
    SpecialistDefinition(
        agent_name=AgentName.GOVERNANCE,
        routing_terms=["bylaws", "articles", "board", "shareholder", "cap table", "equity", "governance"],
        clause_types=[ClauseType.GOVERNANCE_CLAUSE],
    ),
    SpecialistDefinition(
        agent_name=AgentName.RELATED_PARTY,
        routing_terms=["related party", "affiliate", "beneficial owner", "family member", "conflict of interest"],
        clause_types=[ClauseType.RELATED_PARTY_TRANSACTION],
    ),
    SpecialistDefinition(
        agent_name=AgentName.CYBER,
        routing_terms=["cybersecurity", "security incident", "it system", "hosting", "source code", "software", "saas"],
        clause_types=[ClauseType.CYBER_SECURITY],
    ),
    SpecialistDefinition(
        agent_name=AgentName.ASSETS,
        routing_terms=["asset", "lease", "equipment", "title", "encumbrance", "property", "change of control"],
        clause_types=[ClauseType.CHANGE_OF_CONTROL],
    ),
    SpecialistDefinition(
        agent_name=AgentName.SUPPLIER,
        routing_terms=["supplier", "vendor", "supply chain", "logistics", "distributor", "procurement"],
        clause_types=[ClauseType.SUPPLIER_CONTRACT],
    ),
    SpecialistDefinition(
        agent_name=AgentName.CUSTOMER,
        routing_terms=[
            "customer",
            "revenue concentration",
            "customer contract",
            "renewal",
            "churn",
            "accounts receivable",
        ],
        clause_types=[ClauseType.CUSTOMER_CONTRACT],
    ),
    SpecialistDefinition(
        agent_name=AgentName.REPUTATION,
        routing_terms=["reputation", "adverse media", "brand", "corruption", "misconduct", "whistleblower"],
        clause_types=[ClauseType.REPUTATION_RISK],
    ),
    SpecialistDefinition(
        agent_name=AgentName.ESG,
        routing_terms=["environmental", "emissions", "hazardous waste", "contamination", "esg", "sustainability"],
        clause_types=[ClauseType.ESG_OBLIGATION],
    ),
]

AGENT_SYNONYMS: dict[AgentName, dict[str, list[str]]] = {
    AgentName.IP: {
        "intellectual property": ["ip", "proprietary rights"],
        "patent": ["patent rights", "invention"],
    },
    AgentName.LITIGATION: {
        "litigation": ["lawsuit", "legal action"],
        "arbitration": ["dispute resolution", "proceeding"],
    },
    AgentName.REGULATORY: {
        "regulatory approval": ["permit", "license", "clearance"],
        "antitrust": ["competition law", "merger control", "hsr"],
    },
    AgentName.PRIVACY: {
        "personal data": ["personally identifiable information", "pii"],
        "privacy": ["data protection", "gdpr", "ccpa"],
    },
    AgentName.FINANCE: {
        "income statement": ["p&l", "profit and loss"],
        "cash": ["liquidity", "cash flow"],
        "debt": ["loan", "credit facility", "borrowing"],
    },
    AgentName.TAX: {
        "tax": ["taxation", "levy"],
        "withholding": ["tax deduction", "retention tax"],
    },
    AgentName.INSURANCE: {
        "insurance": ["coverage", "policy"],
        "insurer": ["carrier", "underwriter"],
    },
    AgentName.HR: {
        "employee": ["personnel", "workforce"],
        "compensation": ["salary", "remuneration"],
    },
    AgentName.GOVERNANCE: {
        "board": ["directors", "board of directors"],
        "shareholder": ["stockholder", "equity holder"],
    },
    AgentName.RELATED_PARTY: {
        "related party": ["affiliate", "connected person"],
        "beneficial owner": ["ultimate owner", "ubo"],
    },
    AgentName.CYBER: {
        "cybersecurity": ["information security", "infosec"],
        "it system": ["technology system", "infrastructure"],
    },
    AgentName.ASSETS: {
        "asset": ["property", "equipment"],
        "encumbrance": ["lien", "security interest"],
    },
    AgentName.SUPPLIER: {
        "supplier": ["vendor", "provider"],
        "supply chain": ["procurement", "logistics"],
    },
    AgentName.CUSTOMER: {
        "customer": ["client", "account"],
        "revenue concentration": ["customer concentration", "key account dependency"],
    },
    AgentName.REPUTATION: {
        "adverse media": ["negative press", "controversy"],
        "misconduct": ["wrongdoing", "ethics breach"],
    },
    AgentName.ESG: {
        "environmental": ["ecological", "environment"],
        "emissions": ["carbon footprint", "greenhouse gas"],
    },
}

SPECIALIST_REGISTRY = [
    specialist.model_copy(update={"synonym_groups": AGENT_SYNONYMS[specialist.agent_name]})
    for specialist in _BASE_REGISTRY
]
_SPECIALISTS_BY_NAME = {specialist.agent_name: specialist for specialist in SPECIALIST_REGISTRY}


def build_compound_query(
    agent_name: AgentName,
    text: str,
    *,
    clause_types: Iterable[ClauseType] | None = None,
    top_k: int | None = None,
) -> SearchQuery:
    """Build a query-time synonym expansion without mutating the BM25 index."""

    specialist = _SPECIALISTS_BY_NAME[agent_name]
    lowered_text = text.casefold()
    expanded_terms: list[str] = []
    for canonical_term, synonyms in specialist.synonym_groups.items():
        group = [canonical_term, *synonyms]
        if any(term.casefold() in lowered_text for term in group):
            for term in group:
                if term.casefold() != lowered_text and term not in expanded_terms:
                    expanded_terms.append(term)

    return SearchQuery(
        text=text,
        expanded_terms=expanded_terms,
        filters=SearchFilters(
            clause_types=list(clause_types) if clause_types is not None else specialist.clause_types,
        ),
        size=top_k if top_k is not None else specialist.top_k,
    )


class LLMPlannerOutput(BaseModel):
    """Pydantic schema for Planner LLM classification output."""
    active_agents: list[str] = Field(
        ...,
        description=f"List of active specialist agent IDs selected from the available list: {CORRECT_AGENT_IDS}"
    )
    document_type_map: dict[str, str] = Field(
        ...,
        description="Mapping of document names to their classified types."
    )


class PlannerAgent:
    """Select the narrowest deterministic or LLM-based specialist set for a manifest."""

    def __init__(self, *, model_name: str = "llama3.2:1b") -> None:
        self.model_name = model_name

    def plan(
        self,
        *,
        document_names: Iterable[str],
        chunks: Iterable[DocumentChunk],
    ) -> ActiveSpecialistManifest:
        chunk_list = list(chunks)
        doc_names = list(document_names)

        # 1. Try LLM-based planning
        try:
            manifest = self._plan_with_llm(doc_names, chunk_list)
            if manifest is not None:
                return manifest
        except Exception as exc:
            logger.warning("LLM-based planning failed: %s. Falling back to deterministic plan.", exc)

        # 2. Deterministic fallback plan
        return self._plan_deterministic(doc_names, chunk_list)

    def _plan_with_llm(
        self,
        doc_names: list[str],
        chunk_list: list[DocumentChunk],
    ) -> ActiveSpecialistManifest | None:
        """Synchronous LLM-based planning using blocking httpx.

        Uses a direct synchronous HTTP call to Ollama so the pre-flight
        pipeline never enters an asyncio event loop.  This keeps
        ``PreflightPipeline.run()`` purely synchronous.
        """
        import json as _json

        import httpx
        from pydantic import ValidationError

        from src.config import settings

        if not doc_names:
            return None

        ollama_url = settings.ollama_url.rstrip("/")

        # Build prompt
        system_prompt = (
            "You are an expert contract analysis and planner agent. Your job is to analyze "
            "the provided list of document names and snippets of text chunks from a deal bundle. \n"
            "1. Classify the document type of each document (e.g. 'SPA', 'Employment Agreement', 'NDA', 'Lease', etc.).\n"
            "2. Determine which specialist agents should be activated to analyze this bundle based on the document types and content. "
            "Select from the following available agent IDs:\n"
            f"{', '.join(CORRECT_AGENT_IDS)}\n"
            "Output ONLY valid JSON matching the schema."
        )

        # Gather a text sample of the documents to stay within reasonable token limits
        text_samples = []
        for doc in doc_names:
            doc_chunks = [c.text for c in chunk_list if c.document_name == doc]
            if doc_chunks:
                sample = "\n".join(doc_chunks)[:1000]
                text_samples.append(f"Document: {doc}\nContent Snippet:\n{sample}")
            else:
                text_samples.append(f"Document: {doc}\nContent Snippet:\n(No content/metadata extracted)")

        chunks_summary = "\n\n".join(text_samples)
        doc_names_str = "\n- ".join(doc_names)

        user_prompt = (
            f"Documents present in the bundle:\n- {doc_names_str}\n\n"
            f"Here are snippets from the documents:\n{chunks_summary}\n\n"
            "Return a JSON object matching the requested schema."
        )

        payload = {
            "model": self.model_name,
            "prompt": user_prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            resp = httpx.post(
                f"{ollama_url}/api/generate",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("Synchronous LLM call failed: %s", exc)
            return None

        raw_text = resp.json().get("response", "")
        try:
            parsed = _json.loads(raw_text)
            llm_output = LLMPlannerOutput.model_validate(parsed)
        except (_json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLM planner output parsing failed: %s", exc)
            return None

        active_agents_enums = []
        for agent_id in llm_output.active_agents:
            try:
                active_agents_enums.append(AgentName(agent_id))
            except ValueError:
                pass

        if not active_agents_enums:
            # If LLM returned no valid agents, trigger the fallback dispatching logic,
            # but we can still keep the document type map!
            fallback_manifest = self._plan_deterministic(doc_names, chunk_list)
            return ActiveSpecialistManifest(
                active_agents=fallback_manifest.active_agents,
                matched_terms=fallback_manifest.matched_terms,
                used_fallback=True,
                document_type_map=llm_output.document_type_map,
            )

        return ActiveSpecialistManifest(
            active_agents=active_agents_enums,
            matched_terms={},
            used_fallback=False,
            document_type_map=llm_output.document_type_map,
        )

    def _plan_deterministic(
        self,
        doc_names: list[str],
        chunk_list: list[DocumentChunk],
    ) -> ActiveSpecialistManifest:
        corpus = " ".join([*doc_names, *(chunk.text for chunk in chunk_list)])
        chunk_clause_types = {chunk.clause_type for chunk in chunk_list}
        matched_terms: dict[AgentName, list[str]] = {}
        active_agents: list[AgentName] = []

        for specialist in SPECIALIST_REGISTRY:
            term_matches = [
                term
                for term in specialist.routing_terms
                if _contains_term(corpus, term)
            ]
            clause_matches = [
                clause_type.value
                for clause_type in specialist.clause_types
                if clause_type in chunk_clause_types and clause_type is not ClauseType.GENERAL
            ]
            matches = [*term_matches, *clause_matches]
            if matches:
                active_agents.append(specialist.agent_name)
                matched_terms[specialist.agent_name] = list(dict.fromkeys(matches))

        if not active_agents:
            return ActiveSpecialistManifest(
                active_agents=[specialist.agent_name for specialist in SPECIALIST_REGISTRY],
                used_fallback=True,
                document_type_map={},
            )
        return ActiveSpecialistManifest(
            active_agents=active_agents,
            matched_terms=matched_terms,
            document_type_map={},
        )


def _contains_term(text: str, term: str) -> bool:
    normalized_text = re.sub(r"[_\-]+", " ", text.casefold())
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", normalized_text) is not None


def resolve_section_pointers(
    results: list[SearchResult],
    search_engine: SparseSearchEngine,
    *,
    document_name: str | None = None,
    max_additional: int = 5,
) -> list[SearchResult]:
    """Expand BM25 results by fetching sections cross-referenced in the initial hits.

    When a retrieved chunk references other sections (e.g. 'see Section 4.2'),
    those sections are fetched and appended so the agent can analyse the full
    context of a clause cross-reference chain.  Silently returns the original
    results on any retrieval failure so the main pipeline is never blocked.
    """
    existing_chunk_ids = {r.chunk_id for r in results}
    existing_section_ids = {r.section_id for r in results}

    referenced: set[str] = set()
    for result in results:
        for ref in result.references_sections:
            if ref not in existing_section_ids:
                referenced.add(ref)

    if not referenced:
        return results

    section_ids_to_fetch = list(referenced)[:max_additional]
    try:
        extra = search_engine.fetch_sections(
            section_ids_to_fetch,
            document_name=document_name,
            size=max_additional,
        )
    except Exception:
        return results

    new = [r for r in extra if r.chunk_id not in existing_chunk_ids]
    return [*results, *new]
