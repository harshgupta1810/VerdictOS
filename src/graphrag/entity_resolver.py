"""3-Tier Entity Resolution Engine.

Resolves naming variations across documents using:
  - Tier 1: Case-insensitive string match / punctuation stripping
  - Tier 2: Fuzzy logic (Levenshtein distance ratio > 0.85)
  - Tier 3: LLM-prompted disambiguation via Ollama
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Protocol

from rapidfuzz import fuzz

from src.graphrag.schemas import EntityResolution, LLMEntityResolution

FUZZY_MATCH_THRESHOLD = 0.85


class EntityDisambiguator(Protocol):
    """Injected local LLM adapter used only for ambiguous candidates."""

    def disambiguate(
        self,
        *,
        name: str,
        entity_type: str,
        candidates: list[str],
    ) -> str | Mapping[str, object]: ...


class EntityResolver:
    """Resolve entity aliases conservatively while preserving auditability."""

    def __init__(self, *, llm_client: EntityDisambiguator | None = None) -> None:
        self._registry: dict[str, list[str]] = defaultdict(list)
        self._cache: dict[tuple[str, str], EntityResolution] = {}
        self._llm_client = llm_client

    def register(self, canonical_name: str, entity_type: str) -> None:
        """Register a known canonical entity and invalidate affected misses."""

        if canonical_name not in self._registry[entity_type]:
            self._registry[entity_type].append(canonical_name)
            self._invalidate_entity_type(entity_type)

    def registered_entities(self, entity_type: str) -> list[str]:
        """Return a copy of the known canonical entities for one type."""

        return list(self._registry[entity_type])

    def resolve(
        self,
        name: str,
        entity_type: str,
        *,
        candidates: Iterable[str] | None = None,
    ) -> EntityResolution:
        """Resolve a candidate using exact normalized matching."""

        candidate_names = list(candidates) if candidates is not None else list(self._registry[entity_type])
        cache_key = (normalize_entity_name(name), entity_type)
        if candidates is None and cache_key in self._cache:
            return self._cache[cache_key].model_copy(update={"cache_hit": True})

        normalized_name = normalize_entity_name(name)
        exact_matches = [
            candidate_name
            for candidate_name in candidate_names
            if normalize_entity_name(candidate_name) == normalized_name
        ]
        if len(exact_matches) == 1:
            resolution = EntityResolution(
                original_name=name,
                canonical_name=exact_matches[0],
                entity_type=entity_type,
                resolution_tier=1,
                status="confirmed",
                confidence=1.0,
            )
        else:
            resolution = self._resolve_fuzzy(name, entity_type, candidate_names)
            if resolution.status == "unconfirmed_node":
                resolution = self._resolve_with_llm(name, entity_type, candidate_names)

        if candidates is None:
            self._cache[cache_key] = resolution
        return resolution

    @staticmethod
    def _resolve_fuzzy(name: str, entity_type: str, candidates: list[str]) -> EntityResolution:
        scored_candidates = [
            (candidate_name, _similarity_ratio(name, candidate_name))
            for candidate_name in candidates
        ]
        if scored_candidates:
            highest_score = max(score for _, score in scored_candidates)
            leaders = [
                candidate_name
                for candidate_name, score in scored_candidates
                if score == highest_score
            ]
            if highest_score > FUZZY_MATCH_THRESHOLD and len(leaders) == 1:
                return EntityResolution(
                    original_name=name,
                    canonical_name=leaders[0],
                    entity_type=entity_type,
                    resolution_tier=2,
                    status="confirmed",
                    confidence=highest_score,
                )

        return EntityResolution(
            original_name=name,
            canonical_name=name,
            entity_type=entity_type,
            status="unconfirmed_node",
            confidence=0.0,
            reason="no_unique_fuzzy_match",
        )

    def _resolve_with_llm(self, name: str, entity_type: str, candidates: list[str]) -> EntityResolution:
        if self._llm_client is None or not candidates:
            return _unconfirmed_resolution(name, entity_type, reason="no_llm_resolution_available")

        try:
            raw_resolution = self._llm_client.disambiguate(
                name=name,
                entity_type=entity_type,
                candidates=candidates,
            )
            if isinstance(raw_resolution, str):
                llm_resolution = LLMEntityResolution.model_validate_json(raw_resolution)
            else:
                llm_resolution = LLMEntityResolution.model_validate(raw_resolution)
        except Exception:
            return _unconfirmed_resolution(name, entity_type, reason="llm_resolution_failed")

        if not llm_resolution.merge:
            return _unconfirmed_resolution(name, entity_type, reason="llm_rejected_merge")
        if llm_resolution.canonical_name not in candidates:
            return _unconfirmed_resolution(name, entity_type, reason="llm_returned_unknown_canonical_name")
        return EntityResolution(
            original_name=name,
            canonical_name=llm_resolution.canonical_name,
            entity_type=entity_type,
            resolution_tier=3,
            status="confirmed",
            confidence=llm_resolution.confidence,
            reason=llm_resolution.reason,
        )

    def _invalidate_entity_type(self, entity_type: str) -> None:
        self._cache = {
            cache_key: resolution
            for cache_key, resolution in self._cache.items()
            if cache_key[1] != entity_type
        }


def normalize_entity_name(name: str) -> str:
    """Normalize case, punctuation, and whitespace for Tier 1 matching."""

    return " ".join(re.sub(r"[^\w\s]", " ", name.casefold()).split())


def _similarity_ratio(left: str, right: str) -> float:
    return fuzz.ratio(normalize_entity_name(left), normalize_entity_name(right)) / 100


def _unconfirmed_resolution(name: str, entity_type: str, *, reason: str) -> EntityResolution:
    return EntityResolution(
        original_name=name,
        canonical_name=name,
        entity_type=entity_type,
        status="unconfirmed_node",
        confidence=0.0,
        reason=reason,
    )
