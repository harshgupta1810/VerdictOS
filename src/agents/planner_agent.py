"""Planner Agent (Phase 2: Smart Dispatch).

Evaluates file manifests and selectively activates only the
domain-specific specialist agents needed, saving 30-60% on tokens.
"""

import re
from collections.abc import Iterable

from src.agents.schemas import ActiveSpecialistManifest, AgentName, SpecialistDefinition
from src.common.models import ClauseType
from src.ingestion.schemas import DocumentChunk
from src.search.schemas import SearchFilters, SearchQuery

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

SPECIALIST_REGISTRY = [
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
    ),
    SpecialistDefinition(
        agent_name=AgentName.HR,
        routing_terms=["employee", "employment", "compensation", "benefits", "severance", "non-compete"],
        clause_types=[ClauseType.EMPLOYMENT_TERM],
    ),
    SpecialistDefinition(
        agent_name=AgentName.GOVERNANCE,
        routing_terms=["bylaws", "articles", "board", "shareholder", "cap table", "equity", "governance"],
    ),
    SpecialistDefinition(
        agent_name=AgentName.RELATED_PARTY,
        routing_terms=["related party", "affiliate", "beneficial owner", "family member", "conflict of interest"],
    ),
    SpecialistDefinition(
        agent_name=AgentName.CYBER,
        routing_terms=["cybersecurity", "security incident", "it system", "hosting", "source code", "software", "saas"],
    ),
    SpecialistDefinition(
        agent_name=AgentName.ASSETS,
        routing_terms=["asset", "lease", "equipment", "title", "encumbrance", "property", "change of control"],
        clause_types=[ClauseType.CHANGE_OF_CONTROL],
    ),
    SpecialistDefinition(
        agent_name=AgentName.SUPPLIER,
        routing_terms=["supplier", "vendor", "supply chain", "logistics", "distributor", "procurement"],
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
    ),
    SpecialistDefinition(
        agent_name=AgentName.REPUTATION,
        routing_terms=["reputation", "adverse media", "brand", "corruption", "misconduct", "whistleblower"],
    ),
    SpecialistDefinition(
        agent_name=AgentName.ESG,
        routing_terms=["environmental", "emissions", "hazardous waste", "contamination", "esg", "sustainability"],
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
    for specialist in SPECIALIST_REGISTRY
]
_SPECIALISTS_BY_NAME = {specialist.agent_name: specialist for specialist in SPECIALIST_REGISTRY}


def build_compound_query(
    agent_name: AgentName,
    text: str,
    *,
    clause_types: Iterable[ClauseType] | None = None,
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
    )


class PlannerAgent:
    """Select the narrowest deterministic specialist set for a manifest."""

    def plan(
        self,
        *,
        document_names: Iterable[str],
        chunks: Iterable[DocumentChunk],
    ) -> ActiveSpecialistManifest:
        chunk_list = list(chunks)
        corpus = " ".join([*document_names, *(chunk.text for chunk in chunk_list)])
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
            )
        return ActiveSpecialistManifest(
            active_agents=active_agents,
            matched_terms=matched_terms,
        )


def _contains_term(text: str, term: str) -> bool:
    normalized_text = re.sub(r"[_\-]+", " ", text.casefold())
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", normalized_text) is not None
