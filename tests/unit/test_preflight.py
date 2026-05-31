import pytest
from unittest.mock import MagicMock
import networkx as nx
import os
import pathlib
from src.preflight import PreflightPipeline
from src.common.exceptions import DocumentIngestionError, SearchEngineError
from src.search.schemas import IndexingOutcome

def test_preflight_pipeline_run_success():
    ingestor = MagicMock()
    chunker = MagicMock()
    classifier = MagicMock()
    graph_constructor = MagicMock()
    indexer = MagicMock()
    planner = MagicMock()
    
    document_mock = MagicMock()
    document_mock.document_name = "test.pdf"
    ingestor.parse.return_value = document_mock
    
    chunker.chunk.return_value = []
    graph_constructor.build_graph.return_value = nx.DiGraph()
    indexer.index_chunks.return_value = IndexingOutcome(attempted=0, indexed=0, errors=[])
    planner.plan.return_value = MagicMock()
    
    pipeline = PreflightPipeline(
        ingestor=ingestor,
        chunker=chunker,
        classifier=classifier,
        graph_constructor=graph_constructor,
        indexer=indexer,
        planner=planner
    )
    
    test_file = "tests/unit/test_preflight_dummy.txt"
    with open(test_file, "w") as f:
        f.write("content")
    
    try:
        result = pipeline.run([test_file, "not_a_file_path_1234"])
        assert result.graph is not None
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_preflight_pipeline_empty_paths():
    pipeline = PreflightPipeline(ingestor=MagicMock(), chunker=MagicMock(), classifier=MagicMock(), graph_constructor=MagicMock(), indexer=MagicMock(), planner=MagicMock())
    with pytest.raises(DocumentIngestionError):
        pipeline.run([])

def test_preflight_pipeline_indexing_error():
    ingestor = MagicMock()
    indexer = MagicMock()
    indexer.index_chunks.return_value = IndexingOutcome(attempted=1, indexed=0, errors=[{"error": "some error"}])
    
    pipeline = PreflightPipeline(
        ingestor=ingestor,
        chunker=MagicMock(),
        classifier=MagicMock(),
        graph_constructor=MagicMock(),
        indexer=indexer,
        planner=MagicMock()
    )
    
    test_file = "tests/unit/test_preflight_dummy_2.txt"
    with open(test_file, "w") as f:
        f.write("content")
        
    try:
        with pytest.raises(SearchEngineError):
            pipeline.run([test_file])
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
