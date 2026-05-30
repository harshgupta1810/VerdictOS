"""Elasticsearch Index Management.

Handles index lifecycle operations: creation, mapping configuration,
incremental updates, and deletion.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, cast

from elasticsearch.helpers import bulk as elasticsearch_bulk

from src.common.exceptions import SearchEngineError
from src.ingestion.schemas import DocumentChunk
from src.search.schemas import IndexedChunk, IndexingOutcome

DOCUMENT_INDEX_MAPPING = {
    "properties": {
        "chunk_id": {"type": "keyword"},
        "document_name": {"type": "keyword"},
        "text": {"type": "text"},
        "section_id": {"type": "keyword"},
        "absolute_page": {"type": "integer"},
        "clause_type": {"type": "keyword"},
        "references_sections": {"type": "keyword"},
    }
}
BulkWriter = Callable[..., tuple[int, list[dict[str, object]]]]


class ElasticsearchIndexer:
    """Manage the lifecycle of the vectorless document index."""

    def __init__(
        self,
        client: Any,
        *,
        index_name: str,
        bulk_writer: BulkWriter | None = None,
    ) -> None:
        self._client = client
        self.index_name = index_name
        self._bulk_writer = bulk_writer or cast(BulkWriter, elasticsearch_bulk)

    def ensure_index(self) -> bool:
        """Create the document index when it does not already exist."""

        if self._client.indices.exists(index=self.index_name):
            return False
        self._client.indices.create(index=self.index_name, mappings=DOCUMENT_INDEX_MAPPING)
        return True

    def index_chunks(self, chunks: Iterable[DocumentChunk]) -> IndexingOutcome:
        """Incrementally upsert chunks using deterministic source chunk IDs."""

        indexed_chunks = [IndexedChunk.from_document_chunk(chunk) for chunk in chunks]
        actions = [
            {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": chunk.chunk_id,
                "_source": chunk.model_dump(mode="json"),
            }
            for chunk in indexed_chunks
        ]
        if not actions:
            return IndexingOutcome(attempted=0, indexed=0)

        try:
            indexed, errors = self._bulk_writer(
                self._client,
                actions,
                raise_on_error=False,
            )
        except Exception as exc:
            raise SearchEngineError("Elasticsearch bulk indexing failed") from exc
        return IndexingOutcome(
            attempted=len(actions),
            indexed=indexed,
            errors=errors,
        )
