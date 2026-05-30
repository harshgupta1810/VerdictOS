"""Section-Aware Document Chunker.

Segments document text at clause/sentence boundaries (200-500 tokens)
with structural metadata preservation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.ingestion.schemas import DocumentChunk, ParsedDocument

_CLAUSE_BOUNDARY_RE = re.compile(r"(?<=[.;])\s+|\r?\n+")
_TOKEN_RE = re.compile(r"\b[\w]+(?:[-'][\w]+)*\b")
_SECTION_REFERENCE_RE = re.compile(
    r"\b(?:Section|Article)\s+\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*",
    re.IGNORECASE,
)
_SECTION_PREFIX_RE = re.compile(
    r"^\s*((?:Section|Article)\s+\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)\b(.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Clause:
    text: str
    section_id: str
    absolute_page: int


class SectionAwareChunker:
    """Create deterministic chunks without splitting ordinary clauses."""

    def __init__(self, *, min_tokens: int = 200, max_tokens: int = 500) -> None:
        if min_tokens <= 0:
            raise ValueError("min_tokens must be positive")
        if max_tokens < min_tokens:
            raise ValueError("max_tokens must be greater than or equal to min_tokens")
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        """Split a parsed document into non-overlapping section-aware chunks."""

        clauses = self._extract_clauses(document)
        chunk_groups: list[list[_Clause]] = []
        current_group: list[_Clause] = []
        current_tokens = 0

        for clause in clauses:
            clause_tokens = count_tokens(clause.text)
            crosses_boundary = bool(
                current_group
                and (
                    current_group[-1].section_id != clause.section_id
                    or current_group[-1].absolute_page != clause.absolute_page
                )
            )
            exceeds_limit = bool(current_group and current_tokens + clause_tokens > self.max_tokens)
            if crosses_boundary or exceeds_limit:
                chunk_groups.append(current_group)
                current_group = []
                current_tokens = 0
            current_group.append(clause)
            current_tokens += clause_tokens

        if current_group:
            chunk_groups.append(current_group)

        # Merge-up pass: fold undersized trailing groups into the previous group
        # when they share the same section and the merged result fits within max_tokens.
        merged_groups: list[list[_Clause]] = []
        for group in chunk_groups:
            if (
                merged_groups
                and count_tokens(" ".join(c.text for c in group)) < self.min_tokens
                and merged_groups[-1][0].section_id == group[0].section_id
                and merged_groups[-1][0].absolute_page == group[0].absolute_page
            ):
                combined_tokens = count_tokens(
                    " ".join(c.text for c in merged_groups[-1] + group)
                )
                if combined_tokens <= self.max_tokens:
                    merged_groups[-1].extend(group)
                    continue
            merged_groups.append(group)

        return [
            self._build_chunk(document.document_name, chunk_index, group)
            for chunk_index, group in enumerate(merged_groups)
        ]

    def _extract_clauses(self, document: ParsedDocument) -> list[_Clause]:
        clauses: list[_Clause] = []
        active_section = "document_root"

        for page in document.raw_pages:
            for line in page.text.splitlines():
                text = line.strip()
                if not text:
                    continue
                section_id = _detect_section_header(text)
                if section_id:
                    active_section = section_id
                for clause_text in split_clauses(text):
                    for bounded_text in _split_oversized_clause(clause_text, self.max_tokens):
                        clauses.append(
                            _Clause(
                                text=bounded_text,
                                section_id=active_section,
                                absolute_page=page.page_index,
                            )
                        )
        return clauses

    @staticmethod
    def _build_chunk(document_name: str, chunk_index: int, clauses: list[_Clause]) -> DocumentChunk:
        text = " ".join(clause.text for clause in clauses)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return DocumentChunk(
            chunk_id=f"{document_name}:{chunk_index}:{digest}",
            document_name=document_name,
            chunk_index=chunk_index,
            text=text,
            section_id=clauses[0].section_id,
            absolute_page=clauses[0].absolute_page,
            references_sections=extract_section_references(text),
        )


def split_clauses(text: str) -> list[str]:
    """Split text at semantic clause boundaries while retaining punctuation."""

    return [part.strip() for part in _CLAUSE_BOUNDARY_RE.split(text) if part.strip()]


def extract_section_references(text: str) -> list[str]:
    """Extract unique cross-reference pointers in first-seen order."""

    references: list[str] = []
    seen: set[str] = set()
    for match in _SECTION_REFERENCE_RE.finditer(text):
        reference = match.group(0)
        key = reference.casefold()
        if key not in seen:
            seen.add(key)
            references.append(reference)
    return references


def count_tokens(text: str) -> int:
    """Count lightweight lexical tokens without introducing a model tokenizer."""

    return len(_TOKEN_RE.findall(text))


def _detect_section_header(text: str) -> str | None:
    match = _SECTION_PREFIX_RE.match(text)
    if not match:
        return None
    remainder = match.group(2).strip(" .:-")
    if remainder and (len(remainder.split()) > 12 or remainder.endswith((".", ";"))):
        return None
    return match.group(1)


def _split_oversized_clause(text: str, max_tokens: int) -> list[str]:
    matches = list(_TOKEN_RE.finditer(text))
    if len(matches) <= max_tokens:
        return [text]

    parts: list[str] = []
    for start in range(0, len(matches), max_tokens):
        end = min(start + max_tokens, len(matches))
        start_offset = matches[start].start()
        end_offset = matches[end].start() if end < len(matches) else len(text)
        parts.append(text[start_offset:end_offset].strip())
    return parts
