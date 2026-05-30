"""Pydantic schemas for search requests and responses.

Defines data contracts for search queries, filter parameters,
and search result payloads.
"""

from pydantic import BaseModel, ConfigDict, Field

from src.common.models import ClauseType
from src.ingestion.schemas import DocumentChunk


class IndexedChunk(BaseModel):
    """Canonical Elasticsearch document stored for each source chunk."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    absolute_page: int = Field(ge=0)
    clause_type: ClauseType
    references_sections: list[str] = Field(default_factory=list)
    defined_terms: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_document_chunk(cls, chunk: DocumentChunk) -> "IndexedChunk":
        return cls(
            chunk_id=chunk.chunk_id,
            document_name=chunk.document_name,
            text=chunk.text,
            section_id=chunk.section_id,
            absolute_page=chunk.absolute_page,
            clause_type=chunk.clause_type,
            references_sections=chunk.references_sections,
            defined_terms=chunk.defined_terms,
        )



class IndexingOutcome(BaseModel):
    """Summary returned after incremental bulk indexing."""

    model_config = ConfigDict(extra="forbid")

    attempted: int = Field(ge=0)
    indexed: int = Field(ge=0)
    errors: list[dict[str, object]] = Field(default_factory=list)


class SearchFilters(BaseModel):
    """Optional exact filters applied alongside BM25 matching."""

    model_config = ConfigDict(extra="forbid")

    document_name: str | None = None
    clause_types: list[ClauseType] = Field(default_factory=list)


class SearchQuery(BaseModel):
    """Sparse retrieval query contract."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    expanded_terms: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    size: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    """Structured BM25 search hit with paragraph citation metadata."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    document_name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    absolute_page: int = Field(ge=0)
    clause_type: ClauseType
    references_sections: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
