"""Phase 1 Pre-Flight Pipeline Runner.

Executes the synchronous pre-flight pipeline against one or more PDF/DOCX
files and prints a structured report. Elasticsearch is used when reachable;
otherwise a dry-run stub is used so the script works offline.

Usage:
    python scripts/run_pipeline.py <file> [<file> ...]
    python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
    python scripts/run_pipeline.py testing_pdfs/*.pdf
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")

from src.agents.planner_agent import PlannerAgent
from src.config import settings
from src.graphrag.graph_constructor import GraphConstructor
from src.ingestion.chunker import SectionAwareChunker
from src.ingestion.classifier import ClauseClassifier
from src.ingestion.ingest import DocumentIngestor
from src.ingestion.schemas import DocumentChunk
from src.preflight import PreflightPipeline
from src.search.indexer import ElasticsearchIndexer
from src.search.schemas import IndexingOutcome


# ---------------------------------------------------------------------------
# Dry-run stub — used when Elasticsearch is unreachable
# ---------------------------------------------------------------------------

from collections.abc import Iterable


class _DryRunIndexer:
    """Accepts chunks without writing to ES. Reports attempted = indexed."""

    index_name = settings.elasticsearch_index

    def ensure_index(self) -> bool:
        return False

    def index_chunks(self, chunks: Iterable[DocumentChunk]) -> IndexingOutcome:
        chunk_list = list(chunks)
        return IndexingOutcome(attempted=len(chunk_list), indexed=len(chunk_list))


def _build_indexer(*, wait_seconds: int = 60) -> ElasticsearchIndexer | _DryRunIndexer:
    import time
    try:
        from elasticsearch import Elasticsearch
        client = Elasticsearch(settings.elasticsearch_url, request_timeout=30)
        deadline = time.monotonic() + wait_seconds
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            try:
                if client.ping():
                    print(f"[ES] Connected to {settings.elasticsearch_url} (attempt {attempt}) — live indexing enabled.\n")
                    return ElasticsearchIndexer(client, index_name=settings.elasticsearch_index)
            except Exception:
                pass
            print(f"[ES] Waiting for Elasticsearch... (attempt {attempt})", end="\r")
            time.sleep(3)
    except ImportError:
        pass
    print(f"\n[ES] Not reachable at {settings.elasticsearch_url} — running in dry-run mode.\n")
    return _DryRunIndexer()


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def _print_report(result: object, source_paths: list[Path]) -> None:
    from src.preflight import PreflightResult
    assert isinstance(result, PreflightResult)

    print("=" * 70)
    print("PHASE 1 PRE-FLIGHT REPORT")
    print("=" * 70)

    # Documents
    print(f"\nDocuments parsed: {len(result.documents)}")
    for doc in result.documents:
        print(f"  - {doc.document_name}  ({len(doc.raw_pages)} pages)")

    # Chunks
    print(f"\nChunks produced:  {len(result.chunks)}")

    # Clause-type breakdown
    clause_counts: Counter[str] = Counter(
        chunk.clause_type.value for chunk in result.chunks
    )
    print("\nClause-type distribution:")
    for clause_type, count in clause_counts.most_common():
        bar = "#" * min(count, 40)
        print(f"  {clause_type:<22} {bar} {count}")

    # Graph
    graph = result.graph
    entity_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "entity"]
    section_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "section"]
    confirmed = [n for n in entity_nodes if graph.nodes[n].get("status") == "confirmed"]
    unconfirmed = [n for n in entity_nodes if graph.nodes[n].get("status") == "unconfirmed_node"]

    print(f"\nGraphRAG graph:")
    print(f"  Entity nodes      : {len(entity_nodes)}  ({len(confirmed)} confirmed, {len(unconfirmed)} unconfirmed)")
    print(f"  Section nodes     : {len(section_nodes)}")
    print(f"  Edges             : {graph.number_of_edges()}")

    # Show top-10 confirmed entities by alias count
    if confirmed:
        top_entities = sorted(
            confirmed,
            key=lambda n: len(graph.nodes[n].get("aliases", [])),
            reverse=True,
        )[:10]
        print("\n  Top entities (by alias count):")
        for node_id in top_entities:
            attrs = graph.nodes[node_id]
            aliases = attrs.get("aliases", [])
            print(f"    [{attrs['entity_type']:12}] {attrs['canonical_name']}  ({len(aliases)} alias(es))")

    # Indexing
    print(f"\nIndexing outcome:")
    print(f"  Attempted : {result.indexing.attempted}")
    print(f"  Indexed   : {result.indexing.indexed}")
    if result.indexing.errors:
        print(f"  Errors    : {len(result.indexing.errors)}")

    # Specialist manifest
    manifest = result.specialist_manifest
    print(f"\nPlanner manifest  ({'fallback — all agents' if manifest.used_fallback else 'targeted'}):")
    for agent in manifest.active_agents:
        terms = manifest.matched_terms.get(agent, [])
        term_str = ", ".join(terms[:5]) + ("…" if len(terms) > 5 else "")
        print(f"  [+] {agent.value:<26} {term_str}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        print("Usage: python scripts/run_pipeline.py <file> [<file> ...]")
        sys.exit(1)

    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: file not found: {p}", file=sys.stderr)
        sys.exit(1)

    pipeline = PreflightPipeline(
        ingestor=DocumentIngestor(),
        chunker=SectionAwareChunker(),
        classifier=ClauseClassifier(),
        graph_constructor=GraphConstructor(),
        indexer=_build_indexer(),
        planner=PlannerAgent(),
    )

    print(f"Running Phase 1 pre-flight on {len(paths)} document(s)...\n")
    try:
        result = pipeline.run(paths)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_report(result, paths)


if __name__ == "__main__":
    main()
