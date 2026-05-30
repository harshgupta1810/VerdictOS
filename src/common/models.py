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
    GENERAL = "general"
