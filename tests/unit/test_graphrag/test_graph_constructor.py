"""Tests for GraphRAG knowledge graph constructor."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import pytest

from src.graphrag.graph_constructor import (
    GraphConstructor,
    load_graph_json,
    load_graphml,
    save_graph_json,
    save_graphml,
)
from src.ingestion.schemas import DocumentChunk


@dataclass
class _Entity:
    text: str
    label_: str


@dataclass
class _Document:
    ents: list[_Entity]


class _NLP:
    def __call__(self, _text: str) -> _Document:
        return _Document(
            ents=[
                _Entity("Acme Corp.", "ORG"),
                _Entity("Ada Smith", "PERSON"),
                _Entity("London", "GPE"),
                _Entity("Factory 7", "FAC"),
                _Entity("Code 42", "LAW"),
                _Entity("ignored", "EVENT"),
            ]
        )


class _MappedNLP:
    def __init__(self, entities_by_text: dict[str, list[_Entity]]) -> None:
        self.entities_by_text = entities_by_text

    def __call__(self, text: str) -> _Document:
        return _Document(ents=self.entities_by_text[text])


def test_extract_entities_maps_supported_labels_with_chunk_provenance() -> None:
    chunk = DocumentChunk(
        chunk_id="agreement:0",
        document_name="agreement.pdf",
        chunk_index=0,
        text="Source text.",
        section_id="Section 1",
        absolute_page=2,
    )

    entities = GraphConstructor(nlp=_NLP()).extract_entities([chunk])

    assert [(entity.name, entity.entity_type) for entity in entities] == [
        ("Acme Corp.", "organization"),
        ("Ada Smith", "person"),
        ("London", "location"),
        ("Factory 7", "asset"),
        ("Code 42", "code"),
    ]
    assert all(entity.chunk_id == "agreement:0" for entity in entities)
    assert all(entity.absolute_page == 2 for entity in entities)


def test_build_graph_adds_resolved_nodes_co_occurrence_and_reference_edges() -> None:
    chunk = _chunk(
        chunk_id="agreement:0",
        text="source",
        references_sections=["Section 9.4"],
    )
    nlp = _MappedNLP(
        {
            "source": [
                _Entity("Acme Corp.", "ORG"),
                _Entity("Ada Smith", "PERSON"),
            ]
        }
    )

    graph = GraphConstructor(nlp=nlp).build_graph([chunk])

    entity_nodes = [
        node_id
        for node_id, attributes in graph.nodes(data=True)
        if attributes["node_type"] == "entity"
    ]
    section_nodes = [
        node_id
        for node_id, attributes in graph.nodes(data=True)
        if attributes["node_type"] == "section"
    ]
    assert len(entity_nodes) == 2
    assert len(section_nodes) == 1
    assert graph.has_edge(entity_nodes[0], entity_nodes[1])
    assert graph.has_edge(entity_nodes[1], entity_nodes[0])
    assert graph.edges[entity_nodes[0], entity_nodes[1]]["relationship"] == "co_occurrence"
    assert all(graph.has_edge(entity_node, section_nodes[0]) for entity_node in entity_nodes)
    assert not any(graph.has_edge(section_nodes[0], entity_node) for entity_node in entity_nodes)


def test_build_graph_merges_resolved_aliases_and_separates_unconfirmed_entities() -> None:
    chunks = [
        _chunk(chunk_id="agreement:0", text="first"),
        _chunk(chunk_id="agreement:1", text="alias"),
        _chunk(chunk_id="agreement:2", text="distinct"),
    ]
    nlp = _MappedNLP(
        {
            "first": [_Entity("Acme Corporation", "ORG")],
            "alias": [_Entity("Acme Corporatio", "ORG")],
            "distinct": [_Entity("Different Holdings", "ORG")],
        }
    )

    graph = GraphConstructor(nlp=nlp).build_graph(chunks)

    entity_attributes = [
        attributes
        for _, attributes in graph.nodes(data=True)
        if attributes["node_type"] == "entity"
    ]
    assert len(entity_attributes) == 2
    confirmed = next(attributes for attributes in entity_attributes if attributes["status"] == "confirmed")
    unconfirmed = next(attributes for attributes in entity_attributes if attributes["status"] == "unconfirmed_node")
    assert confirmed["aliases"] == ["Acme Corporation", "Acme Corporatio"]
    assert unconfirmed["canonical_name"] == "Different Holdings"


def test_build_graph_registers_unconfirmed_entity_so_later_aliases_resolve() -> None:
    """Unconfirmed entities are registered as new canonicals so subsequent
    spelling variants (aliases) can still resolve to them at tier 1/2."""
    chunks = [
        _chunk(chunk_id="agreement:0", text="first"),
        _chunk(chunk_id="agreement:1", text="new_entity"),
        _chunk(chunk_id="agreement:2", text="alias_of_new"),
    ]
    nlp = _MappedNLP(
        {
            "first": [_Entity("Acme Corp.", "ORG")],
            # "Globex Holdings" cannot match "Acme Corp." — registered as new canonical
            "new_entity": [_Entity("Globex Holdings", "ORG")],
            # "Globex Holding" is a near-exact alias of "Globex Holdings" (ratio ~0.97 > 0.85)
            "alias_of_new": [_Entity("Globex Holding", "ORG")],
        }
    )

    graph = GraphConstructor(nlp=nlp).build_graph(chunks)

    entity_nodes = [
        attrs for _, attrs in graph.nodes(data=True) if attrs["node_type"] == "entity"
    ]
    # "Acme Corp." confirmed + "Globex Holdings"/"Globex Holding" merged into one node
    assert len(entity_nodes) == 2
    globex_node = next(
        attrs for attrs in entity_nodes if "Globex" in attrs["canonical_name"]
    )
    # Both spellings merged under the same canonical
    assert "Globex Holdings" in globex_node["aliases"]
    assert "Globex Holding" in globex_node["aliases"]
    # Status upgraded to confirmed once the alias resolved at tier 2
    assert globex_node["status"] == "confirmed"


@pytest.mark.parametrize(
    ("extension", "save_graph", "load_graph"),
    [
        ("json", save_graph_json, load_graph_json),
        ("graphml", save_graphml, load_graphml),
    ],
)
def test_graph_serialization_round_trip_preserves_attributes(
    tmp_path: Path,
    extension: str,
    save_graph: Any,
    load_graph: Any,
) -> None:
    graph = GraphConstructor(
        nlp=_MappedNLP({"source": [_Entity("Acme Corp.", "ORG"), _Entity("Ada Smith", "PERSON")]})
    ).build_graph([_chunk(chunk_id="agreement:0", text="source", references_sections=["Section 9.4"])])
    output_path = tmp_path / f"graph.{extension}"

    save_graph(graph, output_path)
    restored = load_graph(output_path)

    assert set(restored.nodes) == set(graph.nodes)
    assert set(restored.edges) == set(graph.edges)
    assert list(restored.nodes(data=True)) == list(graph.nodes(data=True))
    assert list(restored.edges(data=True)) == list(graph.edges(data=True))


@pytest.mark.parametrize(
    ("extension", "save_graph", "load_graph"),
    [
        ("json", save_graph_json, load_graph_json),
        ("graphml", save_graphml, load_graphml),
    ],
)
def test_empty_graph_serialization_round_trip(
    tmp_path: Path,
    extension: str,
    save_graph: Any,
    load_graph: Any,
) -> None:
    output_path = tmp_path / f"empty.{extension}"

    save_graph(nx.DiGraph(), output_path)
    restored = load_graph(output_path)

    assert len(restored) == 0
    assert len(restored.edges) == 0


def _chunk(
    *,
    chunk_id: str,
    text: str,
    references_sections: list[str] | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_name="agreement.pdf",
        chunk_index=0,
        text=text,
        section_id="Section 1",
        absolute_page=0,
        references_sections=references_sections or [],
    )
