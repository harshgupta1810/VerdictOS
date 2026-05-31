"""Tests for BaseAgent default behaviors."""

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.base_agent import BaseSpecialistAgent
from src.agents.schemas import AgentName, SpecialistDefinition
from src.common.exceptions import LLMClientError
from src.common.models import ClauseType

class DummyAgent(BaseSpecialistAgent):
    """Minimal concrete implementation."""
    @property
    def _domain_description(self) -> str:
        return "Dummy Domain"

def test_base_agent_default_properties() -> None:
    defn = SpecialistDefinition(
        agent_name=AgentName.IP,
        routing_terms=["ip"],
    )
    agent = DummyAgent(defn, AsyncMock(), AsyncMock())
    assert agent._domain_instructions == ""
    assert agent._discard_rules == ""

@pytest.mark.asyncio
async def test_base_agent_analyze_catches_llm_error() -> None:
    from unittest.mock import MagicMock
    from src.search.schemas import SearchResult
    
    defn = SpecialistDefinition(
        agent_name=AgentName.IP,
        routing_terms=["ip"],
    )
    
    mock_search = MagicMock()
    mock_search.search.return_value = [SearchResult(
        document_name="doc", chunk_id="chunk1", section_id="sec1", text="text",
        absolute_page=1, score=1.0, clause_type=ClauseType.GENERAL
    )]
    
    mock_llm = AsyncMock()
    
    agent = DummyAgent(defn, mock_search, mock_llm)
    
    # Patch _relevance_filter to raise the error so it gets caught by analyze's try/except
    with patch.object(agent, '_relevance_filter', AsyncMock(side_effect=LLMClientError("LLM failed"))):
        result = await agent.analyze()
        
    assert result.error == "LLM failed"
    assert result.agent_name == AgentName.IP
