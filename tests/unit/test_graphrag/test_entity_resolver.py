"""Tests for 3-tier entity resolution engine."""

import pytest
from typing import Any

import src.graphrag.entity_resolver as resolver_module
from src.graphrag.entity_resolver import EntityResolver, normalize_entity_name


class _LLMClient:
    def __init__(self, response: str | dict[str, object] | Exception) -> None:
        self.response = response

    def disambiguate(self, *, name: str, entity_type: str, candidates: list[str]) -> str | dict[str, object]:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_normalize_entity_name_strips_punctuation_case_and_extra_spaces() -> None:
    assert normalize_entity_name("  ACME,  Corp. ") == "acme corp"


def test_tier_one_resolves_case_and_punctuation_variants() -> None:
    resolver = EntityResolver()
    resolver.register("Acme Corp.", "organization")

    resolution = resolver.resolve("ACME CORP", "organization")

    assert resolution.canonical_name == "Acme Corp."
    assert resolution.resolution_tier == 1
    assert resolution.status == "confirmed"
    assert resolution.confidence == 1.0


def test_resolver_caches_registry_lookups() -> None:
    resolver = EntityResolver()
    resolver.register("Acme Corp.", "organization")

    assert resolver.resolve("ACME CORP", "organization").cache_hit is False
    assert resolver.resolve("ACME CORP", "organization").cache_hit is True


def test_resolver_preserves_distinct_unconfirmed_entities() -> None:
    resolver = EntityResolver()
    resolver.register("Acme Corp.", "organization")

    resolution = resolver.resolve("Acme Corporation", "organization")

    assert resolution.canonical_name == "Acme Corporation"
    assert resolution.resolution_tier is None
    assert resolution.status == "unconfirmed_node"


def test_register_invalidates_cached_misses_for_entity_type() -> None:
    resolver = EntityResolver()
    unresolved = resolver.resolve("New Co.", "organization")
    resolver.register("New Co", "organization")

    resolved = resolver.resolve("new co.", "organization")

    assert unresolved.status == "unconfirmed_node"
    assert resolved.status == "confirmed"
    assert resolved.cache_hit is False


def test_tier_two_resolves_unique_fuzzy_match_above_threshold() -> None:
    resolver = EntityResolver()
    resolver.register("Acme Corporation", "organization")

    resolution = resolver.resolve("Acme Corporatio", "organization")

    assert resolution.canonical_name == "Acme Corporation"
    assert resolution.resolution_tier == 2
    assert resolution.confidence > 0.85


@pytest.mark.parametrize(
    ("ratio", "expected_status"),
    [
        (0.851, "confirmed"),
        (0.85, "unconfirmed_node"),
        (0.849, "unconfirmed_node"),
    ],
)
def test_tier_two_requires_ratio_strictly_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
    ratio: float,
    expected_status: str,
) -> None:
    monkeypatch.setattr(resolver_module, "_similarity_ratio", lambda _left, _right: ratio)
    resolver = EntityResolver()
    resolver.register("Known Entity", "organization")

    resolution = resolver.resolve("Candidate Entity", "organization")

    assert resolution.status == expected_status


def test_tier_two_preserves_ambiguous_tied_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolver_module, "_similarity_ratio", lambda _left, _right: 0.99)
    resolver = EntityResolver()
    resolver.register("Known One", "organization")
    resolver.register("Known Two", "organization")

    resolution = resolver.resolve("Candidate", "organization")

    assert resolution.status == "unconfirmed_node"
    assert resolution.resolution_tier is None


def test_tier_three_accepts_strict_json_merge_for_registered_canonical_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resolver_module, "_similarity_ratio", lambda _left, _right: 0.70)
    resolver = EntityResolver(
        llm_client=_LLMClient(
            '{"merge":true,"canonical_name":"Acme Corp.","confidence":0.91,"reason":"Known alias"}'
        )
    )
    resolver.register("Acme Corp.", "organization")

    resolution = resolver.resolve("Acme Holdings", "organization")

    assert resolution.canonical_name == "Acme Corp."
    assert resolution.resolution_tier == 3
    assert resolution.status == "confirmed"
    assert resolution.confidence == pytest.approx(0.91)


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (
            {"merge": False, "canonical_name": None, "confidence": 0.2, "reason": "Different entity"},
            "llm_rejected_merge",
        ),
        ("not json", "llm_resolution_failed"),
        (ConnectionError("ollama offline"), "llm_resolution_failed"),
        (
            {"merge": True, "canonical_name": "Unknown Co", "confidence": 0.9, "reason": "Bad canonical"},
            "llm_returned_unknown_canonical_name",
        ),
    ],
)
def test_tier_three_preserves_unconfirmed_node_for_rejected_or_invalid_results(
    monkeypatch: pytest.MonkeyPatch,
    response: str | dict[str, object] | Exception,
    reason: str,
) -> None:
    monkeypatch.setattr(resolver_module, "_similarity_ratio", lambda _left, _right: 0.70)
    resolver = EntityResolver(llm_client=_LLMClient(response))
    resolver.register("Acme Corp.", "organization")

    resolution = resolver.resolve("Acme Holdings", "organization")

    assert resolution.canonical_name == "Acme Holdings"
    assert resolution.resolution_tier is None
    assert resolution.status == "unconfirmed_node"
    assert resolution.reason == reason


def test_tier_1_person_initials_matching() -> None:
    resolver = EntityResolver()
    resolver.register("John Smith", "person")

    # J. Smith should resolve to John Smith at Tier 1
    res1 = resolver.resolve("J. Smith", "person")
    assert res1.canonical_name == "John Smith"
    assert res1.resolution_tier == 1

    # Smith, J. should resolve to John Smith at Tier 1
    res2 = resolver.resolve("Smith, J.", "person")
    assert res2.canonical_name == "John Smith"
    assert res2.resolution_tier == 1


def test_tier_1_role_stripping() -> None:
    resolver = EntityResolver()
    resolver.register("John Smith", "person")

    # "CEO John Smith" should resolve to "John Smith" at Tier 1 after role stripping
    res = resolver.resolve("CEO John Smith", "person")
    assert res.canonical_name == "John Smith"
    assert res.resolution_tier == 1


def test_tier_2_bundle_context() -> None:
    resolver = EntityResolver()
    # Register Acme Corporation in doc1.pdf
    resolver.register("Acme Corporation", "organization", document_name="doc1.pdf")

    # Resolve "Acme Corporatio" in same bundle context (doc1.pdf)
    # The similarity score will be boosted, ensuring resolution
    res = resolver.resolve(
        "Acme Corporatio",
        "organization",
        bundle_context=["doc1.pdf"]
    )
    assert res.canonical_name == "Acme Corporation"
    assert res.resolution_tier == 2


def test_tier_3_gating(monkeypatch: pytest.MonkeyPatch) -> None:
    # If the similarity is too low (e.g. 0.50), LLM should NOT be called, returning unconfirmed
    monkeypatch.setattr(resolver_module, "_similarity_ratio", lambda _left, _right: 0.50)
    llm_calls = []

    class TrackedLLM:
        def disambiguate(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            llm_calls.append(kwargs)
            return {"merge": False}

    resolver = EntityResolver(llm_client=TrackedLLM())
    resolver.register("Acme Corp.", "organization")

    res = resolver.resolve("Acme Holdings", "organization")
    assert res.status == "unconfirmed_node"
    assert len(llm_calls) == 0  # Gated out since score is 0.50

