"""Tests for Elasticsearch indexing and search."""

import pytest
from pathlib import Path
from typing import Any

import src.search.client as client_module
from src.common.exceptions import SearchEngineError
from src.common.models import ClauseType
from src.ingestion.schemas import DocumentChunk
from src.search.client import create_elasticsearch_client
from src.search.indexer import DOCUMENT_INDEX_MAPPING, ElasticsearchIndexer
from src.search.schemas import SearchFilters, SearchQuery
from src.search.search_engine import SparseSearchEngine, build_search_request


class _Indices:
    def __init__(self, *, exists: bool = False) -> None:
        self._exists = exists
        self.created: list[dict[str, Any]] = []

    def exists(self, *, index: str) -> bool:
        return self._exists

    def create(self, **kwargs: Any) -> None:
        self.created.append(kwargs)


class _Client:
    def __init__(self, *, index_exists: bool = False) -> None:
        self.indices = _Indices(exists=index_exists)


class _SearchClient:
    def __init__(self, response: dict[str, Any] | Exception) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_create_elasticsearch_client_uses_configured_local_url(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_urls: list[str] = []

    def elasticsearch(url: str) -> object:
        captured_urls.append(url)
        return object()

    monkeypatch.setattr(client_module, "Elasticsearch", elasticsearch)

    client = create_elasticsearch_client()

    assert client is not None
    assert captured_urls == ["http://localhost:9200"]


def test_index_mapping_uses_canonical_clause_type_and_structural_fields() -> None:
    assert DOCUMENT_INDEX_MAPPING == {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "document_name": {"type": "keyword"},
            "text": {
                "type": "text",
                "analyzer": "synonym_analyzer",
                "search_analyzer": "synonym_analyzer",
            },
            "section_id": {"type": "keyword"},
            "absolute_page": {"type": "integer"},
            "clause_type": {"type": "keyword"},
            "references_sections": {"type": "keyword"},
            "defined_terms": {"type": "object", "enabled": False},
        }
    }


def test_ensure_index_creates_missing_index_with_mapping() -> None:
    client = _Client()

    created = ElasticsearchIndexer(client, index_name="verdictos_documents").ensure_index()

    assert created is True
    assert len(client.indices.created) == 1
    created_index = client.indices.created[0]
    assert created_index["index"] == "verdictos_documents"
    assert created_index["mappings"] == DOCUMENT_INDEX_MAPPING
    assert "settings" in created_index
    assert "synonym_analyzer" in created_index["settings"]["index"]["analysis"]["analyzer"]


def test_ensure_index_keeps_existing_index() -> None:
    client = _Client(index_exists=True)

    created = ElasticsearchIndexer(client, index_name="verdictos_documents").ensure_index()

    assert created is False
    assert client.indices.created == []


def test_index_chunks_uses_deterministic_ids_for_incremental_upserts() -> None:
    captured_actions: list[dict[str, Any]] = []

    def bulk_writer(_client: object, actions: list[dict[str, Any]], **_kwargs: Any) -> tuple[int, list[dict[str, Any]]]:
        captured_actions.extend(actions)
        return len(actions), []

    indexer = ElasticsearchIndexer(
        _Client(),
        index_name="verdictos_documents",
        bulk_writer=bulk_writer,
    )
    chunk = _chunk(chunk_id="agreement:0:stable", text="First version.")

    first_outcome = indexer.index_chunks([chunk])
    second_outcome = indexer.index_chunks([chunk.model_copy(update={"text": "Updated version."})])

    assert first_outcome.indexed == 1
    assert second_outcome.indexed == 1
    assert [action["_id"] for action in captured_actions] == ["agreement:0:stable", "agreement:0:stable"]
    assert captured_actions[1]["_source"]["text"] == "Updated version."


def test_index_chunks_adds_supplemental_documents_without_rebuild() -> None:
    captured_actions: list[dict[str, Any]] = []

    def bulk_writer(_client: object, actions: list[dict[str, Any]], **_kwargs: Any) -> tuple[int, list[dict[str, Any]]]:
        captured_actions.extend(actions)
        return len(actions), []

    indexer = ElasticsearchIndexer(_Client(), index_name="verdictos_documents", bulk_writer=bulk_writer)

    outcome = indexer.index_chunks(
        [
            _chunk(chunk_id="first:0", document_name="first.pdf"),
            _chunk(chunk_id="supplement:0", document_name="supplement.pdf"),
        ]
    )

    assert outcome.attempted == 2
    assert outcome.indexed == 2
    assert [action["_source"]["document_name"] for action in captured_actions] == ["first.pdf", "supplement.pdf"]


def test_index_chunks_reports_bulk_errors_and_accepts_empty_batches() -> None:
    error = {"index": {"_id": "bad", "error": "failure"}}

    def bulk_writer(_client: object, _actions: list[dict[str, object]], **_kwargs: object) -> tuple[int, list[dict]]:
        return 0, [error]

    indexer = ElasticsearchIndexer(_Client(), index_name="verdictos_documents", bulk_writer=bulk_writer)

    failed = indexer.index_chunks([_chunk(chunk_id="bad")])
    empty = indexer.index_chunks([])

    assert failed.errors == [error]
    assert empty.model_dump() == {"attempted": 0, "indexed": 0, "errors": []}


def test_build_search_request_uses_bm25_text_query_and_exact_filters() -> None:
    request = build_search_request(
        SearchQuery(
            text="liability cap",
            filters=SearchFilters(
                document_name="agreement.pdf",
                clause_types=[ClauseType.LIABILITY_CAP],
            ),
            size=5,
        )
    )

    assert request == {
        "query": {
            "bool": {
                "must": [{"match": {"text": {"query": "liability cap", "operator": "and"}}}],
                "filter": [
                    {"term": {"document_name": "agreement.pdf"}},
                    {"terms": {"clause_type": ["liability_cap"]}},
                ],
            }
        },
        "highlight": {"fields": {"text": {}}},
        "size": 5,
    }


def test_search_returns_structured_results_with_highlights() -> None:
    client = _SearchClient(
        {
            "hits": {
                "hits": [
                    {
                        "_score": 2.4,
                        "_source": {
                            "chunk_id": "agreement:0",
                            "document_name": "agreement.pdf",
                            "text": "The liability cap applies.",
                            "section_id": "Section 1",
                            "absolute_page": 0,
                            "clause_type": "liability_cap",
                            "references_sections": ["Section 9.4"],
                        },
                        "highlight": {"text": ["The <em>liability cap</em> applies."]},
                    }
                ]
            }
        }
    )

    results = SparseSearchEngine(client, index_name="verdictos_documents").search(SearchQuery(text="liability cap"))

    assert len(results) == 1
    assert results[0].clause_type is ClauseType.LIABILITY_CAP
    assert results[0].highlights == ["The <em>liability cap</em> applies."]
    assert client.requests[0]["index"] == "verdictos_documents"


def test_search_returns_empty_results() -> None:
    client = _SearchClient({"hits": {"hits": []}})

    results = SparseSearchEngine(client, index_name="verdictos_documents").search(SearchQuery(text="missing"))

    assert results == []


def test_search_wraps_client_failures() -> None:
    client = _SearchClient(ConnectionError("offline"))

    with pytest.raises(SearchEngineError, match="Elasticsearch search failed"):
        SparseSearchEngine(client, index_name="verdictos_documents").search(SearchQuery(text="missing"))


def _chunk(
    *,
    chunk_id: str,
    document_name: str = "agreement.pdf",
    text: str = "The liability cap applies.",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_name=document_name,
        chunk_index=0,
        text=text,
        section_id="Section 1",
        absolute_page=0,
        clause_type=ClauseType.LIABILITY_CAP,
        references_sections=["Section 9.4"],
    )


def test_search_resolves_section_references() -> None:
    # A search client that returns hits matching Section 9.4
    client = _SearchClient(
        {
            "hits": {
                "hits": [
                    {
                        "_score": 1.0,
                        "_source": {
                            "chunk_id": "agreement:12",
                            "document_name": "agreement.pdf",
                            "text": "This is Section 9.4 about liability cap.",
                            "section_id": "Section 9.4",
                            "absolute_page": 4,
                            "clause_type": "liability_cap",
                            "references_sections": [],
                            "defined_terms": {},
                        },
                    }
                ]
            }
        }
    )

    results = SparseSearchEngine(client, index_name="verdictos_documents").search(
        SearchQuery(text="Find Section 9.4 in this deal")
    )

    assert len(results) == 1
    assert results[0].section_id == "Section 9.4"
    assert results[0].chunk_id == "agreement:12"
    # Verify that it performed a term query filter on section_id rather than a match query
    sent_request = client.requests[0]
    assert sent_request["index"] == "verdictos_documents"
    filters = sent_request["query"]["bool"]["filter"]
    assert {"term": {"section_id": "Section 9.4"}} in filters


def test_index_persistence_caching(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"

    indexer = ElasticsearchIndexer(_Client(), index_name="verdictos_documents")

    chunk1 = _chunk(chunk_id="chunk:1", text="some text 1")
    chunk2 = _chunk(chunk_id="chunk:2", text="some text 2")

    # Save cache
    indexer.save_index_cache([chunk1, chunk2], filepath=str(cache_file))

    # Load cache
    loaded = indexer.load_index_cache(filepath=str(cache_file))

    assert len(loaded) == 2
    assert loaded[0].chunk_id == "chunk:1"
    assert loaded[0].text == "some text 1"
    assert loaded[1].chunk_id == "chunk:2"


