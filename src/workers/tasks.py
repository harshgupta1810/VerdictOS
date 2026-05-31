"""Background Pipeline Tasks.

Defines async tasks for document ingestion, debate pipeline
execution, and escalation SLA monitoring.
"""

import asyncio
import logging
from collections import defaultdict
from elasticsearch import Elasticsearch

from src.config import settings
from src.db.session import AsyncSessionLocal
from src.db.models import Deal
from src.api.websockets.emitter import emit_pipeline_event

# Phase 1
from src.preflight import PreflightPipeline
from src.ingestion.ingest import DocumentIngestor
from src.ingestion.chunker import SectionAwareChunker
from src.ingestion.classifier import ClauseClassifier
from src.graphrag.graph_constructor import GraphConstructor
from src.agents.planner_agent import PlannerAgent
from src.search.indexer import ElasticsearchIndexer

# Phase 2
from src.search.search_engine import SparseSearchEngine
from src.llm.client import OllamaClient
from src.agents.dispatcher import run_parallel_analysis

# Phase 3-5
from src.debate.orchestrator import run_debate_loop
from src.debate.schemas import DimensionState

# Phase 6
from src.agents.judge_agent import JudgeAgent

# Phase 7
from src.verdict.generator import VerdictAssembler

logger = logging.getLogger(__name__)

async def run_deal_pipeline(deal_id: str, document_paths: list[str], is_delta: bool = False):
    """
    Executes the full VerdictOS analytical pipeline for a given deal.
    This runs asynchronously using FastAPI BackgroundTasks.
    """
    logger.info(f"Starting pipeline for deal_id: {deal_id}, delta={is_delta}")
    
    try:
        # Step 1: Initialize external clients
        es_client = Elasticsearch(settings.elasticsearch_url)
        indexer = ElasticsearchIndexer(es_client, index_name=settings.elasticsearch_index)
        search_engine = SparseSearchEngine(es_client, index_name=settings.elasticsearch_index)
        
        llm_client = OllamaClient(
            base_url=settings.ollama_url,
            default_model=settings.llm_reasoning_model
        )
        
        # Step 2: Phase 1 (Pre-Flight)
        async with AsyncSessionLocal() as db:
            deal = await db.get(Deal, deal_id)
            if not deal:
                return
            deal.status = "indexing"
            await db.commit()
            await emit_pipeline_event(deal_id, "phase_transition", {"phase": "indexing", "progress": 10})
        
        preflight_pipeline = PreflightPipeline(
            ingestor=DocumentIngestor(),
            chunker=SectionAwareChunker(),
            classifier=ClauseClassifier(),
            graph_constructor=GraphConstructor(),
            indexer=indexer,
            planner=PlannerAgent(model_name=settings.llm_reasoning_model)
        )
        
        # Preflight runs synchronously
        preflight_result = await asyncio.to_thread(preflight_pipeline.run, document_paths)
        
        # Step 3: Phase 2 (Smart Dispatch & Specialist Analysis)
        async with AsyncSessionLocal() as db:
            deal = await db.get(Deal, deal_id)
            if deal:
                deal.status = "analyzing"
                await db.commit()
                await emit_pipeline_event(deal_id, "phase_transition", {"phase": "analyzing", "progress": 30})
            
        dispatch_result = await run_parallel_analysis(
            preflight_result=preflight_result,
            search_engine=search_engine,
            llm_client=llm_client
        )
        findings = dispatch_result.unique_findings
        
        # Step 4: Phase 3-5 (Debate & Consensus)
        async with AsyncSessionLocal() as db:
            deal = await db.get(Deal, deal_id)
            if deal:
                deal.status = "debating"
                await db.commit()
                await emit_pipeline_event(deal_id, "phase_transition", {"phase": "debating", "progress": 60})
            
            final_states, all_debate_arguments = await run_debate_loop(
                deal_id=deal_id,
                findings=findings,
                llm_client=llm_client,
                search_engine=search_engine,
                db_session=db
            )
            
        # Step 5: Phase 6 (Judge Synthesis)
        async with AsyncSessionLocal() as db:
            deal = await db.get(Deal, deal_id)
            if deal:
                deal.status = "judging"
                await db.commit()
                await emit_pipeline_event(deal_id, "phase_transition", {"phase": "judging", "progress": 85})
        
        judge = JudgeAgent(search_engine=search_engine, llm_client=llm_client)
        judge_results = {}
        
        # Group arguments by finding for the judge
        args_by_finding = defaultdict(list)
        for arg in all_debate_arguments:
            args_by_finding[arg.finding_id].append(arg)
            
        for finding in findings:
            state = final_states.get(finding.dimension, DimensionState.ACTIVE)
            if state in [DimensionState.CONTESTED, DimensionState.UNRESOLVED]:
                f_args = args_by_finding[finding.id]
                res = await judge.synthesize(finding, f_args, state)
                judge_results[finding.id] = res

        # Step 6: Phase 7 (Verdict Assembly & Persistence)
        async with AsyncSessionLocal() as db:
            assembler = VerdictAssembler(db)
            verdict = await assembler.generate_verdict(deal_id, judge_results)
            await emit_pipeline_event(deal_id, "phase_transition", {"phase": "complete", "progress": 100})
            
        logger.info(f"Pipeline complete for deal_id: {deal_id}")

    except Exception as e:
        logger.error(f"Pipeline error for deal_id {deal_id}: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            deal = await db.get(Deal, deal_id)
            if deal:
                deal.status = "error"
                await db.commit()
                await emit_pipeline_event(deal_id, "error", {"message": str(e)})
