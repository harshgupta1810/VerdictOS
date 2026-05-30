"""Tests for section-aware document chunker."""

from src.ingestion.chunker import SectionAwareChunker, count_tokens, extract_section_references, split_clauses
from src.ingestion.schemas import ParsedDocument, ParsedPage


def test_split_clauses_uses_period_semicolon_and_newline_boundaries() -> None:
    assert split_clauses("First clause. Second clause; Third clause\nFourth clause") == [
        "First clause.",
        "Second clause;",
        "Third clause",
        "Fourth clause",
    ]


def test_extract_section_references_deduplicates_case_insensitively() -> None:
    assert extract_section_references("See Section 9.4 and section 9.4 plus Article 2.1(b).") == [
        "Section 9.4",
        "Article 2.1(b)",
    ]


def test_chunker_tracks_sections_pages_references_and_non_overlapping_text() -> None:
    document = _document(
        [
            "Section 1. Assets\nAsset clause refers to Section 9.4; another asset clause.",
            "Section 2. Privacy\nPrivacy clause refers to Article 2.1(b).",
        ]
    )

    chunks = SectionAwareChunker().chunk(document)

    assert [(chunk.section_id, chunk.absolute_page) for chunk in chunks] == [
        ("Section 1", 0),
        ("Section 2", 1),
    ]
    assert chunks[0].references_sections == ["Section 1", "Section 9.4"]
    assert chunks[1].references_sections == ["Section 2", "Article 2.1(b)"]
    assert "Asset clause" in chunks[0].text
    assert "Privacy clause" not in chunks[0].text


def test_chunker_groups_clauses_into_bounded_chunks_without_overlap() -> None:
    clauses = [f"clause{i} " + " ".join(f"word{i}_{word}" for word in range(58)) + "." for i in range(12)]
    document = _document([" ".join(clauses)])

    chunks = SectionAwareChunker().chunk(document)

    assert len(chunks) == 2
    assert all(200 <= count_tokens(chunk.text) <= 500 for chunk in chunks)
    assert "clause0" in chunks[0].text
    assert "clause0" not in chunks[1].text


def test_chunker_splits_individually_oversized_clauses_and_keeps_short_documents() -> None:
    oversized = " ".join(f"word{index}" for index in range(1100))
    oversized_chunks = SectionAwareChunker().chunk(_document([oversized]))
    short_chunks = SectionAwareChunker().chunk(_document(["Short agreement."]))

    assert [count_tokens(chunk.text) for chunk in oversized_chunks] == [500, 500, 100]
    assert len(short_chunks) == 1
    assert short_chunks[0].text == "Short agreement."


def test_chunker_merges_undersized_trailing_group_into_previous_same_section() -> None:
    # Build one large clause (~300 tokens) followed by a tiny one (~5 tokens),
    # both in the same section/page. The tiny group should be folded up.
    big_clause = " ".join(f"word{i}" for i in range(300))
    small_clause = "Short tail clause."
    document = _document([f"{big_clause} {small_clause}"])

    chunks = SectionAwareChunker(min_tokens=200, max_tokens=500).chunk(document)

    # The trailing short clause should be merged into the preceding chunk.
    assert len(chunks) == 1
    assert "Short tail clause" in chunks[0].text


def test_chunker_does_not_merge_across_section_boundaries() -> None:
    # Two sections: each has content, the second section only has a tiny clause.
    # The tiny clause must NOT merge into the first section's chunk.
    big_clause = " ".join(f"word{i}" for i in range(250))
    document = _document(
        [
            f"Section 1. Assets\n{big_clause}",
            "Section 2. Privacy\nTiny.",
        ]
    )

    chunks = SectionAwareChunker(min_tokens=200, max_tokens=500).chunk(document)

    assert len(chunks) == 2
    assert chunks[0].section_id == "Section 1"
    assert chunks[1].section_id == "Section 2"


def test_chunker_rejects_invalid_bounds() -> None:
    try:
        SectionAwareChunker(min_tokens=0)
    except ValueError as exc:
        assert str(exc) == "min_tokens must be positive"
    else:
        raise AssertionError("expected invalid min_tokens to fail")

    try:
        SectionAwareChunker(min_tokens=500, max_tokens=200)
    except ValueError as exc:
        assert str(exc) == "max_tokens must be greater than or equal to min_tokens"
    else:
        raise AssertionError("expected invalid max_tokens to fail")


def _document(pages: list[str]) -> ParsedDocument:
    return ParsedDocument(
        document_name="agreement.pdf",
        source_path="agreement.pdf",
        document_type="pdf",
        raw_pages=[ParsedPage(page_index=index, text=text) for index, text in enumerate(pages)],
    )


def test_defined_terms_extraction() -> None:
    from src.ingestion.defined_terms import DefinedTermsExtractor
    from src.ingestion.schemas import DocumentChunk

    document = ParsedDocument(
        document_name="agreement.pdf",
        source_path="agreement.pdf",
        document_type="pdf",
        raw_pages=[
            ParsedPage(
                page_index=0,
                text=(
                    "Section 1. Definitions\n"
                    '\"Affiliate\" shall mean any entity that controls Acme.\n'
                    '\"Intellectual Property\" means all patents and trademarks.\n'
                    "Section 2. Assets\n"
                    "This section lists assets."
                )
            )
        ]
    )

    extractor = DefinedTermsExtractor()
    definitions = extractor.extract_definitions(document)

    assert "Affiliate" in definitions
    assert definitions["Affiliate"] == "any entity that controls Acme"
    assert "Intellectual Property" in definitions
    assert definitions["Intellectual Property"] == "all patents and trademarks"

    chunk1 = DocumentChunk(
        chunk_id="chunk:1",
        document_name="agreement.pdf",
        chunk_index=0,
        text="The Affiliate of the vendor is Acme Holdings.",
        section_id="Section 2",
        absolute_page=0
    )
    chunk2 = DocumentChunk(
        chunk_id="chunk:2",
        document_name="agreement.pdf",
        chunk_index=1,
        text="This is an unrelated chunk.",
        section_id="Section 2",
        absolute_page=0
    )

    mapped = extractor.map_defined_terms_to_chunks([chunk1, chunk2], definitions)
    assert "Affiliate" in mapped[0].defined_terms
    assert mapped[0].defined_terms["Affiliate"] == "any entity that controls Acme"
    assert "Intellectual Property" not in mapped[0].defined_terms
    assert mapped[1].defined_terms == {}

