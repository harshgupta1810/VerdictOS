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
