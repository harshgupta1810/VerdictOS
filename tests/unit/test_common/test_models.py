"""Tests for shared domain models."""

import json

import pytest

from src.common.models import ClauseType


def test_clause_type_contains_locked_taxonomy_values() -> None:
    assert [clause_type.value for clause_type in ClauseType] == [
        "tax_provision",
        "ip_assignment",
        "liability_cap",
        "fx_hedging",
        "employment_term",
        "change_of_control",
        "indemnification",
        "data_protection",
        "insurance_policy",
        "governance_clause",
        "related_party_transaction",
        "cyber_security",
        "supplier_contract",
        "customer_contract",
        "reputation_risk",
        "esg_obligation",
        "general",
    ]


def test_clause_type_serializes_as_string_value() -> None:
    assert json.dumps({"clause_type": ClauseType.GENERAL}) == '{"clause_type": "general"}'


def test_clause_type_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        ClauseType("unknown")
