# VerdictOS Phase Linkage & Execution Flow

Complete documentation of how all 8 phases of the VerdictOS pipeline connect and interact.

---

## Quick Reference: Phase Dependencies

```
Phase 1 (Input) → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 (Output)
  Ingest        Dispatch   Gating    Debate   Consensus  Judge     Delta      Escalation
  & Index       & Search   & Filter  Engine   Mapping    Synthesis  Engine     & Approval
```

---

## Detailed Phase Flow

### Phase 1: Pre-Flight Pipeline (Synchronous Boundary)

**Input:** PDF/DOCX documents  
**Output:** Indexed chunks, GraphRAG, specialist manifest

**Responsibilities:**
- Parse documents with layout-aware chunking (200-500 tokens)
- Extract and classify clauses into 16 domain-specific types
- Resolve entity naming variations (3-tier: exact → fuzzy → LLM)
- Build NetworkX knowledge graph with cross-references
- Index all chunks in Elasticsearch via BM25
- Generate active-specialist manifest based on clause types found

**Key Modules:**
- `src/ingestion/ingest.py` — Document parser
- `src/ingestion/chunker.py` — Section-aware chunker
- `src/ingestion/classifier.py` — Clause type classifier
- `src/graphrag/entity_resolver.py` — 3-tier entity resolution
- `src/graphrag/graph_constructor.py` — NetworkX graph builder
- `src/search/indexer.py` — Elasticsearch indexer

**Output Schema:**
```python
{
    "document_id": str,
    "chunks_indexed": int,
    "entities_resolved": int,
    "graph_nodes": int,
    "active_specialists": ["ip_agent", "finance_agent", ...]
}
```

**Dependencies:** None (entry point)

---

### Phase 2: Smart Dispatch & Specialist Analysis (Async)

**Input:** Active specialist manifest from Phase 1  
**Output:** Domain-specific findings grouped by dimension

**Responsibilities:**
- Activate Planner Agent to assess document manifest
- Dispatch only relevant domain specialist agents (30-60% token savings)
- Each specialist queries Elasticsearch with custom synonym expansion
- Retrieve context chunks and generate findings
- Aggregate findings by 8 strategic dimensions

**Key Modules:**
- `src/agents/planner_agent.py` — Manifest assessment & routing
- `src/agents/specialist_agent.py` — Domain discovery agents
- `src/workers/celery_app.py` — Task broker & worker execution
- `src/search/search_engine.py` — BM25 query expansion

**Specialist Registry (16 agents):**
- `ip_agent`, `litigation_agent`, `tax_agent`, `finance_agent`
- `hr_agent`, `governance_agent`, `privacy_agent`, `insurance_agent`
- `related_party_agent`, `cyber_agent`, `supplier_agent`, `customer_agent`
- `reputation_agent`, `esg_agent`, `regulatory_agent`, `assets_agent`

**Output Schema:**
```python
{
    "findings": [
        {
            "finding_id": str,
            "specialist": str,
            "dimension": str,  # Risk Exposure, Valuation, etc.
            "claim": str,
            "evidence": [{"chunk_id": str, "quote": str}],
            "confidence": float
        }
    ]
}
```

**Dependencies:** Phase 1 (indexed chunks, specialist manifest)

---

### Phase 3: Aggregation & Dimension Gating (Async)

**Input:** Specialist findings from Phase 2  
**Output:** Gated findings ready for debate or direct gap reporting

**Responsibilities:**
- Group all findings by the 8 strategic dimensions
- Apply gating filter: dimensions with < 3 verified findings skip debate
- Route sparse findings directly to evidence gap report
- Prepare debate-ready findings with dimension context

**Key Modules:**
- `src/debate/orchestrator.py` — Dimension mapping & gating logic

**8 Strategic Dimensions:**
1. Risk Exposure
2. Valuation Fairness
3. Strategic Fit
4. Synergy Validity
5. Integration Complexity
6. Market Timing
7. Regulatory Approval
8. Exit Scenario

**Output Schema:**
```python
{
    "gated_findings": {
        "risk_exposure": [findings...],  # ≥ 3 findings
        "valuation": [findings...]       # ≥ 3 findings
    },
    "gap_findings": {
        "market_timing": [findings...]   # < 3 findings (skip debate)
    }
}
```

**Dependencies:** Phase 2 (specialist findings)

---

### Phase 4: Adversarial Debate Engine (Async)

**Input:** Gated findings from Phase 3  
**Output:** Debate transcripts with stance scores

**Responsibilities:**
- Coordinate 6 debate personas across 8 strategic tracks
- Execute maximum 3 rounds of debate with early-exit on consensus
- Enforce Steelman rule (every persona must provide counter-argument)
- Execute 5 validation gates at each round:
  1. Schema Verification (Pydantic validation)
  2. Citation Validation (BM25 verification)
  3. Self-Contradiction Check
  4. Stance Calibration
  5. Consensus Check

**Key Modules:**
- `src/debate/orchestrator.py` — Round coordination
- `src/debate/personas.py` — Persona prompts & logic
- `src/debate/schemas.py` — Pydantic contracts
- `src/debate/executor.py` — Debate round execution
- `src/debate/gates.py` — Validation gates

**6 Debate Personas:**
1. **Skeptic** — Questions all assumptions
2. **Extremist** — Worst-case scenario
3. **Pragmatist** — Balanced assessment
4. **Risk-Focused** — Emphasizes liabilities
5. **Compliance** — Regulatory lens
6. **Business** — Strategic value lens

**Output Schema:**
```python
{
    "debate_rounds": [
        {
            "round_number": int,
            "arguments": [
                {
                    "persona": str,
                    "stance": float,  # -1.0 (opposed) to +1.0 (favors)
                    "reasoning": str,
                    "steelman": str,
                    "gates_passed": [bool, bool, bool, bool, bool]
                }
            ],
            "consensus_reached": bool
        }
    ]
}
```

**Dependencies:** Phase 3 (gated findings), Phase 1 (indexed chunks for citation validation)

---

### Phase 5: Consensus Mapping (Deterministic Math)

**Input:** Debate transcripts from Phase 4  
**Output:** Sorted findings by consensus state

**Responsibilities:**
- Aggregate persona stances using majority-rule counting (no LLM needed)
- Classify findings into three states:
  - **Settled:** Consensus across ≥ 4 personas
  - **Contested:** Mixed stances (2-3 pros, 2-3 cons)
  - **Unresolved:** Insufficient consensus or early exit
- Prepare filtered input for Judge Agent

**Key Modules:**
- `src/debate/orchestrator.py` — Consensus mapping algorithm

**Output Schema:**
```python
{
    "settled_findings": [...],           # Unanimous or near-unanimous
    "contested_findings": [...],         # Mixed debate
    "unresolved_findings": [...]         # No consensus
    "consensus_score": float
}
```

**Dependencies:** Phase 4 (debate transcripts)

---

### Phase 6: Judge Synthesis (Async LLM)

**Input:** Consensus states from Phase 5  
**Output:** Final verdict with confidence scores

**Responsibilities:**
- Filter input: process only Contested + Unresolved (avoid Settled)
- Reduce token budget by filtering 90% of settled findings
- Generate final verdict with confidence scoring
- Create Go/No-Go Brief
- Compile Evidence Gap Report

**Key Modules:**
- `src/agents/judge_agent.py` — Verdict synthesis
- `src/llm/client.py` — Local LLM (Ollama/vLLM)

**Output Schema:**
```python
{
    "verdict": {
        "go_no_go": "GO" | "NO_GO" | "CONDITIONAL",
        "confidence_score": float,
        "key_findings": [...],
        "escalation_list": [...],
        "evidence_gaps": [...]
    }
}
```

**Dependencies:** Phase 5 (consensus mapping)

---

### Phase 7: Verdict & Delta Engine

**Input:** Judge verdict from Phase 6  
**Output:** Stored verdict, trackable deltas

**Responsibilities:**
- Persist verdict to database
- Enable delta reanalysis for supplementary documents
- Track document versions and chunk deltas
- On delta submission: selectively re-index only new/modified chunks
- Re-run affected specialists with delta context
- Merge supplementary findings into existing verdict

**Key Modules:**
- `src/api/main.py` — Verdict storage endpoints
- `src/hitl/delta_engine.py` — Delta tracking & reanalysis
- `src/db/models.py` — Verdict persistence
- `src/db/repositories.py` — Data access patterns

**Output Schema:**
```python
{
    "verdict_id": str,
    "deal_id": str,
    "verdict": {...},
    "delta_enabled": bool,
    "document_versions": {"original": str, "deltas": [str]}
}
```

**Dependencies:** Phase 6 (judge verdict), Phase 1 (for delta re-indexing)

---

### Phase 8: Advanced Escalation & Approval Workflow

**Input:** Verdict + human disputes from Phase 7  
**Output:** Escalation decisions, audit trail, delta re-analysis triggers

**Responsibilities:**
- Route findings requiring human judgment to escalation queue
- Implement multi-level approval chains with priority routing
- Enforce SLA tracking (4-hour alert on timeout)
- Manage user disputes against AI findings
- Preserve immutable audit trails for all decisions
- Trigger delta re-analysis based on dispute evidence

**Key Modules:**
- `src/hitl/escalation.py` — Escalation management
- `src/hitl/dispute.py` — Dispute resolution
- `src/hitl/audit.py` — Audit trail queries
- `src/api/routes/escalations.py` — Escalation endpoints

**Escalation States:**
- `pending` → `assigned` → `in_review` → `resolved` or `rejected`

**Append-Only Tables:**
- `DebateArg` — No UPDATE/DELETE (debate transcript immutable)
- `AuditRecord` — No UPDATE/DELETE (all actions logged additively)

**Output Schema:**
```python
{
    "escalation": {
        "escalation_id": str,
        "finding_id": str,
        "status": "pending" | "assigned" | "resolved",
        "priority": "low" | "medium" | "high" | "critical",
        "sla_hours": int,
        "assigned_to": str,
        "decision": str,
        "reasoning": str,
        "actor": str,
        "created_at": datetime,
        "resolved_at": datetime
    },
    "audit_trail": [
        {"event": str, "actor": str, "timestamp": datetime}
    ]
}
```

**Dispute Handling:**
- User provides dispute reason + evidence
- System marks finding as disputed
- Delta re-analysis triggered with new evidence context
- Supplementary verdict generated

**Dependencies:** Phase 6 & 7 (verdict for escalation), Phase 1 (for delta re-indexing)

---

## Cross-Phase Data Models

### Finding Lifecycle

```
Phase 2: Created by specialist
    ↓
Phase 3: Grouped by dimension, gated
    ↓
Phase 4: Debated by 6 personas (3 rounds max)
    ↓
Phase 5: Sorted into Settled/Contested/Unresolved
    ↓
Phase 6: Synthesized into verdict (Contested/Unresolved only)
    ↓
Phase 7: Persisted to database
    ↓
Phase 8: Escalated/disputed for human review, audit trail appended
```

### Database Schema (7 Tables)

| Table | Purpose | Append-Only |
|-------|---------|------------|
| `Deal` | Transaction record, manifest | ❌ |
| `Finding` | Specialist discovery | ❌ |
| `DebateArg` | Debate argument | ✅ |
| `AuditRecord` | Immutable audit log | ✅ |
| `Escalation` | Human review item | ❌ |
| `Dispute` | User challenge | ❌ |
| `DeltaRun` | Incremental analysis | ❌ |

---

## API Endpoints by Phase

| Endpoint | Phase | Purpose |
|----------|-------|---------|
| `POST /api/v1/deals` | 1 | Submit documents |
| `GET /api/v1/deals/{id}/status` | 2-6 | Stream progress |
| `GET /api/v1/deals/{id}/verdict` | 6-7 | Retrieve verdict |
| `GET /api/v1/deals/{id}/audit` | 4,8 | Access debate transcripts |
| `POST /api/v1/deals/{id}/escalate` | 8 | Escalate finding |
| `POST /api/v1/deals/{id}/dispute` | 8 | Challenge finding |
| `POST /api/v1/deals/{id}/delta` | 7-8 | Upload supplementary doc |

---

## Concurrency & Resource Management

- **Asyncio Semaphore:** Max 40 concurrent debate operations
- **Celery Worker Pool:** Configurable task concurrency
- **Redis Broker:** Message queuing between phases
- **3-Round Hard Cap:** Guarantees Phase 4 termination
- **Elasticsearch Timeout:** 60-second polling on document indexing

---

## Testing by Phase

| Phase | Test File | Focus |
|-------|-----------|-------|
| 1 | `tests/unit/test_ingestion/` | Parsing, chunking, classification |
| 2 | `tests/unit/test_agents/` | Planner dispatch, specialist activation |
| 3 | `tests/unit/test_debate/` | Dimension gating, filtering |
| 4 | `tests/unit/test_debate/` | Persona logic, validation gates |
| 5 | `tests/unit/test_debate/` | Consensus mapping algorithm |
| 6 | `tests/unit/test_agents/` | Judge synthesis, confidence scoring |
| 7 | `tests/integration/test_pipeline/` | Delta engine, verdict persistence |
| 8 | `tests/unit/test_hitl.py` | Escalation, dispute, audit trails |

---

## Environment Configuration by Phase

```env
# Phase 1 & 7 (Elasticsearch)
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=verdictos_documents

# Phase 2 & 8 (Task Broker)
REDIS_URL=redis://localhost:6379/0

# Phase 4, 6 (Local LLM)
OLLAMA_URL=http://localhost:11434
LLM_REASONING_MODEL=llama3
LLM_DISAMBIGUATION_MODEL=qwen2.5

# Phase 1, 7, 8 (Database)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/verdictos

# Phase 5, 8 (API Security)
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
```

---

## Error Handling & Recovery

| Scenario | Recovery Phase |
|----------|----------------|
| ES indexing timeout (Phase 1) | Retry with exponential backoff; skip live indexing if offline |
| Specialist task timeout (Phase 2) | Celery task retry (3 attempts); mark as skipped if all fail |
| Debate deadlock (Phase 4) | Hard 3-round exit; route to gap report |
| LLM timeout (Phase 6) | Fallback to highest-confidence debate stance |
| Escalation SLA timeout (Phase 8) | Alert + escalate to manager queue |

---

## Reference Documentation

- **Architecture:** `memory/system_overview.md`
- **Components:** `memory/component_specifications.md`
- **Workflow:** `memory/workflow.md`
- **Decisions:** `memory/decisions.md`
- **README:** `README.md` (quick reference tables)
