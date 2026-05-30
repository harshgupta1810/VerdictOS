"""Pydantic schemas for document ingestion pipeline.

Defines data contracts for parsed documents, chunk metadata,
and classifier outputs.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.common.models import ClauseType


class LayoutElement(BaseModel):
    """A provenance-backed unit extracted from a source document."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["word", "paragraph", "table", "heading"]
    text: str = Field(min_length=1)
    source_index: int | None = Field(default=None, ge=0)
    x0: float | None = Field(default=None, ge=0)
    top: float | None = Field(default=None, ge=0)
    x1: float | None = Field(default=None, ge=0)
    bottom: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "LayoutElement":
        """Require PDF coordinates as a complete, ordered set when present."""

        coordinates = (self.x0, self.top, self.x1, self.bottom)
        if any(value is not None for value in coordinates) and not all(value is not None for value in coordinates):
            raise ValueError("layout coordinates must be supplied together")
        if self.x0 is not None and self.x1 is not None and self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0")
        if self.top is not None and self.bottom is not None and self.bottom < self.top:
            raise ValueError("bottom must be greater than or equal to top")
        return self


class ParsedPage(BaseModel):
    """Text and ordered layout metadata extracted from one logical page."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(ge=0)
    text: str
    layout_info: list[LayoutElement] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """Normalized parser output shared by PDF and DOCX adapters."""

    model_config = ConfigDict(extra="forbid")

    document_name: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    document_type: Literal["pdf", "docx"]
    raw_pages: list[ParsedPage] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """A section-aware chunk ready for classification and indexing."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    absolute_page: int = Field(ge=0)
    references_sections: list[str] = Field(default_factory=list)
    clause_type: ClauseType = ClauseType.GENERAL
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
    defined_terms: dict[str, str] = Field(default_factory=dict)



class ClassificationResult(BaseModel):
    """Rule-based classification output for a document chunk."""

    model_config = ConfigDict(extra="forbid")

    clause_type: ClauseType
    confidence: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
