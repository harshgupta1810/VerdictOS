"""Shared domain models used across VerdictOS pipeline boundaries."""

from enum import Enum


class ClauseType(str, Enum):  # noqa: UP042 - Keep the cross-module wire contract explicit.
    """Canonical clause taxonomy shared by ingestion, search, and agents."""

    TAX_PROVISION = "tax_provision"
    IP_ASSIGNMENT = "ip_assignment"
    LIABILITY_CAP = "liability_cap"
    FX_HEDGING = "fx_hedging"
    EMPLOYMENT_TERM = "employment_term"
    CHANGE_OF_CONTROL = "change_of_control"
    INDEMNIFICATION = "indemnification"
    DATA_PROTECTION = "data_protection"
    INSURANCE_POLICY = "insurance_policy"
    GOVERNANCE_CLAUSE = "governance_clause"
    RELATED_PARTY_TRANSACTION = "related_party_transaction"
    CYBER_SECURITY = "cyber_security"
    SUPPLIER_CONTRACT = "supplier_contract"
    CUSTOMER_CONTRACT = "customer_contract"
    REPUTATION_RISK = "reputation_risk"
    ESG_OBLIGATION = "esg_obligation"
    GENERAL = "general"
