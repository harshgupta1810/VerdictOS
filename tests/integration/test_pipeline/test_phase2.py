"""Integration tests for Phase 2: Finding Generation (Specialist Agents)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.schemas import ActiveSpecialistManifest, AgentName, Finding
from src.agents.dispatcher import run_parallel_analysis
from src.search.schemas import SearchResult
from src.common.models import ClauseType

@pytest.mark.asyncio
async def test_phase2_compound_queries_and_deduplication():
    # Setup
    mock_search = MagicMock()
    mock_llm = AsyncMock()
    mock_llm.default_model = "llama3"

    # 1. SearchEngine returns multiple chunks, some overlapping
    mock_search.search.side_effect = [
        [
            SearchResult(
                chunk_id="doc1:chunk:1",
                score=5.0,
                document_name="agreement.pdf",
                text="The IP rights are assigned to the buyer.",
                section_id="Sec 1",
                absolute_page=1,
                clause_type=ClauseType.IP_ASSIGNMENT,
                references_sections=[],
                highlights=[]
            )
        ],
        [
            SearchResult(
                chunk_id="doc1:chunk:2",
                score=4.0,
                document_name="agreement.pdf",
                text="Tax obligations belong to seller.",
                section_id="Sec 2",
                absolute_page=2,
                clause_type=ClauseType.TAX_PROVISION,
                references_sections=[],
                highlights=[]
            )
        ]
    ]

    from src.agents.base_agent import RelevanceCheckResult, _AnalysisOutput, _RawFinding
    
    # LLM Mocking for IP agent
    ip_relevance = RelevanceCheckResult(relevant=True, reason="IP")
    ip_analysis = _AnalysisOutput(findings=[
        _RawFinding(claim="IP rights transferred.", citation="The IP rights are assigned to the buyer.", confidence=0.9),
        _RawFinding(claim="IP rights transferred.", citation="The IP rights are assigned to the buyer.", confidence=0.9) # Duplicate!
    ])
    
    # LLM Mocking for Tax agent
    tax_relevance = RelevanceCheckResult(relevant=True, reason="Tax")
    tax_analysis = _AnalysisOutput(findings=[
        _RawFinding(claim="Seller pays tax.", citation="Tax obligations belong to seller.", confidence=0.9)
    ])

    async def mock_generate(prompt, schema, **kwargs):
        if schema.__name__ == "RelevanceCheckResult":
            return RelevanceCheckResult(relevant=True, reason="Matched")
        elif schema.__name__ == "_AnalysisOutput":
            system_prompt = prompt.system_prompt.lower()
            if "intellectual property" in system_prompt:
                return ip_analysis
            else:
                return tax_analysis
        raise ValueError(f"Unknown schema: {schema}")

    mock_llm.generate_with_schema.side_effect = mock_generate

    manifest = ActiveSpecialistManifest(active_agents=[AgentName.IP, AgentName.TAX])
    preflight_mock = MagicMock()
    preflight_mock.specialist_manifest = manifest
    
    # Execute Phase 2
    result = await run_parallel_analysis(
        preflight_result=preflight_mock,
        search_engine=mock_search,
        llm_client=mock_llm,
        document_name="agreement.pdf"
    )
    
    # Verify compound queries returned filtered chunks
    assert mock_search.search.call_count == 2
    
    # Verify Pydantic validation (findings are correctly parsed into `Finding` instances)
    assert all(isinstance(f, Finding) for f in result.unique_findings)
    
    # Verify Deduplication (the two identical IP findings should be merged)
    # We had 2 IP findings (duplicates) and 1 Tax finding -> total 2 unique findings.
    assert len(result.unique_findings) == 2
    
    ip_findings = [f for f in result.unique_findings if f.source_agent == AgentName.IP]
    tax_findings = [f for f in result.unique_findings if f.source_agent == AgentName.TAX]
    
    assert len(ip_findings) == 1
    assert len(tax_findings) == 1
    assert ip_findings[0].claim == "IP rights transferred."
