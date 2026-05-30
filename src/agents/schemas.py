"""Typed contracts for specialist planning and query construction."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.common.models import ClauseType


class AgentName(str, Enum):  # noqa: UP042 - Phase 2 dispatch consumes these string enum values.
    """Stable specialist identifiers shared with Phase 2 dispatch."""

    IP = "ip_agent"
    LITIGATION = "litigation_agent"
    REGULATORY = "regulatory_agent"
    PRIVACY = "privacy_agent"
    FINANCE = "finance_agent"
    TAX = "tax_agent"
    INSURANCE = "insurance_agent"
    HR = "hr_agent"
    GOVERNANCE = "governance_agent"
    RELATED_PARTY = "related_party_agent"
    CYBER = "cyber_agent"
    ASSETS = "assets_agent"
    SUPPLIER = "supplier_agent"
    CUSTOMER = "customer_agent"
    REPUTATION = "reputation_agent"
    ESG = "esg_agent"


class SpecialistDefinition(BaseModel):
    """Data-driven specialist scope used by planner routing."""

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName
    routing_terms: list[str] = Field(min_length=1)
    clause_types: list[ClauseType] = Field(default_factory=list)
    synonym_groups: dict[str, list[str]] = Field(default_factory=dict)


class ActiveSpecialistManifest(BaseModel):
    """Deterministic planner output consumed by Phase 2 dispatch."""

    model_config = ConfigDict(extra="forbid")

    active_agents: list[AgentName] = Field(min_length=1)
    matched_terms: dict[AgentName, list[str]] = Field(default_factory=dict)
    used_fallback: bool = False
