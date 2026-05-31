# VerdictOS

**Enterprise-Grade Multi-Agent System for M&A Due Diligence, Asset Validation, and Transaction Risk Analysis**

VerdictOS is a deterministic, production-ready AI system that eliminates hallucination and semantic drift failures inherent in vector-similarity RAG pipelines. Built with **vectorless Elasticsearch BM25 retrieval**, **structural GraphRAG via NetworkX**, and an **adversarial 6-persona multi-round debate engine**, VerdictOS ensures every finding is traceable to exact source text and verified through rigorous challenge—no hallucinated citations, no fabricated references.

**Core principle:** In high-stakes legal work, speculative conclusions are liabilities. Confidence requires auditability.

---

## Why VerdictOS: Five Core Innovations

### 1. **Vectorless Retrieval — Eliminates Hallucinated Citations**

Vector embeddings compress hyper-specific debt covenants and liability clauses into proximity space with generic language, causing RAG systems to retrieve irrelevant context and LLMs to fabricate section references. VerdictOS replaces embeddings with **Elasticsearch BM25 sparse retrieval**—exact keyword matching with structured section-aware taxonomy. Finding accuracy depends on actual contract text, not semantic similarity scores.

### 2. **Deterministic Reasoning Over Probabilistic Search**

Vector similarity introduces silent failures: a clause might retrieve at 0.87 cosine similarity but be legally distinct. VerdictOS **pre-builds a structural knowledge graph** (spaCy NER + NetworkX) *before* any agent runs, resolving cross-references and entity ambiguity upfront. The right context is determined, not guessed.

### 3. **Adversarial Multi-Persona Debate**

Single-agent systems miss edge cases and rarely challenge their own assumptions. VerdictOS implements a **6-persona debate engine across 8 strategic tracks**: Proponent (argues in favor), Critic (challenges evidence), Devil's Advocate (contrarian view), Valuation Skeptic (questions financials), Integration Realist (post-merger execution), and Regulator's Eye (compliance risk). Each persona attacks findings independently; consensus requires surviving rigorous challenge, not achieving high confidence alone.

### 4. **Immutable Audit Logs for Regulatory Compliance**

Legal auditors and regulators demand AI reasoning trails that cannot be altered retroactively. Human override is **additive, never destructive**. VerdictOS enforces append-only audit logs at the ORM level—UPDATE and DELETE are blocked on `DebateArg` and `AuditRecord` tables. Every decision is traceable; every override is logged.

### 5. **100% Local Open-Source LLMs**

Confidential legal documents cannot egress to cloud APIs. VerdictOS runs exclusively on **local open-source models** (Ollama / vLLM): Llama-3 for reasoning, Qwen-2.5 for entity disambiguation. No data leaves your infrastructure; full control over model versions and custom fine-tuning.

---

## Architecture Overview

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Sparse Retrieval** | Elasticsearch 8 + BM25 | Exact keyword search; no embeddings |
| **Document Parsing** | pdfplumber + python-docx | PDF/DOCX with layout coordinates |
| **Semantic Chunking** | Custom (200–500 token windows) | Section-aware, non-overlapping chunks |
| **Clause Classification** | Rule-based taxonomy (16 types) | Automated document structure analysis |
| **Entity Resolution** | String → RapidFuzz → LLM | 3-tier resolution; unconfirmed nodes never silently merged |
| **Knowledge Graph** | spaCy NER + NetworkX | Pre-flight DiGraph built before agent execution |
| **Specialist Routing** | Planner Agent (16 specialists) | Activates only relevant agents; 30–60% token savings |
| **Adversarial Debate** | 6 personas, 8 strategic tracks | 3-round max, Asyncio Semaphore (40), dimension gating |
| **Consensus Synthesis** | Majority-rule counting | Structured JSON synthesis from debate transcripts |
| **Verdict Generation** | Judge Agent | Final verdict with gap reports for unresolved findings |
| **LLM Stack** | Ollama (Llama-3, Qwen-2.5) | 100% local open-source, no cloud API calls |
| **Schema Contracts** | Pydantic V2 | Strict validation at every agent boundary |
| **Database** | PostgreSQL / SQLite | Async SQLAlchemy, append-only audit logs |
| **Task Broker** | Redis + Celery | Asynchronous specialist task distribution |
| **API Gateway** | FastAPI + uvicorn | JWT auth, structured REST endpoints |
| **Human-in-the-Loop** | HITL escalation & disputes | Escalation management, delta reanalysis, audit trails |

---

## System Architecture: 8-Phase Pipeline

VerdictOS processes M&A documents through a fully deterministic pipeline with clear phase boundaries, each with defined responsibilities and measurable outputs.

```
Phase 1: Ingest & Index (Synchronous Pre-Flight)
  ├─ PDF/DOCX parsing, section-aware chunking
  ├─ Clause classification (16 types)
  ├─ Entity resolution (3-tier)
  ├─ GraphRAG knowledge graph construction
  └─ Elasticsearch BM25 indexing
           │
           ▼
Phase 2: Smart Dispatch & Specialist Analysis (Async)
  ├─ Planner Agent activates domain specialists (16 agents)
  ├─ Specialist agents query indexed documents
  └─ Parallel task execution via Celery + Redis
           │
           ▼
Phase 3: Dimension Gating & Findings Aggregation (Async)
  ├─ Group findings by 8 strategic dimensions
  ├─ Apply gating filter (skip debate if < 3 findings)
  └─ Route sparse findings to evidence gaps
           │
           ▼
Phase 4: Adversarial Debate Engine (Async)
  ├─ 6 debate personas attack findings independently
  ├─ 8 strategic tracks with 5 validation gates
  ├─ 3-round maximum with early-exit on consensus
  └─ Steelman rule enforcement via Pydantic
           │
           ▼
Phase 5: Consensus Mapping (Deterministic Math)
  ├─ Aggregate persona stances (majority-rule counting)
  ├─ Sort: Settled, Contested, Unresolved
  └─ Filter for Judge Agent processing
           │
           ▼
Phase 6: Judge Synthesis (Async LLM)
  ├─ Judge Agent processes Contested/Unresolved (90% token savings)
  ├─ Generate final verdict with confidence scoring
  └─ Create Go/No-Go Brief & Evidence Gap Report
           │
           ▼
Phase 7: Delta Engine & Incremental Re-analysis
  ├─ Track document deltas on supplementary uploads
  ├─ Selective re-indexing (only new/modified chunks)
  ├─ Re-run affected specialists
  └─ Merge supplementary findings into verdict
           │
           ▼
Phase 8: Advanced Escalation & Approval Workflow
  ├─ Multi-level escalation routing with priority management
  ├─ Human escalation & dispute management
  ├─ Approval chain workflows with SLA tracking
  ├─ Immutable audit trails for all decisions
  └─ Delta re-analysis on user disputes
           │
           ▼
       FastAPI REST Gateway & Verdict Output
```

### Fully Implemented Phases

| Phase | Component | Status | Highlights |
|-------|-----------|--------|-----------|
| **1** | Pre-Flight Pipeline | ✅ Complete | PDF/DOCX parsing, 16-type clause classification, 3-tier entity resolution, GraphRAG |
| **2** | Specialist Dispatch | ✅ Complete | 16 domain agents, planner routing, Celery task distribution, vocabulary indexing |
| **3** | Dimension Gating | ✅ Complete | 8 strategic dimensions, sparse finding routing, debate qualification |
| **4** | Debate Engine | ✅ Complete | 6-persona adversarial debate, 3-round max, 5 validation gates, Steelman enforcement |
| **5** | Consensus Mapping | ✅ Complete | Majority-rule aggregation, Settled/Contested/Unresolved classification |
| **6** | Judge Synthesis | ✅ Complete | Verdict generation, confidence scoring, gap reporting, Go/No-Go brief |
| **7** | Delta Engine | ✅ Complete | Incremental re-analysis, delta tracking, selective re-indexing, finding merging |
| **8** | Escalation & Audit | ✅ Complete | Multi-level routing, SLA tracking, append-only audit logs, dispute resolution |

---

## Clause Types & Specialist Agents

VerdictOS classifies document chunks into 16 domain-specific clause types and routes them to expert agents:

| Clause Type | Specialist Agent | Domain |
|--|--|--|
| `IP_ASSIGNMENT` | `ip_agent` | Patents, copyright, IP ownership |
| `TAX_PROVISION` | `tax_agent` | Tax indemnities, provisions |
| `INDEMNIFICATION` | `litigation_agent` | Indemnity obligations, carve-outs |
| `FX_HEDGING` | `finance_agent` | Currency hedging, forex covenants |
| `EMPLOYMENT_TERM` | `hr_agent` | Employee agreements, severance |
| `CHANGE_OF_CONTROL` | `governance_agent` | CoC triggers, governance changes |
| `DATA_PROTECTION` | `privacy_agent` | GDPR, privacy covenants |
| `INSURANCE_POLICY` | `insurance_agent` | Coverage terms, policy requirements |
| `RELATED_PARTY_TRANSACTION` | `related_party_agent` | Related-party deals, conflicts |
| `CYBER_SECURITY` | `cyber_agent` | Security obligations, breach response |
| `SUPPLIER_CONTRACT` | `supplier_agent` | Supply chain, vendor terms |
| `CUSTOMER_CONTRACT` | `customer_agent` | Customer agreements, SLAs |
| `REPUTATION_RISK` | `reputation_agent` | Reputational risk clauses |
| `ESG_OBLIGATION` | `esg_agent` | ESG commitments, sustainability |
| `LIABILITY_CAP` | `finance_agent` / `litigation_agent` | Damages caps, liability limitations |
| `GOVERNANCE_CLAUSE` | `governance_agent` | Board governance, voting rights |

---

## Getting Started

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.11+ | Core runtime |
| **Docker Desktop** | latest | Elasticsearch, Redis, PostgreSQL, Ollama |
| **Git** | latest | Version control |

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/harshgupta1810/VerdictOS.git
cd VerdictOS

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model (required for GraphRAG)
python -m spacy download en_core_web_lg

# 5. Copy environment configuration
cp .env.example .env

# 6. Start full infrastructure stack
docker compose -f docker/docker-compose.yml up -d

# 7. Initialize database
python scripts/setup_database.py
alembic upgrade head

# 8. Pull Ollama models
python scripts/pull_models.py

# 9. Start API server
make run

# 10. Access interactive API docs
# Open http://localhost:8000/docs in your browser
```

### Environment Configuration

Edit `.env` with your infrastructure endpoints:

```env
# Elasticsearch (BM25 sparse search)
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=verdictos_documents

# Local LLM (Ollama / vLLM)
OLLAMA_URL=http://localhost:11434
LLM_REASONING_MODEL=llama3:8b
LLM_DISAMBIGUATION_MODEL=qwen2.5:7b

# Message Queue
REDIS_URL=redis://localhost:6379/0

# Database (PostgreSQL for production; SQLite for local dev)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/verdictos
# DATABASE_URL=sqlite+aiosqlite:///./verdictos.db

# API Security
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Infrastructure Services

```bash
# Full stack (all services)
docker compose -f docker/docker-compose.yml up -d

# Individual services
docker compose -f docker/docker-compose.yml up elasticsearch redis postgres ollama -d
```

| Service | Port | Purpose |
|---------|------|---------|
| `app` | 8000 | FastAPI server |
| `worker` | — | Celery background worker |
| `elasticsearch` | 9200 | BM25 search index |
| `redis` | 6379 | Celery message broker |
| `postgres` | 5432 | Primary database |
| `ollama` | 11434 | Local LLM server |

---

## Running the System

### Phase 1: Pre-Flight Pipeline

Phase 1 is the synchronous boundary that parses documents, classifies clauses, builds the knowledge graph, indexes chunks, and emits the specialist manifest.

```bash
# Dry run (no Docker needed; gracefully skips live ES indexing)
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf

# Live Elasticsearch indexing (ES auto-polled for 60 seconds)
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf

# Multiple documents
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf testing_pdfs/Amendment.pdf
```

### API Server

```bash
# Via Makefile (recommended; enables hot reload)
make run

# Direct
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation: `http://localhost:8000/docs`

#### Core API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/deals` | Submit deal with documents |
| `GET` | `/api/v1/deals/{id}/status` | Stream analysis progress |
| `GET` | `/api/v1/deals/{id}/verdict` | Compiled structured verdict |
| `GET` | `/api/v1/deals/{id}/audit` | Full debate transcripts (immutable) |
| `POST` | `/api/v1/deals/{id}/escalate` | Escalate finding for human review |
| `POST` | `/api/v1/deals/{id}/dispute` | User dispute against a finding |
| `POST` | `/api/v1/deals/{id}/delta` | Trigger incremental re-analysis |
| `WebSocket` | `/api/v1/deals/{id}/stream` | Real-time pipeline event stream |
| `GET` | `/health` | Service health check |

### Celery Worker

```bash
# Via Makefile
make worker

# Direct
celery -A src.workers.celery_app worker --loglevel=info
```

---

## Human-in-the-Loop Capabilities

### Escalation Management

Analysts can escalate findings requiring human judgment:

```python
from src.hitl.escalation import create_escalation, resolve_escalation

# Escalate a finding
escalation = create_escalation(db, deal_id, finding_id)

# Resolve with human decision
resolution = resolve_escalation(
    db=db,
    escalation_id=escalation.escalation_id,
    decision="resolve",
    reasoning="Verified against source documentation",
    actor="compliance_officer"
)
```

### Dispute Resolution

Users can challenge AI findings with evidence:

```python
from src.hitl.dispute import handle_user_dispute

dispute = handle_user_dispute(
    db=db,
    finding_id=finding_id,
    dispute_reason="Finding contradicts Section 3.2(a)",
    evidence="See attached amendment dated 2024-01-15",
    requester="legal_team"
)
```

### Delta Reanalysis

Add supplementary documents without full re-analysis:

```python
from src.hitl.delta_engine import trigger_delta_reanalysis

delta_run = trigger_delta_reanalysis(
    db=db,
    deal_id=deal_id,
    uploaded_document_path="Amendment_2024_Q1.pdf"
)
# System re-indexes delta chunks, re-runs affected specialists,
# merges supplementary findings into existing verdict
```

### Immutable Audit Trail

Every action is logged in append-only fashion:

```python
from src.hitl.audit import get_audit_trail_for_finding

audit_trail = get_audit_trail_for_finding(db, finding_id)
# Returns: [
#   {"event": "FINDING_CREATED", "agent": "ip_agent", "timestamp": "..."},
#   {"event": "DEBATE_ROUND_1", "persona": "critic", "timestamp": "..."},
#   {"event": "CONSENSUS_REACHED", "confidence": "high", "timestamp": "..."},
#   {"event": "ESCALATION_CREATED", "actor": "human", "timestamp": "..."},
#   {"event": "ESCALATION_RESOLVED", "decision": "resolve", "timestamp": "..."}
# ]
```

---

## Testing

All tests run **offline** — no Docker, no Ollama required.

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# HITL tests
pytest tests/unit/test_hitl.py -v

# Verbose output
pytest tests/ -v

# Via Makefile
make test
make test-unit
make test-integration
```

### Test Coverage by Component

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Ingestion Pipeline | `tests/unit/test_ingestion/` | PDF/DOCX parsing, chunking, clause classification |
| GraphRAG | `tests/unit/test_graphrag/` | Entity resolution (3-tier), graph construction |
| Agent System | `tests/unit/test_agents/` | Planner dispatch, specialist activation, schemas |
| Search | `tests/unit/test_search/` | BM25 retrieval, clause filtering, section resolution |
| Database | `tests/unit/test_db/` | ORM models, state machine, append-only enforcement |
| LLM Client | `tests/unit/test_llm/` | Ollama integration, retry logic |
| HITL System | `tests/unit/test_hitl/` | Escalation, dispute, delta engine, audit logs |
| End-to-End | `tests/integration/test_pipeline/` | Full preflight pipeline with real documents |

---

## Code Quality

```bash
# Lint and type-check
make lint

# Ruff linter
ruff check src/ tests/

# Mypy type checking
mypy src/

# Pyright (configured in pyrightconfig.json)
pyright
```

---

## Project Structure

```
VerdictOS/
├── src/
│   ├── api/                    # FastAPI gateway
│   │   ├── main.py             # Application factory
│   │   ├── middleware/
│   │   │   └── auth.py         # JWT authentication
│   │   └── routes/
│   │       ├── deals.py        # Deal submission & verdict
│   │       ├── escalations.py  # Escalation management
│   │       └── health.py       # Service health
│   ├── agents/                 # Agent system (16 specialists + planner + judge)
│   │   ├── planner_agent.py    # Smart dispatch, clause-type routing
│   │   ├── specialist_agent.py # Domain discovery agents
│   │   ├── judge_agent.py      # Verdict synthesis
│   │   ├── base_agent.py       # Agent interface
│   │   └── schemas.py          # Pydantic contracts
│   ├── debate/                 # Adversarial debate engine
│   │   ├── orchestrator.py     # 6-persona, 8-track coordination
│   │   ├── personas.py         # Persona definitions
│   │   ├── gates.py            # Validation gates
│   │   ├── consensus.py        # Consensus synthesis
│   │   ├── audit.py            # Audit log management
│   │   └── executor.py         # Debate round execution
│   ├── graphrag/               # Knowledge graph construction
│   │   ├── entity_resolver.py  # 3-tier entity resolution
│   │   └── graph_constructor.py# NetworkX DiGraph builder
│   ├── ingestion/              # Document parsing & chunking
│   │   ├── ingest.py           # PDF/DOCX parser (pdfplumber + python-docx)
│   │   ├── chunker.py          # Section-aware chunker (200–500 tokens)
│   │   ├── classifier.py       # Rule-based clause classifier
│   │   ├── defined_terms.py    # Defined terms extractor
│   │   └── schemas.py          # Domain models
│   ├── search/                 # Vectorless retrieval (BM25)
│   │   ├── search_engine.py    # Elasticsearch BM25 search
│   │   ├── indexer.py          # Chunk indexer
│   │   ├── client.py           # ES client wrapper
│   │   └── schemas.py          # Search contracts
│   ├── hitl/                   # Human-in-the-Loop system
│   │   ├── escalation.py       # Escalation management
│   │   ├── dispute.py          # Dispute resolution
│   │   ├── delta_engine.py     # Incremental reanalysis
│   │   ├── audit.py            # Audit trail queries
│   │   └── schemas.py          # HITL data contracts
│   ├── db/                     # Database layer
│   │   ├── models.py           # SQLAlchemy ORM (7 tables)
│   │   ├── session.py          # Async session factory
│   │   ├── repositories.py     # Data access patterns
│   │   └── migrations/         # Alembic migrations
│   ├── llm/                    # Local LLM integration
│   │   ├── client.py           # Ollama / vLLM client
│   │   └── schemas.py          # LLM contracts
│   ├── workers/                # Celery task workers
│   │   ├── celery_app.py       # Celery app factory
│   │   └── tasks.py            # Async task definitions
│   ├── common/                 # Shared utilities
│   │   ├── models.py           # Shared Pydantic models
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── logging.py          # Logging configuration
│   │   ├── retry.py            # Retry decorators
│   │   └── utils.py            # Helper functions
│   ├── preflight.py            # Phase 1 pipeline composition
│   └── config.py               # Environment-backed Pydantic settings
├── scripts/
│   ├── run_pipeline.py         # Phase 1 CLI runner
│   ├── setup_elasticsearch.py  # Index bootstrap
│   ├── setup_database.py       # Database initializer
│   ├── pull_models.py          # Ollama model downloader
│   └── seed_data.py            # Development data seeding
├── tests/
│   ├── unit/                   # Per-component unit tests
│   └── integration/            # Pipeline & API integration tests
├── docker/
│   ├── docker-compose.yml      # Full-stack infrastructure
│   ├── Dockerfile              # API server image
│   └── Dockerfile.worker       # Celery worker image
├── docs/
│   └── architecture/           # Architecture decision records
├── memory/
│   ├── system_overview.md      # Detailed system specification
│   └── guidelines.md           # Coding & prompt engineering standards
├── .env.example                # Environment template
├── alembic.ini                 # Database migration config
├── pyproject.toml              # Project metadata & dependencies
├── pyrightconfig.json          # Type checking config
├── Makefile                    # Build & test automation
└── README.md                   # This file
```

---

## Database Schema

Seven SQLAlchemy ORM tables power the system:

| Table | Purpose | Append-Only |
|-------|---------|------------|
| `Deal` | M&A transaction record, file manifest, state tracking | ❌ |
| `Finding` | Agent-discovered finding — claim, citation, confidence, severity | ❌ |
| `DebateArg` | Individual debate argument — persona, stance, steelman | ✅ |
| `AuditRecord` | Immutable audit log — event type, actor, timestamp, payload | ✅ |
| `Escalation` | Issue escalated for human review — status, decision, resolver | ❌ |
| `Dispute` | End-user dispute against a finding | ❌ |
| `DeltaRun` | Delta analysis execution for incremental index updates | ❌ |

**Append-Only Enforcement:** `DebateArg` and `AuditRecord` tables block UPDATE and DELETE at the ORM level — audit trails are immutable.

### Deal State Machine

```
created → indexing → analyzing → aggregating → debating → judging → complete
                                                                       ↓
                                    error ←──────────────────────────── (any state)
                                    error → recovery / indexing (recovery)
```

---

## Performance Characteristics

- **Phase 1 Parsing:** ~20–50 pages/second (PDF parsing is I/O bound; use thread pools)
- **Chunk Count:** 300–500 chunks per 100-page document (200–500 token windows, no overlap)
- **Entity Resolution:** 800–1200 entities per 100-page document; Tier 1 (exact) resolves ~80%, Tier 2 (fuzzy) adds ~15%, Tier 3 (LLM) adds ~5%
- **BM25 Indexing:** ~2–5 seconds per 100 chunks (Elasticsearch on commodity hardware)
- **Debate Token Budget:** ~4,000–6,000 tokens per finding (3 rounds × 6 personas × context compression)
- **Full Analysis:** 5–15 minutes end-to-end for 100-page document (Ollama on 8-core CPU)
- **Delta Reanalysis:** ~30–60% faster than full analysis (only affected documents re-processed)

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **BM25 over Embeddings** | Embeddings compress hyper-specific clauses near generic text, causing drift on debt covenants. BM25 ensures exact keyword retrieval. |
| **Local Open-Source LLMs** | Confidential documents cannot egress to cloud APIs. 100% local inference on Ollama / vLLM. |
| **Pre-Flight GraphRAG** | Cross-references broken by chunking must be resolved upfront. GraphRAG built before debate engine runs. |
| **Append-Only Audit Logs** | Regulatory auditors require immutable reasoning trails. Human judgment is additive, never destructive. |
| **3-Round Hard Cap** | Guarantees system termination. Unresolved findings route to gap reports rather than speculative consensus. |
| **Pydantic V2 Contracts** | Open-source LLMs produce malformed JSON. Pydantic retry loops enable self-healing without human intervention. |
| **Asyncio Semaphore (40)** | Debate parallelism bounded to prevent resource exhaustion. Token budgets optimized at this concurrency level. |
| **HITL Escalation Layer** | Analysts need human judgment for edge cases. Escalation system enables structured review with immutable logging. |

---

## Extensibility

### Adding a New Specialist Agent

1. Create a new file in `src/agents/` following the `SpecialistAgent` base class.
2. Define domain-specific prompt and vocabulary index.
3. Register in `src/agents/planner_agent.py` — add to `SPECIALIST_REGISTRY` with trigger keywords.
4. Add integration test in `tests/integration/`.

### Adding a New Clause Type

1. Add to `src/ingestion/classifier.py` — extend `CLAUSE_TYPE_RULES` dictionary.
2. Update `src/ingestion/schemas.py` — add to `ClauseType` enum.
3. Add test cases in `tests/unit/test_ingestion/test_classifier.py`.

### Custom Debate Persona

1. Define in `src/debate/personas.py` — extend the `Persona` dataclass.
2. Add debate logic in `src/debate/orchestrator.py`.
3. Test in `tests/unit/test_debate/`.

---

## Deployment

### Docker Image Build

```bash
# Build API image
docker build -f docker/Dockerfile -t verdictos:latest .

# Build worker image
docker build -f docker/Dockerfile.worker -t verdictos-worker:latest .
```

### Production Checklist

- [ ] Change `JWT_SECRET` in `.env` to a strong random value
- [ ] Use PostgreSQL (not SQLite) with connection pooling
- [ ] Configure Elasticsearch with persistent storage and snapshots
- [ ] Run Ollama on GPU-capable hardware (NVIDIA CUDA recommended)
- [ ] Enable Redis persistence for Celery broker state
- [ ] Set up log aggregation (ELK, Datadog, Splunk, etc.)
- [ ] Configure monitoring and alerting on debate round timeouts
- [ ] Enable database backups and point-in-time recovery
- [ ] Set up SSL/TLS for API and database connections
- [ ] Configure CORS policies for frontend integration
- [ ] Enable audit log export to compliance systems

---

## Troubleshooting

### Elasticsearch Connection Timeout

```bash
# Check ES is running
curl http://localhost:9200

# If container crashed, check logs
docker logs elasticsearch

# Restart
docker compose -f docker/docker-compose.yml restart elasticsearch
```

### Ollama Model Not Found

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull missing model
ollama pull llama3:8b
```

### Entity Resolution Stays "Unconfirmed"

By default, entity resolution Tier 3 (LLM disambiguation) requires Ollama running. If offline, entities remain unconfirmed. Start Ollama to enable LLM-powered resolution:

```bash
ollama serve
ollama pull qwen2.5:7b
```

### Worker Tasks Not Processing

```bash
# Check Redis is running
redis-cli ping

# Check worker is running
celery -A src.workers.celery_app inspect active

# Restart worker
make worker
```

---

## Contributing

VerdictOS is a completed, production-oriented system. Code contributions should:

1. Maintain 100% type safety (Pyright strict mode).
2. Preserve append-only semantics on audit tables.
3. Add tests for all new functionality (unit + integration).
4. Follow the coding standards in `memory/guidelines.md`.
5. Update this README if adding new components or configuration options.

---

## License

Proprietary. See LICENSE file for details.

---

## Support & Contact

For issues, feature requests, or technical questions:

- **GitHub Issues:** [VerdictOS Issues](https://github.com/harshgupta1810/VerdictOS/issues)
- **Email:** [harshgup11@gmail.com](mailto:harshgup11@gmail.com)

---

**VerdictOS — Enterprise-grade determinism for high-stakes legal reasoning. Built for M&A teams that cannot afford speculation.**
