"""GraphRAG Knowledge Graph Constructor.

Extracts entities via spaCy NER and constructs a NetworkX DiGraph
representing cross-document entity relationships. Serializes to
JSON/GraphML for agent consumption.

Technologies: spacy, networkx
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from itertools import permutations
from pathlib import Path
from typing import Any

import networkx as nx
import spacy
from networkx.readwrite import json_graph

from src.graphrag.entity_resolver import EntityResolver, normalize_entity_name
from src.graphrag.schemas import EntityResolution, EntityType, ExtractedEntity
from src.ingestion.schemas import DocumentChunk

ENTITY_LABEL_MAP: dict[str, EntityType] = {
    "ORG": "organization",
    "PERSON": "person",
    "GPE": "location",
    "LOC": "location",
    "FAC": "asset",
    "PRODUCT": "asset",
    "LAW": "code",
}
_GRAPHML_JSON_ATTRIBUTES = {"aliases", "provenance", "chunk_ids", "section_ids"}


class GraphConstructor:
    """Extract entities and build a provenance-backed directed graph."""

    def __init__(
        self,
        *,
        nlp: Callable[[str], Any] | None = None,
        resolver: EntityResolver | None = None,
    ) -> None:
        self._nlp = nlp or spacy.load("en_core_web_lg")
        self._resolver = resolver or EntityResolver()

    def extract_entities(self, chunks: Iterable[DocumentChunk]) -> list[ExtractedEntity]:
        """Extract supported spaCy labels while retaining chunk provenance."""

        extracted_entities: list[ExtractedEntity] = []
        for chunk in chunks:
            document = self._nlp(chunk.text)
            for entity in document.ents:
                entity_type = ENTITY_LABEL_MAP.get(entity.label_)
                if entity_type is None:
                    continue
                extracted_entities.append(
                    ExtractedEntity(
                        name=entity.text.strip(),
                        entity_type=entity_type,
                        chunk_id=chunk.chunk_id,
                        document_name=chunk.document_name,
                        section_id=chunk.section_id,
                        absolute_page=chunk.absolute_page,
                    )
                )
        return extracted_entities

    def build_graph(self, chunks: Iterable[DocumentChunk]) -> nx.DiGraph:
        """Build entity co-occurrence and explicit section-reference edges."""

        chunk_list = list(chunks)
        bundle_context = {chunk.document_name for chunk in chunk_list}
        graph: nx.DiGraph[str] = nx.DiGraph()
        entities_by_chunk: dict[str, list[ExtractedEntity]] = {}
        for entity in self.extract_entities(chunk_list):
            entities_by_chunk.setdefault(entity.chunk_id, []).append(entity)

        for chunk in chunk_list:
            entity_node_ids: list[str] = []
            for entity in entities_by_chunk.get(chunk.chunk_id, []):
                resolution = self._resolve_entity(entity, bundle_context=bundle_context)
                node_id = _entity_node_id(resolution)
                _upsert_entity_node(graph, node_id, entity, resolution)
                if node_id not in entity_node_ids:
                    entity_node_ids.append(node_id)

            for source_id, target_id in permutations(entity_node_ids, 2):
                _upsert_edge(
                    graph,
                    source_id,
                    target_id,
                    relationship="co_occurrence",
                    chunk_id=chunk.chunk_id,
                    section_id=chunk.section_id,
                )

            for reference in chunk.references_sections:
                section_node_id = _section_node_id(reference)
                graph.add_node(
                    section_node_id,
                    node_type="section",
                    canonical_name=reference,
                    entity_type="section",
                    status="confirmed",
                    aliases=[reference],
                    provenance=[],
                )
                for entity_node_id in entity_node_ids:
                    _upsert_edge(
                        graph,
                        entity_node_id,
                        section_node_id,
                        relationship="section_reference",
                        chunk_id=chunk.chunk_id,
                        section_id=chunk.section_id,
                    )
        return graph

    def _resolve_entity(self, entity: ExtractedEntity, bundle_context: set[str] | None = None) -> EntityResolution:
        if not self._resolver.registered_entities(entity.entity_type):
            self._resolver.register(entity.name, entity.entity_type, document_name=entity.document_name)
            return EntityResolution(
                original_name=entity.name,
                canonical_name=entity.name,
                entity_type=entity.entity_type,
                resolution_tier=1,
                status="confirmed",
                confidence=1.0,
                reason="first_seen_canonical",
            )
        resolution = self._resolver.resolve(entity.name, entity.entity_type, bundle_context=bundle_context)
        if resolution.status == "unconfirmed_node":
            # Genuinely new entity — register it as a new canonical so subsequent
            # aliases of this entity can resolve against it.
            self._resolver.register(entity.name, entity.entity_type, document_name=entity.document_name)
        return resolution


def _entity_node_id(resolution: EntityResolution) -> str:
    normalized_name = normalize_entity_name(resolution.canonical_name)
    digest = hashlib.sha256(f"{resolution.entity_type}:{normalized_name}".encode()).hexdigest()[:16]
    return f"entity:{resolution.entity_type}:{digest}"


def _section_node_id(reference: str) -> str:
    digest = hashlib.sha256(reference.casefold().encode()).hexdigest()[:16]
    return f"section:{digest}"


def _upsert_entity_node(
    graph: nx.DiGraph,
    node_id: str,
    entity: ExtractedEntity,
    resolution: EntityResolution,
) -> None:
    provenance = {
        "chunk_id": entity.chunk_id,
        "document_name": entity.document_name,
        "section_id": entity.section_id,
        "absolute_page": entity.absolute_page,
    }
    if node_id not in graph:
        graph.add_node(
            node_id,
            node_type="entity",
            canonical_name=resolution.canonical_name,
            entity_type=resolution.entity_type,
            status=resolution.status,
            aliases=[entity.name],
            provenance=[provenance],
        )
        return

    attributes = graph.nodes[node_id]
    if entity.name not in attributes["aliases"]:
        attributes["aliases"].append(entity.name)
    if provenance not in attributes["provenance"]:
        attributes["provenance"].append(provenance)
    # Upgrade status if a later resolution confirms the node.
    if resolution.status == "confirmed" and attributes["status"] == "unconfirmed_node":
        attributes["status"] = "confirmed"


def _upsert_edge(
    graph: nx.DiGraph,
    source_id: str,
    target_id: str,
    *,
    relationship: str,
    chunk_id: str,
    section_id: str,
) -> None:
    if graph.has_edge(source_id, target_id):
        edge = graph.edges[source_id, target_id]
        if chunk_id not in edge["chunk_ids"]:
            edge["chunk_ids"].append(chunk_id)
        if section_id not in edge["section_ids"]:
            edge["section_ids"].append(section_id)
        return
    graph.add_edge(
        source_id,
        target_id,
        relationship=relationship,
        chunk_ids=[chunk_id],
        section_ids=[section_id],
    )


def save_graph_json(graph: nx.DiGraph, output_path: str | Path) -> None:
    """Persist a directed graph as node-link JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_graph.node_link_data(graph, edges="edges"), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_graph_json(input_path: str | Path) -> nx.DiGraph:
    """Load a directed graph from node-link JSON."""

    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return nx.DiGraph(json_graph.node_link_graph(data, edges="edges", directed=True))


def save_graphml(graph: nx.DiGraph, output_path: str | Path) -> None:
    """Persist a directed graph as GraphML with encoded complex attributes."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable_graph = graph.copy()
    for _, attributes in serializable_graph.nodes(data=True):
        _encode_graphml_attributes(attributes)
    for _, _, attributes in serializable_graph.edges(data=True):
        _encode_graphml_attributes(attributes)
    nx.write_graphml(serializable_graph, path)


def load_graphml(input_path: str | Path) -> nx.DiGraph:
    """Load GraphML and restore encoded complex attributes."""

    graph: nx.DiGraph = nx.DiGraph(nx.read_graphml(Path(input_path)))
    for _, attributes in graph.nodes(data=True):
        _decode_graphml_attributes(attributes)
    for _, _, attributes in graph.edges(data=True):
        _decode_graphml_attributes(attributes)
    return graph


def _encode_graphml_attributes(attributes: dict[str, Any]) -> None:
    for key, value in attributes.items():
        if isinstance(value, (dict, list)):
            attributes[key] = json.dumps(value, sort_keys=True)


def _decode_graphml_attributes(attributes: dict[str, Any]) -> None:
    for key in _GRAPHML_JSON_ATTRIBUTES & attributes.keys():
        attributes[key] = json.loads(attributes[key])
