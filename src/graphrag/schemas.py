"""Pydantic schemas for GraphRAG entities and relationships.

Defines data contracts for graph nodes, edges, and entity
resolution results.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EntityType = Literal["organization", "person", "location", "asset", "code"]


class EntityResolution(BaseModel):
    """Auditable output of the three-tier entity resolver."""

    model_config = ConfigDict(extra="forbid")

    original_name: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    resolution_tier: Literal[1, 2, 3] | None = None
    status: Literal["confirmed", "unconfirmed_node"]
    confidence: float = Field(ge=0.0, le=1.0)
    cache_hit: bool = False
    reason: str | None = None


class LLMEntityResolution(BaseModel):
    """Strict response contract for local LLM entity disambiguation."""

    model_config = ConfigDict(extra="forbid")

    merge: bool
    canonical_name: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_canonical_name_for_merge(self) -> "LLMEntityResolution":
        if self.merge and not self.canonical_name:
            raise ValueError("canonical_name is required when merge is true")
        return self


class ExtractedEntity(BaseModel):
    """A provenance-backed named entity extracted from a document chunk."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    entity_type: EntityType
    chunk_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    absolute_page: int = Field(ge=0)
