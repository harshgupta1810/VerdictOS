"""Tests for clause-type taxonomy classifier."""

import pytest

from src.common.models import ClauseType
from src.ingestion.classifier import CLAUSE_TYPE_TERMS, ClauseClassifier
from src.ingestion.schemas import DocumentChunk


@pytest.mark.parametrize(
    ("clause_type", "text"),
    [
        (ClauseType.TAX_PROVISION, "Seller shall remit withholding tax."),
        (ClauseType.IP_ASSIGNMENT, "The patent assignment covers each invention."),
        (ClauseType.LIABILITY_CAP, "The aggregate liability is subject to a liability cap."),
        (ClauseType.FX_HEDGING, "Foreign exchange exposure is covered by currency hedge contracts."),
        (ClauseType.EMPLOYMENT_TERM, "Employee compensation and benefits continue after closing."),
        (ClauseType.CHANGE_OF_CONTROL, "A change of control occurs upon an acquisition."),
        (ClauseType.INDEMNIFICATION, "Seller shall indemnify and hold harmless the buyer."),
        (ClauseType.DATA_PROTECTION, "Personal data processing complies with GDPR."),
        (ClauseType.INSURANCE_POLICY, "The insurer shall maintain coverage and pay the premium."),
        (ClauseType.GOVERNANCE_CLAUSE, "The shareholder agreement governs the cap table and voting rights."),
        (ClauseType.RELATED_PARTY_TRANSACTION, "The related party transaction requires board approval by the beneficial owner."),
        (ClauseType.CYBER_SECURITY, "The cybersecurity policy covers the it system and source code."),
        (ClauseType.SUPPLIER_CONTRACT, "The supplier and distributor agree on procurement terms."),
        (ClauseType.CUSTOMER_CONTRACT, "The customer contract specifies renewal term and accounts receivable."),
        (ClauseType.REPUTATION_RISK, "Adverse media relating to misconduct may trigger a reputation clause."),
        (ClauseType.ESG_OBLIGATION, "The esg policy covers emissions and sustainability reporting."),
    ],
)
def test_classifier_returns_each_locked_clause_type(clause_type: ClauseType, text: str) -> None:
    result = ClauseClassifier().classify(text)

    assert result.clause_type is clause_type
    assert result.confidence >= 0.7
    assert result.matched_terms


def test_classifier_returns_general_for_uncertain_text() -> None:
    result = ClauseClassifier().classify("The parties agree to cooperate.")

    assert result.clause_type is ClauseType.GENERAL
    assert result.confidence < 0.7


def test_classifier_returns_general_for_ambiguous_tie() -> None:
    result = ClauseClassifier().classify("The tax and patent schedules are attached.")

    assert result.clause_type is ClauseType.GENERAL
    assert result.matched_terms == ["patent", "tax"]


def test_classifier_enriches_chunk_without_mutating_source() -> None:
    chunk = DocumentChunk(
        chunk_id="agreement:0",
        document_name="agreement.pdf",
        chunk_index=0,
        text="Personal data is protected under GDPR.",
        section_id="Section 1",
        absolute_page=0,
    )

    classified = ClauseClassifier().classify_chunk(chunk)

    assert chunk.clause_type is ClauseType.GENERAL
    assert classified.clause_type is ClauseType.DATA_PROTECTION
    assert classified.classification_confidence == pytest.approx(0.8)


def test_classifier_defines_terms_for_every_non_general_clause_type() -> None:
    assert set(CLAUSE_TYPE_TERMS) == set(ClauseType) - {ClauseType.GENERAL}
