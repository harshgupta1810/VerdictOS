"""Integration tests for Phase 4: Debate Loop Orchestration."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.schemas import Finding, FindingDimension, AgentName
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState
from src.debate.orchestrator import run_debate_loop

@pytest.mark.asyncio
async def test_phase4_debate_loop_integration():
    # Setup mock findings
    findings = [
        Finding(
            id=f"f{i}",
            claim=f"Risk finding {i}",
            citation="Source text",
            citation_chunk_id="chunk1",
            source_agent=AgentName.LITIGATION,
            section_id="Sec1",
            absolute_page=1,
            confidence=0.9,
            dimension=FindingDimension.RISK_EXPOSURE
        )
        for i in range(3)  # 3 findings triggers "full" mode
    ]

    mock_llm = AsyncMock()
    mock_search = MagicMock()
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    # Mock execute_dimension_debate to simulate rounds and gates
    # We will run 3 rounds. Round 1: Active, Round 2: Active, Round 3: Active
    # At Round 3, it should cap and exit.
    
    round_counts = []
    
    async def mock_execute(*args, **kwargs):
        round_number = kwargs["round_number"]
        round_counts.append(round_number)
        
        # Simulate Gate B dropping an uncited claim by NOT returning an argument for finding f2
        finding_id = kwargs["finding_id"]
        if finding_id == "f2":
            return [], DimensionState.ACTIVE
        
        # For f0 and f1, return some arguments. 
        # Simulate a dropout in round 2 for Critic
        dropout_flag = (round_number >= 2 and finding_id == "f1")
        
        arg = DebateArgument(
            id=f"arg_{finding_id}_{round_number}",
            finding_id=finding_id,
            persona=DebatePersona.CRITIC,
            round=round_number,
            dimension=FindingDimension.RISK_EXPOSURE,
            stance=DebateStance.OPPOSE,
            argument="This is bad.",
            steelman="I understand your point",
            citations=["chunk1"],
            dropout_flag=dropout_flag
        )
        return [arg], DimensionState.ACTIVE

    with patch("src.debate.orchestrator.execute_dimension_debate", side_effect=mock_execute) as mock_exec, \
         patch("src.debate.orchestrator.persist_round_transcript", new_callable=AsyncMock) as mock_persist, \
         patch("src.debate.orchestrator.run_consensus_mapping") as mock_consensus:

        # Execute
        final_states, all_arguments = await run_debate_loop(
            deal_id="deal123",
            findings=findings,
            llm_client=mock_llm,
            search_engine=mock_search,
            db_session=mock_db
        )

        # Verify Round Cap at 3
        # We had 3 findings. finding "f2" drops out. f0 and f1 continue.
        # Max round number should be 3
        assert max(round_counts) == 3

        # Verify Audit Records (persist_round_transcript called for each round)
        assert mock_persist.call_count == 3
        
        # Verify Dropout-aware rule fires (run_consensus_mapping called)
        mock_consensus.assert_called_once()
