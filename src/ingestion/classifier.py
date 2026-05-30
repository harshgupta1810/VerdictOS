"""Clause-Type Taxonomy Classifier.

Rule-based heuristic classifier mapping text chunks to legal/operational
taxonomy tags (e.g., tax_provision, ip_assignment, liability_cap).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from src.common.models import ClauseType
from src.ingestion.schemas import ClassificationResult, DocumentChunk

MIN_CLASSIFICATION_CONFIDENCE = 0.7

CLAUSE_TYPE_TERMS: Mapping[ClauseType, Sequence[str]] = {
    ClauseType.TAX_PROVISION: ("tax", "tax return", "withholding", "sales tax", "vat"),
    ClauseType.IP_ASSIGNMENT: (
        "intellectual property",
        "ip assignment",
        "patent",
        "trademark",
        "copyright",
        "invention",
    ),
    ClauseType.LIABILITY_CAP: (
        "liability cap",
        "liability limit",
        "limitation of liability",
        "aggregate liability",
    ),
    ClauseType.FX_HEDGING: ("foreign exchange", "fx", "currency hedge", "hedging", "exchange rate"),
    ClauseType.EMPLOYMENT_TERM: ("employment", "employee", "compensation", "benefits", "severance"),
    ClauseType.CHANGE_OF_CONTROL: ("change of control", "acquisition", "merger", "assignment consent"),
    ClauseType.INDEMNIFICATION: ("indemnification", "indemnify", "hold harmless", "defend"),
    ClauseType.DATA_PROTECTION: ("personal data", "privacy", "data protection", "gdpr", "ccpa"),
}


class ClauseClassifier:
    """Apply conservative keyword scoring to document chunks."""

    def classify(self, text: str) -> ClassificationResult:
        """Return the strongest unambiguous clause classification."""

        matches_by_type = {
            clause_type: _matching_terms(text, terms)
            for clause_type, terms in CLAUSE_TYPE_TERMS.items()
        }
        matches_by_type = {clause_type: matches for clause_type, matches in matches_by_type.items() if matches}
        if not matches_by_type:
            return ClassificationResult(clause_type=ClauseType.GENERAL, confidence=0.0)

        highest_match_count = max(len(matches) for matches in matches_by_type.values())
        leaders = [
            clause_type
            for clause_type, matches in matches_by_type.items()
            if len(matches) == highest_match_count
        ]
        if len(leaders) != 1:
            all_matches = sorted({term for matches in matches_by_type.values() for term in matches})
            return ClassificationResult(
                clause_type=ClauseType.GENERAL,
                confidence=0.0,
                matched_terms=all_matches,
            )

        clause_type = leaders[0]
        matched_terms = matches_by_type[clause_type]
        confidence = min(MIN_CLASSIFICATION_CONFIDENCE + (0.1 * (len(matched_terms) - 1)), 0.99)
        if confidence < MIN_CLASSIFICATION_CONFIDENCE:
            return ClassificationResult(
                clause_type=ClauseType.GENERAL,
                confidence=confidence,
                matched_terms=matched_terms,
            )
        return ClassificationResult(
            clause_type=clause_type,
            confidence=confidence,
            matched_terms=matched_terms,
        )

    def classify_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """Return a chunk enriched with classification metadata."""

        classification = self.classify(chunk.text)
        return chunk.model_copy(
            update={
                "clause_type": classification.clause_type,
                "classification_confidence": classification.confidence,
                "matched_terms": classification.matched_terms,
            }
        )


def _matching_terms(text: str, terms: Sequence[str]) -> list[str]:
    matches = []
    for term in terms:
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(term)
    return matches
