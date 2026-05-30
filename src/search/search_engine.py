"""Sparse Retrieval Engine (Elasticsearch BM25).

Exposes search methods for exact term matching with structured
paragraph citations. Supports synonym expansion and taxonomy filters.

Technologies: elasticsearch
"""

from __future__ import annotations

from typing import Any

from src.common.exceptions import SearchEngineError
from src.search.schemas import IndexedChunk, SearchQuery, SearchResult


class SparseSearchEngine:
    """Run vectorless Elasticsearch BM25 queries."""

    def __init__(self, client: Any, *, index_name: str) -> None:
        self._client = client
        self.index_name = index_name

    def search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute BM25 search and return structured paragraph citations."""

        import re
        section_pattern = re.compile(r"\b(?:Section|Article)\s+\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*", re.IGNORECASE)
        match = section_pattern.search(query.text)
        if match:
            section_id = match.group(0)
            section_results = self.resolve_section_reference(
                section_id,
                document_name=query.filters.document_name
            )
            if section_results:
                if query.filters.clause_types:
                    clause_vals = {ct.value for ct in query.filters.clause_types}
                    section_results = [r for r in section_results if r.clause_type.value in clause_vals]
                return section_results[:query.size]

        request = build_search_request(query)
        try:
            response = self._client.search(index=self.index_name, **request)
        except Exception as exc:
            raise SearchEngineError("Elasticsearch search failed") from exc

        results = []
        for hit in response.get("hits", {}).get("hits", []):
            indexed_chunk = IndexedChunk.model_validate(hit["_source"])
            results.append(
                SearchResult(
                    chunk_id=indexed_chunk.chunk_id,
                    score=float(hit.get("_score") or 0.0),
                    document_name=indexed_chunk.document_name,
                    text=indexed_chunk.text,
                    section_id=indexed_chunk.section_id,
                    absolute_page=indexed_chunk.absolute_page,
                    clause_type=indexed_chunk.clause_type,
                    references_sections=indexed_chunk.references_sections,
                    highlights=hit.get("highlight", {}).get("text", []),
                )
            )
        return results

    def resolve_section_reference(self, section_id: str, document_name: str | None = None) -> list[SearchResult]:
        """Directly query the index for chunks matching a section_id keyword."""

        filters = [{"term": {"section_id": section_id}}]
        if document_name:
            filters.append({"term": {"document_name": document_name}})

        request = {
            "query": {
                "bool": {
                    "filter": filters
                }
            },
            "size": 50
        }

        try:
            response = self._client.search(index=self.index_name, **request)
        except Exception as exc:
            raise SearchEngineError(f"Elasticsearch section resolve failed: {exc}") from exc

        results = []
        for hit in response.get("hits", {}).get("hits", []):
            indexed_chunk = IndexedChunk.model_validate(hit["_source"])
            results.append(
                SearchResult(
                    chunk_id=indexed_chunk.chunk_id,
                    score=float(hit.get("_score") or 1.0),
                    document_name=indexed_chunk.document_name,
                    text=indexed_chunk.text,
                    section_id=indexed_chunk.section_id,
                    absolute_page=indexed_chunk.absolute_page,
                    clause_type=indexed_chunk.clause_type,
                    references_sections=indexed_chunk.references_sections,
                    highlights=[],
                )
            )
        return results

    def fetch_sections(
        self,
        section_ids: list[str],
        *,
        document_name: str | None = None,
        size: int = 10,
    ) -> list[SearchResult]:
        """Fetch chunks belonging to the given section IDs without BM25 scoring.

        Used by the section pointer resolver to follow cross-references found
        in initial BM25 results (e.g. 'see Section 4.2').
        """
        filters: list[dict[str, object]] = [{"terms": {"section_id": section_ids}}]
        if document_name:
            filters.append({"term": {"document_name": document_name}})

        request: dict[str, object] = {
            "query": {"bool": {"filter": filters}},
            "size": size,
        }

        try:
            response = self._client.search(index=self.index_name, **request)
        except Exception as exc:
            raise SearchEngineError("Elasticsearch section fetch failed") from exc

        results = []
        for hit in response.get("hits", {}).get("hits", []):
            indexed_chunk = IndexedChunk.model_validate(hit["_source"])
            results.append(
                SearchResult(
                    chunk_id=indexed_chunk.chunk_id,
                    score=0.0,
                    document_name=indexed_chunk.document_name,
                    text=indexed_chunk.text,
                    section_id=indexed_chunk.section_id,
                    absolute_page=indexed_chunk.absolute_page,
                    clause_type=indexed_chunk.clause_type,
                    references_sections=indexed_chunk.references_sections,
                    highlights=[],
                )
            )
        return results


def build_search_request(query: SearchQuery) -> dict[str, Any]:
    """Build an Elasticsearch request using sparse text terms and exact filters."""

    filters: list[dict[str, object]] = []
    if query.filters.document_name:
        filters.append({"term": {"document_name": query.filters.document_name}})
    if query.filters.clause_types:
        filters.append(
            {
                "terms": {
                    "clause_type": [
                        clause_type.value
                        for clause_type in query.filters.clause_types
                    ]
                }
            }
        )

    if query.expanded_terms:
        text_query: dict[str, object] = {
            "bool": {
                "should": [
                    {"match_phrase": {"text": term}}
                    for term in [query.text, *query.expanded_terms]
                ],
                "minimum_should_match": 1,
            }
        }
    else:
        text_query = {"match": {"text": {"query": query.text, "operator": "and"}}}

    return {
        "query": {
            "bool": {
                "must": [text_query],
                "filter": filters,
            }
        },
        "highlight": {"fields": {"text": {}}},
        "size": query.size,
    }
