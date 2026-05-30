"""Tests for planner agent smart dispatch."""

from typing import Any

from src.agents.planner_agent import (
    AGENT_SYNONYMS,
    CORRECT_AGENT_IDS,
    SPECIALIST_REGISTRY,
    PlannerAgent,
    build_compound_query,
)
from src.agents.schemas import AgentName
from src.common.models import ClauseType
from src.ingestion.schemas import DocumentChunk
from src.search.search_engine import build_search_request


def test_registry_contains_exact_approved_agent_ids_in_dispatch_order() -> None:
    assert CORRECT_AGENT_IDS == [
        "ip_agent",
        "litigation_agent",
        "regulatory_agent",
        "privacy_agent",
        "finance_agent",
        "tax_agent",
        "insurance_agent",
        "hr_agent",
        "governance_agent",
        "related_party_agent",
        "cyber_agent",
        "assets_agent",
        "supplier_agent",
        "customer_agent",
        "reputation_agent",
        "esg_agent",
    ]
    assert [specialist.agent_name.value for specialist in SPECIALIST_REGISTRY] == CORRECT_AGENT_IDS
    assert {agent.value for agent in AgentName} == set(CORRECT_AGENT_IDS)


def test_registry_ids_are_unique_and_every_specialist_has_routing_terms() -> None:
    agent_names = [specialist.agent_name for specialist in SPECIALIST_REGISTRY]

    assert len(agent_names) == len(set(agent_names)) == 16
    assert all(specialist.routing_terms for specialist in SPECIALIST_REGISTRY)


def test_registry_excludes_removed_or_invented_specialist_ids() -> None:
    removed_ids = {
        "antitrust_competition",
        "transaction_change_control",
        "commercial_contracts",
        "real_estate_assets",
        "technology_it",
        "cybersecurity_privacy",
    }

    assert removed_ids.isdisjoint(CORRECT_AGENT_IDS)


def test_every_specialist_has_query_time_synonym_groups() -> None:
    assert set(AGENT_SYNONYMS) == set(AgentName)
    assert all(specialist.synonym_groups for specialist in SPECIALIST_REGISTRY)


def test_compound_query_expands_privacy_terms_and_uses_shared_clause_type() -> None:
    query = build_compound_query(AgentName.PRIVACY, "personal data")

    assert query.expanded_terms == ["personally identifiable information", "pii"]
    assert query.filters.clause_types == [ClauseType.DATA_PROTECTION]
    assert build_search_request(query)["query"]["bool"]["must"] == [
        {
            "bool": {
                "should": [
                    {"match_phrase": {"text": "personal data"}},
                    {"match_phrase": {"text": "personally identifiable information"}},
                    {"match_phrase": {"text": "pii"}},
                ],
                "minimum_should_match": 1,
            }
        }
    ]


def test_compound_query_accepts_explicit_clause_type_override_without_registry_mutation() -> None:
    finance_specialist = next(item for item in SPECIALIST_REGISTRY if item.agent_name is AgentName.FINANCE)
    original_clause_types = list(finance_specialist.clause_types)

    query = build_compound_query(
        AgentName.FINANCE,
        "cash",
        clause_types=[ClauseType.FX_HEDGING],
    )

    assert query.filters.clause_types == [ClauseType.FX_HEDGING]
    assert finance_specialist.clause_types == original_clause_types


def test_planner_routes_cyber_and_privacy_to_separate_agents() -> None:
    manifest = PlannerAgent().plan(
        document_names=["security-review.pdf"],
        chunks=[_chunk(text="The cybersecurity review covers personal data processing.")],
    )

    assert AgentName.CYBER in manifest.active_agents
    assert AgentName.PRIVACY in manifest.active_agents


def test_planner_routes_change_of_control_to_assets_and_regulatory_agents() -> None:
    manifest = PlannerAgent().plan(
        document_names=["agreement.pdf"],
        chunks=[_chunk(text="Closing term.", clause_type=ClauseType.CHANGE_OF_CONTROL)],
    )

    assert manifest.active_agents == [AgentName.REGULATORY, AgentName.ASSETS]


def test_planner_routes_multi_domain_filenames() -> None:
    manifest = PlannerAgent().plan(
        document_names=["tax-return.pdf", "supplier-contract.pdf"],
        chunks=[],
    )

    assert AgentName.TAX in manifest.active_agents
    assert AgentName.SUPPLIER in manifest.active_agents


def test_planner_activates_all_agents_for_unmatched_documents() -> None:
    manifest = PlannerAgent().plan(
        document_names=["miscellaneous.pdf"],
        chunks=[_chunk(text="The parties agree.")],
    )

    assert manifest.used_fallback is True
    assert [agent.value for agent in manifest.active_agents] == CORRECT_AGENT_IDS


def test_planner_agent_llm_success() -> None:
    from typing import Any
    from unittest.mock import patch, MagicMock
    import json
    from src.agents.planner_agent import LLMPlannerOutput

    expected_output = LLMPlannerOutput(
        active_agents=["ip_agent", "finance_agent"],
        document_type_map={"doc1.pdf": "SPA", "doc2.pdf": "IP assignment"}
    )
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(expected_output.model_dump())}
    
    with patch("httpx.post", return_value=mock_resp) as mock_post:
        planner = PlannerAgent()
        manifest = planner.plan(
            document_names=["doc1.pdf", "doc2.pdf"],
            chunks=[
                DocumentChunk(
                    chunk_id="doc1:0",
                    document_name="doc1.pdf",
                    chunk_index=0,
                    text="patent info",
                    section_id="Section 1",
                    absolute_page=0,
                    clause_type=ClauseType.GENERAL
                )
            ]
        )
    
    assert manifest.active_agents == [AgentName.IP, AgentName.FINANCE]
    assert manifest.used_fallback is False
    assert manifest.document_type_map == {"doc1.pdf": "SPA", "doc2.pdf": "IP assignment"}
    mock_post.assert_called_once()
    called_json = mock_post.call_args[1]["json"]
    assert "SPA" in called_json["system"]
    assert "patent info" in called_json["prompt"]
    assert "doc1.pdf" in called_json["prompt"]


def test_planner_agent_llm_empty_agents_fallback() -> None:
    from typing import Any
    from unittest.mock import patch, MagicMock
    import json
    from src.agents.planner_agent import LLMPlannerOutput

    expected_output = LLMPlannerOutput(
        active_agents=[],
        document_type_map={"doc1.pdf": "SPA"}
    )
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(expected_output.model_dump())}
    
    with patch("httpx.post", return_value=mock_resp):
        planner = PlannerAgent()
        manifest = planner.plan(
            document_names=["doc1.pdf"],
            chunks=[_chunk(text="patent assignment", clause_type=ClauseType.GENERAL)]
        )
    
    assert AgentName.IP in manifest.active_agents
    assert manifest.used_fallback is True
    assert manifest.document_type_map == {"doc1.pdf": "SPA"}


def test_planner_agent_llm_failure_fallback() -> None:
    import httpx
    from unittest.mock import patch

    with patch("httpx.post", side_effect=httpx.HTTPError("Connection refused")):
        planner = PlannerAgent()
        manifest = planner.plan(
            document_names=["doc1.pdf"],
            chunks=[_chunk(text="patent assignment", clause_type=ClauseType.GENERAL)]
        )
    
    assert manifest.active_agents == [AgentName.IP]
    assert manifest.used_fallback is False
    assert manifest.document_type_map == {}



def _chunk(
    *,
    text: str,
    clause_type: ClauseType = ClauseType.GENERAL,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id="agreement:0",
        document_name="agreement.pdf",
        chunk_index=0,
        text=text,
        section_id="Section 1",
        absolute_page=0,
        clause_type=clause_type,
    )
