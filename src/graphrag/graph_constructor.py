"""GraphRAG Knowledge Graph Constructor.

Extracts entities via spaCy NER and constructs a NetworkX DiGraph
representing cross-document entity relationships. Serializes to
JSON/GraphML for agent consumption.

Technologies: spacy, networkx
"""
