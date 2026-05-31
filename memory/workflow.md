# VerdictOS System Runtime & Developer Workflow

This document details the deterministic **Seven-Phase Runtime Pipeline** of the VerdictOS multi-agent system, along with the local developer workflow required to implement, execute, and verify each phase.

---

## Part 1: The Seven-Phase Runtime Pipeline

```
Phase 1: Ingest & Index (Sync)
           │
           ▼
Phase 2: Smart Dispatch & Analysis (Async)
           │
           ▼
Phase 3: Aggregation & Gating (Async)
           │
           ▼
Phase 4: Adversarial Debate Loop (Async)
           │
           ▼
Phase 5: Consensus Mapping (Sync Math)
           │
           ▼
Phase 6: Judge Synthesis (Async LLM)
           │
           ▼
Phase 7: Verdict & Delta Engine (FastAPI API + Incremental Re-analysis)
           │
           ▼
Phase 8: Advanced Escalation & Approval Workflow
           │
           ▼
Final Output: Structured Verdict & Audit Trail
```

### Phase 1: Ingestion & Structural Indexing (Pre-Flight)
- **Description:** Documents (PDF/DOCX) are ingested, mapped for page coordinates, and split into clause-level chunks (200-500 tokens). spaCy NER extracts entities and feeds the 3-Tier Entity Resolver. A pre-flight NetworkX DiGraph is generated, document chunks are indexed in Elasticsearch, and a deterministic active-specialist manifest is emitted for Phase 2.
- **Key Modules:** `src/ingestion/ingest.py`, `src/ingestion/chunker.py`, `src/graphrag/graph_constructor.py`, `src/search/search_engine.py`.
- **Developer Action:** Set up Elasticsearch indices, define NetworkX serializers, and run parser tests using `pytest tests/test_ingestion.py`.

### Phase 2: Smart Dispatch & Multi-Agent Parallel Analysis
- **Description:** The Planner Agent evaluates the uploaded file manifest. It activates only the domain-specific specialist agents needed for the files (saving 30-60% on tokens). Active specialists query the Elasticsearch BM25 index in parallel using custom synonym expansion and taxonomy filters.
- **Key Modules:** `src/debate/orchestrator.py`, `src/debate/personas.py`.
- **Developer Action:** Test parallel thread execution and verify Ollama API response formats.

### Phase 3: Findings Aggregation & Dimension Mapping Gating
- **Description:** Collects the specialist findings and groups them by the 8 Core Dimensions (Risk, Valuation, Strategic Fit, etc.). A gating check is applied: if a dimension has fewer than 3 verified findings, it skips the debate engine entirely and writes findings straight to the evidence gap report, preventing speculative LLM compute.
- **Key Modules:** `src/debate/orchestrator.py`.
- **Developer Action:** Mock dimension mappings and verify gating filters.

### Phase 4: Gated Multi-Persona Adversarial Debate Loop (DebateOS)
- **Description:** Coordinates the 6 debate personas debating the gated dimensions across a maximum of 3 rounds. The Steelman rule constraint is programmatically checked at the Pydantic level. Each round executes 5 reliability gates (validation, citations verification, contradiction checks, stance calibration, and consensus checks).
- **Key Modules:** `src/debate/personas.py`, `src/debate/schemas.py`.
- **Developer Action:** Verify that local Ollama models (Llama 3 / Qwen) handle Pydantic schema constraints and execute the validation auto-retry loops on failures.

### Phase 5: Deterministic Consensus Mapping
- **Description:** Aggregates the final stances of the debate personas using a local majority-rule counting algorithm (avoiding LLM API calls). Sorts findings into three states: **Settled**, **Contested**, or **Unresolved**.
- **Key Modules:** `src/debate/orchestrator.py`.
- **Developer Action:** Assert consensus mapping outputs by feeding mock stances.

### Phase 6: Context-Filtered Judge Synthesis
- **Description:** The Judge Agent processes only findings marked as **Contested** or **Unresolved** (filtering out Settled stances), reducing context token volume by up to 90%. The Judge synthesizes final verdicts and appends calibrated confidence indexes.
- **Key Modules:** `src/debate/personas.py`.
- **Developer Action:** Run mock inputs through the Judge prompts.

### Phase 7: Structured Verdict & Delta Engine
- **Description:** Generates the final Go/No-Go Brief, Human Escalation List, and Evidence Gap Report. Enables delta reanalysis for document supplements without full reprocessing. User disputes trigger selective re-indexing and re-analysis of affected specialists.
- **Key Modules:** `src/api/main.py`, `src/hitl/delta_engine.py`, `src/db/models.py`.
- **Developer Action:** Query FastAPI endpoints and verify delta tracking logic.

### Phase 8: Advanced Escalation & Approval Workflow
- **Description:** Provides multi-level escalation routing for findings requiring human judgment. Implements approval chains with priority management, SLA tracking (4-hour alert), and immutable audit trails. Escalations can be resolved with human decisions, triggering delta re-analysis or verdict updates. Disputes are logged additively without destroying original AI reasoning.
- **Key Modules:** `src/hitl/escalation.py`, `src/hitl/dispute.py`, `src/hitl/audit.py`, `src/api/routes/escalations.py`.
- **Developer Action:** Verify escalation workflow APIs, approval chain state transitions, and append-only audit enforcement.

---

## Part 2: Local Services Execution Setup

Ensure the following local open-source infrastructure services are running before running the pipeline or testing:

### A. Local LLM Service (Ollama)
Ensure Ollama is running and has the target models downloaded:
```cmd
cmd /c ollama pull llama3
cmd /c ollama pull qwen2.5
```
Ensure Ollama is accessible at `http://localhost:11434`.

### B. Vectorless Search Engine (Elasticsearch)
Ensure a local Elasticsearch cluster is running on port `9200`:
```cmd
cmd /c curl -I http://localhost:9200
```

### C. Message Broker & Key-Value Store (Redis)
Ensure Redis is running locally on port `6379`.

---

## Part 3: Iterative Developer Loop

Collaborating developers (humans or AI agents) must follow this 5-step loop:

1. **Pull Task State:** Inspect [tasks.md](file:///d:/projects/VerdictOS/tasks.md) and [state.md](file:///d:/projects/VerdictOS/memory/state.md). Mark target task as in-progress `[/]`.
2. **Implement Component:** Code under `/src` following the [component_specifications.md](file:///d:/projects/VerdictOS/memory/component_specifications.md) contracts.
3. **Verify with Targeted Tests:** Execute tests in the `cmd` terminal:
   ```cmd
   cmd /c pytest tests/test_ingestion.py
   ```
4. **Delete Temporary Artifacts:** Delete any local scratch scripts, parsed outputs, or text file dumps generated during coding or testing to keep the repository clean.
5. **Update State & ADRs:** Mark task as complete `[x]` in [tasks.md](file:///d:/projects/VerdictOS/tasks.md), update percentages in [state.md](file:///d:/projects/VerdictOS/memory/state.md), and document new patterns in [decisions.md](file:///d:/projects/VerdictOS/memory/decisions.md).
