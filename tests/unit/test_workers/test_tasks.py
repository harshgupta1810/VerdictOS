import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.workers.tasks import run_deal_pipeline
from src.db.models import Deal
from src.debate.schemas import DimensionState
from src.agents.schemas import Finding

@pytest.fixture
def mock_external():
    with patch("src.workers.tasks.Elasticsearch") as mock_es, \
         patch("src.workers.tasks.ElasticsearchIndexer") as mock_indexer, \
         patch("src.workers.tasks.SparseSearchEngine") as mock_search, \
         patch("src.workers.tasks.OllamaClient") as mock_llm, \
         patch("src.workers.tasks.PreflightPipeline") as mock_preflight, \
         patch("src.workers.tasks.run_parallel_analysis") as mock_run_parallel, \
         patch("src.workers.tasks.run_debate_loop") as mock_debate, \
         patch("src.workers.tasks.JudgeAgent") as mock_judge, \
         patch("src.workers.tasks.VerdictAssembler") as mock_assembler, \
         patch("src.workers.tasks.AsyncSessionLocal") as mock_db, \
         patch("src.workers.tasks.emit_pipeline_event") as mock_emit, \
         patch("src.workers.tasks.asyncio.to_thread") as mock_to_thread:
        yield mock_db, mock_to_thread, mock_run_parallel, mock_debate, mock_judge, mock_assembler

@pytest.mark.asyncio
async def test_run_deal_pipeline_success(mock_external):
    mock_db, mock_to_thread, mock_run_parallel, mock_debate, mock_judge, mock_assembler = mock_external
    session_instance = AsyncMock()
    mock_db.return_value.__aenter__.return_value = session_instance
    deal_mock = MagicMock(spec=Deal)
    deal_mock.deal_id = "123"
    session_instance.get.return_value = deal_mock
    
    preflight_result = MagicMock()
    mock_to_thread.return_value = preflight_result
    
    dispatch_result = MagicMock()
    finding = MagicMock(spec=Finding)
    finding.id = "f1"
    finding.dimension = "financial"
    dispatch_result.unique_findings = [finding]
    mock_run_parallel.return_value = dispatch_result
    
    mock_arg = MagicMock()
    mock_arg.finding_id = "f1"
    mock_debate.return_value = ({"financial": DimensionState.CONTESTED}, [mock_arg])
    
    mock_judge_instance = AsyncMock()
    mock_judge.return_value = mock_judge_instance
    mock_judge_instance.synthesize.return_value = MagicMock()
    
    mock_assembler_instance = mock_assembler.return_value
    mock_assembler_instance.generate_verdict = AsyncMock()
    
    await run_deal_pipeline("123", ["path.txt"])
    
    assert deal_mock.status == "judging"

@pytest.mark.asyncio
async def test_run_deal_pipeline_not_found(mock_external):
    mock_db, mock_to_thread, mock_run_parallel, mock_debate, mock_judge, mock_assembler = mock_external
    session_instance = AsyncMock()
    mock_db.return_value.__aenter__.return_value = session_instance
    session_instance.get.return_value = None
    
    await run_deal_pipeline("123", ["path.txt"])
    mock_to_thread.assert_not_called()

@pytest.mark.asyncio
async def test_run_deal_pipeline_error(mock_external):
    mock_db, mock_to_thread, mock_run_parallel, mock_debate, mock_judge, mock_assembler = mock_external
    session_instance = AsyncMock()
    mock_db.return_value.__aenter__.return_value = session_instance
    deal_mock = MagicMock(spec=Deal)
    deal_mock.deal_id = "123"
    session_instance.get.return_value = deal_mock
    
    mock_to_thread.side_effect = Exception("error")
    
    await run_deal_pipeline("123", ["path.txt"])
    
    assert deal_mock.status == "error"
