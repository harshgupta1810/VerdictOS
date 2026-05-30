import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, cast
from elasticsearch.helpers import bulk as elasticsearch_bulk


from src.common.exceptions import SearchEngineError
from src.ingestion.schemas import DocumentChunk
from src.search.schemas import IndexedChunk, IndexingOutcome

DEFAULT_CACHE_PATH = "data/bm25_index_cache.json"

DOCUMENT_INDEX_MAPPING = {
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
BulkWriter = Callable[..., tuple[int, list[dict[str, object]]]]


def get_synonym_list() -> list[str]:
    """Compile agent synonym groups into a format accepted by Elasticsearch."""
    try:
        from src.agents.planner_agent import AGENT_SYNONYMS
        synonyms = []
        for agent_name, groups in AGENT_SYNONYMS.items():
            for term, syns in groups.items():
                group = [term] + syns
                clean_group = list(dict.fromkeys(s.strip().lower() for s in group if s.strip()))
                if len(clean_group) > 1:
                    synonyms.append(", ".join(clean_group))
        return synonyms
    except ImportError:
        return []


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

        synonyms = get_synonym_list()
        settings = {
            "index": {
                "analysis": {
                    "filter": {
                        "synonym_filter": {
                            "type": "synonym",
                            "synonyms": synonyms,
                        }
                    },
                    "analyzer": {
                        "synonym_analyzer": {
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "synonym_filter",
                            ],
                        }
                    },
                }
            }
        }

        self._client.indices.create(
            index=self.index_name,
            settings=settings,
            mappings=DOCUMENT_INDEX_MAPPING,
        )
        return True

    def index_chunks(self, chunks: Iterable[DocumentChunk]) -> IndexingOutcome:
        """Incrementally upsert chunks using deterministic source chunk IDs."""

        chunk_list = list(chunks)
        indexed_chunks = [IndexedChunk.from_document_chunk(chunk) for chunk in chunk_list]
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

        outcome = IndexingOutcome(
            attempted=len(actions),
            indexed=indexed,
            errors=errors,
        )

        if outcome.indexed > 0 and not outcome.errors:
            self.save_index_cache(chunk_list)

        return outcome

    def save_index_cache(self, chunks: list[DocumentChunk], filepath: str = DEFAULT_CACHE_PATH) -> None:
        """Save a list of chunks to a local JSON cache file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        existing[item["chunk_id"]] = item
            except Exception:
                pass

        for chunk in chunks:
            existing[chunk.chunk_id] = chunk.model_dump(mode="json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(existing.values()), f, indent=2)

    def load_index_cache(self, filepath: str = DEFAULT_CACHE_PATH) -> list[DocumentChunk]:
        """Load chunks from the local JSON cache."""
        path = Path(filepath)
        if not path.is_file():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DocumentChunk.model_validate(item) for item in data]
        except Exception:
            return []

