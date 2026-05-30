"""Synchronous Phase 1 pre-flight pipeline composition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from src.agents.planner_agent import PlannerAgent
from src.agents.schemas import ActiveSpecialistManifest
from src.common.exceptions import DocumentIngestionError, SearchEngineError
from src.graphrag.graph_constructor import GraphConstructor
from src.ingestion.chunker import SectionAwareChunker
from src.ingestion.classifier import ClauseClassifier
from src.ingestion.ingest import DocumentIngestor, compute_file_fingerprint
from src.ingestion.schemas import DocumentChunk, ParsedDocument
from src.search.indexer import ElasticsearchIndexer
from typing import Protocol
from src.search.schemas import IndexingOutcome


class IndexerProtocol(Protocol):
    def ensure_index(self) -> bool: ...
    def index_chunks(self, chunks: Iterable[DocumentChunk]) -> IndexingOutcome: ...


@dataclass(frozen=True)
class PreflightResult:
    """Typed Phase 1 output passed to asynchronous orchestration."""

    documents: list[ParsedDocument]
    chunks: list[DocumentChunk]
    graph: nx.DiGraph
    indexing: IndexingOutcome
    specialist_manifest: ActiveSpecialistManifest


class PreflightPipeline:
    """Execute deterministic Phase 1 work before the event loop starts."""

    def __init__(
        self,
        *,
        ingestor: DocumentIngestor,
        chunker: SectionAwareChunker,
        classifier: ClauseClassifier,
        graph_constructor: GraphConstructor,
        indexer: IndexerProtocol,
        planner: PlannerAgent,
    ) -> None:
        self._ingestor = ingestor
        self._chunker = chunker
        self._classifier = classifier
        self._graph_constructor = graph_constructor
        self._indexer = indexer
        self._planner = planner

    def run(self, source_paths: Iterable[str | Path]) -> PreflightResult:
        """Run Phase 1 synchronously and stop on incomplete indexing."""

        paths = list(source_paths)
        if not paths:
            raise DocumentIngestionError("pre-flight requires at least one source document")

        # Deduplicate paths by calculating file fingerprint
        import hashlib
        seen_fingerprints = set()
        unique_paths = []
        for path in paths:
            if Path(path).is_file():
                fp = compute_file_fingerprint(path)
            else:
                fp = hashlib.sha256(str(path).encode()).hexdigest()
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                unique_paths.append(path)

        documents = [self._ingestor.parse(path) for path in unique_paths]

        from src.ingestion.defined_terms import DefinedTermsExtractor
        extractor = DefinedTermsExtractor()

        raw_chunks = []
        for document in documents:
            doc_definitions = extractor.extract_definitions(document)
            doc_chunks = self._chunker.chunk(document)
            mapped_chunks = extractor.map_defined_terms_to_chunks(doc_chunks, doc_definitions)
            raw_chunks.extend(mapped_chunks)

        chunks = [
            self._classifier.classify_chunk(chunk)
            for chunk in raw_chunks
        ]
        graph = self._graph_constructor.build_graph(chunks)
        self._indexer.ensure_index()
        indexing = self._indexer.index_chunks(chunks)
        if indexing.errors:
            raise SearchEngineError(f"Elasticsearch failed to index {len(indexing.errors)} chunk(s)")
        specialist_manifest = self._planner.plan(
            document_names=[document.document_name for document in documents],
            chunks=chunks,
        )
        return PreflightResult(
            documents=documents,
            chunks=chunks,
            graph=graph,
            indexing=indexing,
            specialist_manifest=specialist_manifest,
        )

