"""Defined Terms Extractor.

Parses definitions section of contracts, extracts terms and definitions, and maps them to chunk metadata.
"""

import re
from src.ingestion.schemas import ParsedDocument, DocumentChunk


class DefinedTermsExtractor:
    """Extract defined terms from document definitions section and map to chunks."""

    def extract_definitions(self, document: ParsedDocument) -> dict[str, str]:
        """Locate Definitions section and parse defined terms."""
        in_definitions = False
        definitions_text_parts = []

        # Headers like: Section 1. Definitions, Article I DEFINITIONS, etc.
        section_header_re = re.compile(
            r"^\s*(?:Section|Article|Appendix)\s*\d*(?:\.\d*)*\s*(?:DEFINITIONS|Definitions)\b",
            re.IGNORECASE,
        )
        next_section_header_re = re.compile(
            r"^\s*(?:Section|Article|Appendix)\s*\d*(?:\.\d*)*\s*(?!(?:DEFINITIONS|Definitions)\b)[A-Z0-9]",
            re.IGNORECASE,
        )

        for page in document.raw_pages:
            for line in page.text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if section_header_re.match(stripped):
                    in_definitions = True
                    definitions_text_parts.append(stripped)
                    continue
                if in_definitions:
                    if next_section_header_re.match(stripped) or (
                        stripped.isupper()
                        and len(stripped) < 40
                        and "DEFINITIONS" not in stripped.upper()
                    ):
                        in_definitions = False
                        break
                    definitions_text_parts.append(stripped)
            if in_definitions is False and definitions_text_parts:
                break

        definitions_text = "\n".join(definitions_text_parts)

        # Parse definitions line by line
        quoted_pattern = re.compile(
            r'["\'“”‘’]([^"\'“”‘’]{2,50})["\'“”‘’]\s+(?:shall\s+)?(?:means?|have\s+the\s+meaning|refers\s+to)\s+([^.;\n]+)',
            re.IGNORECASE,
        )
        unquoted_pattern = re.compile(
            r'^\s*([A-Z][A-Za-z0-9\s]{1,49})\s+(?:shall\s+)?(?:means?|have\s+the\s+meaning|refers\s+to)\s+([^.;\n]+)',
            re.IGNORECASE,
        )

        defined_terms = {}
        for line in definitions_text.splitlines():
            # Try quoted first
            match = quoted_pattern.search(line)
            if not match:
                # Try unquoted
                match = unquoted_pattern.search(line)
            if match:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                if term and len(term) >= 2:
                    defined_terms[term] = definition

        return defined_terms

    def map_defined_terms_to_chunks(
        self,
        chunks: list[DocumentChunk],
        definitions: dict[str, str],
    ) -> list[DocumentChunk]:
        """Identify occurrences of defined terms inside chunk text and map them."""
        if not definitions:
            return chunks

        mapped_chunks = []
        for chunk in chunks:
            chunk_defined = {}
            for term, definition in definitions.items():
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, chunk.text):
                    chunk_defined[term] = definition
            mapped_chunks.append(chunk.model_copy(update={"defined_terms": chunk_defined}))
        return mapped_chunks
