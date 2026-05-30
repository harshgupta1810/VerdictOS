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


from typing import Any, Protocol


class EntityDisambiguator(Protocol):
    """Injected local LLM adapter used only for ambiguous candidates."""

    def disambiguate(
        self,
        *,
        name: str,
        entity_type: str,
        candidates: list[str],
    ) -> str | Mapping[str, object]: ...


class OllamaDisambiguator:
    """Concrete implementation of EntityDisambiguator using OllamaClient."""

    def __init__(self, ollama_client: Any, model_name: str = "llama3.2:1b") -> None:
        self.client = ollama_client
        self.model_name = model_name

    async def disambiguate_async(
        self,
        *,
        name: str,
        entity_type: str,
        candidates: list[str],
    ) -> LLMEntityResolution:
        # Formulate prompt
        system_prompt = (
            "You are an expert entity resolution system. Determine if the entity name "
            "refers to the same entity as one of the candidate names. "
            "Output ONLY valid JSON matching the schema."
        )
        user_prompt = (
            f"Entity Name: {name}\n"
            f"Entity Type: {entity_type}\n"
            f"Candidates: {', '.join(candidates)}\n\n"
            "Return a JSON object with: \n"
            "- \"merge\": true if it matches one of the candidates, false otherwise\n"
            "- \"canonical_name\": the exact matched candidate name (or null if merge is false)\n"
            "- \"confidence\": confidence score between 0.0 and 1.0\n"
            "- \"reason\": explanation of the decision"
        )

        from src.llm.schemas import LLMRequest
        req = LLMRequest(
            model=self.model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            format="json",
            temperature=0.1
        )

        try:
            result = await self.client.generate_with_schema(req, LLMEntityResolution)
            return result
        except Exception as exc:
            return LLMEntityResolution(
                merge=False,
                canonical_name=None,
                confidence=0.0,
                reason=f"LLM call failed: {exc}"
            )

    def disambiguate(
        self,
        *,
        name: str,
        entity_type: str,
        candidates: list[str],
    ) -> dict[str, Any]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(
                self.disambiguate_async(name=name, entity_type=entity_type, candidates=candidates)
            ).model_dump()
        else:
            return asyncio.run(
                self.disambiguate_async(name=name, entity_type=entity_type, candidates=candidates)
            ).model_dump()


class EntityResolver:
    """Resolve entity aliases conservatively while preserving auditability."""

    def __init__(self, *, llm_client: EntityDisambiguator | None = None) -> None:
        self._registry: dict[str, list[str]] = defaultdict(list)
        self._cache: dict[tuple[str, str], EntityResolution] = {}
        self._provenance: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self._llm_client = llm_client

    def register(self, canonical_name: str, entity_type: str, document_name: str | None = None) -> None:
        """Register a known canonical entity and invalidate affected misses."""

        if canonical_name not in self._registry[entity_type]:
            self._registry[entity_type].append(canonical_name)
            self._invalidate_entity_type(entity_type)
        if document_name:
            self._provenance[entity_type][canonical_name].add(document_name)

    def registered_entities(self, entity_type: str) -> list[str]:
        """Return a copy of the known canonical entities for one type."""

        return list(self._registry[entity_type])

    def resolve(
        self,
        name: str,
        entity_type: str,
        *,
        candidates: Iterable[str] | None = None,
        bundle_context: Iterable[str] | None = None,
    ) -> EntityResolution:
        """Resolve a candidate using exact normalized matching and rule-based checks."""

        candidate_names = list(candidates) if candidates is not None else list(self._registry[entity_type])
        cache_key = (normalize_entity_name(name), entity_type)
        if candidates is None and cache_key in self._cache:
            return self._cache[cache_key].model_copy(update={"cache_hit": True})

        normalized_name = normalize_entity_name(name)
        stripped_name = strip_roles(name)
        exact_matches = []
        for candidate_name in candidate_names:
            if normalize_entity_name(candidate_name) == normalized_name:
                exact_matches.append(candidate_name)
            elif normalize_entity_name(strip_roles(candidate_name)) == normalize_entity_name(stripped_name):
                exact_matches.append(candidate_name)
            elif entity_type == "person" and person_match(name, candidate_name):
                exact_matches.append(candidate_name)

        exact_matches = list(dict.fromkeys(exact_matches))

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
            resolution = self._resolve_fuzzy(name, entity_type, candidate_names, bundle_context=bundle_context)
            if resolution.status == "unconfirmed_node":
                if 0.60 <= resolution.confidence <= 0.85:
                    resolution = self._resolve_with_llm(name, entity_type, candidate_names)

        if candidates is None:
            self._cache[cache_key] = resolution
        return resolution

    def _resolve_fuzzy(
        self,
        name: str,
        entity_type: str,
        candidates: list[str],
        bundle_context: Iterable[str] | None = None,
    ) -> EntityResolution:
        scored_candidates = []
        for candidate_name in candidates:
            score = _similarity_ratio(name, candidate_name)
            if bundle_context and hasattr(self, "_provenance"):
                cand_docs = self._provenance[entity_type].get(candidate_name, set())
                if cand_docs & set(bundle_context):
                    score = min(score + 0.05, 1.0)
            scored_candidates.append((candidate_name, score))

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
            else:
                return EntityResolution(
                    original_name=name,
                    canonical_name=name,
                    entity_type=entity_type,
                    status="unconfirmed_node",
                    confidence=highest_score,
                    reason="no_unique_fuzzy_match",
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
        canonical_name = llm_resolution.canonical_name
        if canonical_name is None or canonical_name not in candidates:
            return _unconfirmed_resolution(name, entity_type, reason="llm_returned_unknown_canonical_name")
        return EntityResolution(
            original_name=name,
            canonical_name=canonical_name,
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


def strip_roles(name: str) -> str:
    """Clean corporate roles and titles from an entity name."""
    roles = {"ceo", "cfo", "director", "president", "founder", "co-founder", "chairman", "vice president", "secretary", "treasurer"}
    words = name.casefold().split()
    cleaned_words = [w for w in words if w.strip(".,()") not in roles]
    if not cleaned_words:
        return name
    return " ".join(cleaned_words)


def person_match(name1: str, name2: str) -> bool:
    """Check if name1 and name2 refer to the same person using initials and last names."""
    n1 = re.sub(r"[^\w\s]", " ", name1.lower()).split()
    n2 = re.sub(r"[^\w\s]", " ", name2.lower()).split()
    if not n1 or not n2:
        return False
    if len(n1) == 2 and len(n2) == 2:
        if n1[1] == n2[1]:
            f1, f2 = n1[0], n2[0]
            if (len(f1) == 1 and f2.startswith(f1)) or (len(f2) == 1 and f1.startswith(f2)):
                return True
        elif n1[1] == n2[0]:
            f1, f2 = n1[0], n2[1]
            if (len(f1) == 1 and f2.startswith(f1)) or (len(f2) == 1 and f1.startswith(f2)):
                return True
        elif n1[0] == n2[1]:
            f1, f2 = n1[1], n2[0]
            if (len(f1) == 1 and f2.startswith(f1)) or (len(f2) == 1 and f1.startswith(f2)):
                return True
        elif n1[0] == n2[0]:
            f1, f2 = n1[1], n2[1]
            if (len(f1) == 1 and f2.startswith(f1)) or (len(f2) == 1 and f1.startswith(f2)):
                return True
    return False


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
