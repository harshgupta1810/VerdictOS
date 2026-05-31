# VerdictOS

**Enterprise-Grade Multi-Agent System for M&A Due Diligence, Asset Validation, and Transaction Risk Analysis**

VerdictOS eliminates hallucination and semantic drift failures inherent in vector-similarity RAG pipelines by replacing them with a **deterministic, vectorless architecture**: Elasticsearch BM25 sparse retrieval, structural GraphRAG via NetworkX, and an adversarial 6-persona multi-round debate engine. Every finding is traceable to exact source text and verified through adversarial challenge — no hallucinated citations, no fabricated references.

**Core principle:** In high-stakes legal work, speculative conclusions are liabilities. Confidence requires auditability.

---

## Why VerdictOS

### 1. **Eliminates Hallucinated Citations**
Traditional RAG systems compress hyper-specific debt covenants near generic language, causing embeddings to retrieve irrelevant context and LLMs to fabricate section references. VerdictOS uses **BM25 sparse retrieval** (Elasticsearch) — exact keyword matching with no semantic compression — ensuring findings are anchored to actual contract text.

### 2. **Deterministic Reasoning Over Probabilistic Search**
Vector similarity introduces silent failure modes: a clause might retrieve as "similar enough" at 0.87 cosine similarity but be legally distinct. VerdictOS pre-builds a **structural knowledge graph** (spaCy NER + NetworkX) before any agent runs, resolving cross-references and entity ambiguity upfront — the right context is found, not guessed.

### 3. **Adversarial Multi-Persona Debate**
Single-agent systems miss edge cases and rarely challenge their own assumptions. VerdictOS implements a 6-persona debate engine with 8 strategic tracks: **Skeptic, Extremist, Pragmatist, Risk-Focused, Compliance, and Business**. Each persona attacks findings independently with isolated prompts; consensus requires surviving rigorous challenge, not achieving high confidence alone.

### 4. **Append-Only Audit Logs for Regulatory Compliance**
Legal auditors and regulators require immutable AI reasoning trails. Human override is additive, never destructive. VerdictOS enforces append-only audit logs at the ORM level — UPDATE and DELETE are blocked on `DebateArg` and `AuditRecord` tables. Every decision is traceable; every override is logged.

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
| **Consensus Synthesis** | Debate consensus mapper | Structured JSON synthesis from debate transcripts |
| **Verdict Generation** | Judge Agent | Final verdict with gap reports for unresolved findings |
| **LLM Stack** | Ollama (Llama-3, Qwen-2.5) | 100% local open-source, no cloud API calls |
| **Schema Contracts** | Pydantic V2 | Strict validation at every agent boundary |
| **Database** | PostgreSQL / SQLite | Async SQLAlchemy, append-only audit logs |
| **Task Broker** | Redis + Celery | Asynchronous specialist task distribution |
| **API Gateway** | FastAPI + uvicorn | JWT auth, structured REST endpoints |

---

## Clause Types & Specialist Agents

VerdictOS classifies document chunks into 16 domain-specific clause types and routes them to expert agents:

| Clause Type | Specialist Agent | Domain |
|--|--|--|
| `TAX_PROVISION` | `tax_agent` | Tax indemnities, provisions |
| `IP_ASSIGNMENT` | `ip_agent` | Patents, copyright, IP ownership |
| `LIABILITY_CAP` | — | Damages caps, liability limitations |
| `FX_HEDGING` | `finance_agent` | Currency hedging, forex covenants |
| `EMPLOYMENT_TERM` | `hr_agent` | Employee agreements, severance |
| `CHANGE_OF_CONTROL` | `governance_agent` | CoC triggers, governance changes |
| `INDEMNIFICATION` | `litigation_agent` | Indemnity obligations, carve-outs |
| `DATA_PROTECTION` | `privacy_agent` | GDPR, privacy covenants |
| `INSURANCE_POLICY` | `insurance_agent` | Coverage terms, policy requirements |
| `GOVERNANCE_CLAUSE` | `governance_agent` | Board governance, voting rights |
| `RELATED_PARTY_TRANSACTION` | `related_party_agent` | Related-party deals, conflicts |
| `CYBER_SECURITY` | `cyber_agent` | Security obligations, breach response |
| `SUPPLIER_CONTRACT` | `supplier_agent` | Supply chain, vendor terms |
| `CUSTOMER_CONTRACT` | `customer_agent` | Customer agreements, SLAs |
| `REPUTATION_RISK` | `reputation_agent` | Reputational risk clauses |
| `ESG_OBLIGATION` | `esg_agent` | ESG commitments, sustainability |

---

## Getting Started

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.11+ | Core runtime |
| **Docker Desktop** | latest | Elasticsearch, Redis, PostgreSQL, Ollama |
| **Git** | latest | Version control |

### Installation

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
# or via Makefile
make install

# 4. Download spaCy model (required for GraphRAG)
python -m spacy download en_core_web_sm

# 5. Copy environment configuration
cp .env.example .env
```

### Environment Configuration

Edit `.env` with your infrastructure endpoints:

```env
# Elasticsearch (BM25 sparse search)
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=verdictos_documents

# Local LLM (Ollama / vLLM)
OLLAMA_URL=http://localhost:11434
LLM_REASONING_MODEL=llama3
LLM_DISAMBIGUATION_MODEL=qwen2.5

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

### Infrastructure Setup

#### Option A: Full Stack (Recommended)

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts all services on their default ports:

| Service | Port | Purpose |
|---------|------|---------|
| `app` | 8000 | FastAPI server |
| `worker` | — | Celery background worker |
| `elasticsearch` | 9200 | BM25 search index |
| `redis` | 6379 | Celery message broker |
| `postgres` | 5432 | Primary database |
| `ollama` | 11434 | Local LLM server |

#### Option B: Individual Services

```bash
# Elasticsearch only (Phase 1 live indexing)
docker compose -f docker/docker-compose.yml up elasticsearch -d

# Full infrastructure minus app containers
docker compose -f docker/docker-compose.yml up elasticsearch redis postgres ollama -d
```

### Database Initialization

```bash
# Initialize schema
python scripts/setup_database.py

# Apply migrations
alembic upgrade head
# or
make migrate
```

### Pull Ollama Models

```bash
# Automatic: waits for Ollama readiness, then pulls
python scripts/pull_models.py

# Manual
ollama pull llama3:8b
ollama pull qwen2.5:7b
```

---

## Running the System

### Phase 1: Pre-Flight Pipeline

Phase 1 is the synchronous boundary that parses documents, classifies clauses, builds the knowledge graph, indexes chunks, and emits the specialist manifest.

```bash
# Dry run (no Docker needed; gracefully skips live ES indexing)
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf

# Live Elasticsearch indexing (ES auto-polled for 60 seconds)
docker compose -f docker/docker-compose.yml up elasticsearch -d
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf

# Multiple documents
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf testing_pdfs/Amendment.pdf
```

**Sample Output:**
```
[ES] Connected to http://localhost:9200 (attempt 1) — live indexing enabled.

Running Phase 1 pre-flight on 1 document(s)...

======================================================================
PHASE 1 PRE-FLIGHT REPORT
======================================================================

Documents parsed: 1
  - Merger_Agreement.pdf (123 pages)

Chunks produced:  390

Clause-type distribution:
  general                ######################################## 253
  change_of_control      ############################ 81
  employment_term        ################### 25
  tax_provision          ############ 13
  ip_assignment          ############ 10
  ...

GraphRAG graph:
  Entity nodes      : 801  (5 confirmed, 796 unconfirmed)
  Section nodes     : 215
  Edges             : 21744

Indexing outcome:
  Attempted : 390
  Indexed   : 390

Planner manifest (targeted specialists):
  [+] ip_agent                   intellectual property, patent, copyright...
  [+] litigation_agent           litigation, lawsuit, arbitration...
  [+] finance_agent              financial covenants, FX hedging...
======================================================================
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
| `GET` | `/health` | Health check |

### Celery Worker

```bash
# Via Makefile
make worker

# Direct
celery -A src.workers.celery_app worker --loglevel=info
```

---

## Testing

All 66+ unit and integration tests run **offline** — no Docker, no Ollama required.

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

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
| End-to-End | `tests/integration/test_pipeline/` | Full preflight pipeline with real documents |

---

## Code Quality

```bash
# Lint and type-check
make lint

# Ruff linter only
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

| Table | Purpose |
|-------|---------|
| `Deal` | M&A transaction record, file manifest, state tracking |
| `Finding` | Agent-discovered finding — claim, citation, confidence, severity |
| `DebateArg` | Individual debate argument (append-only) — persona, stance, steelman |
| `AuditRecord` | Immutable audit log (append-only) — event type, actor, timestamp, payload |
| `Escalation` | Issue escalated for human review — status, decision, resolver |
| `Dispute` | End-user dispute against a finding |
| `DeltaRun` | Delta analysis execution for incremental index updates |

**Append-Only Enforcement:** `DebateArg` and `AuditRecord` tables block UPDATE and DELETE at the ORM level — audit trails are immutable.

### Deal State Machine

```
created → indexing → analyzing → debating → judging → complete
                                                         ↓
                              error ←──────────────────── (any state)
                              error → recovery / indexing (recovery)
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **BM25 over Embeddings** | Embeddings compress hyper-specific clauses near generic text, causing drift on debt covenants and exact clause matching. BM25 ensures exact keyword retrieval. |
| **Local Open-Source LLMs** | Legal documents are confidential; cloud egress violates data security and client trust. 100% local inference on Ollama / vLLM. |
| **Pre-Flight GraphRAG** | Cross-references broken by chunking must be resolved upfront before agents analyze findings. GraphRAG built before debate engine runs. |
| **Append-Only Audit Logs** | Regulatory and legal auditors require immutable AI reasoning trails. Human judgment is additive, never destructive. |
| **3-Round Hard Cap** | Guarantees system termination. Findings unresolved in 3 rounds route to explicit gap reports rather than speculative consensus. |
| **Pydantic V2 Contracts** | Open-source LLMs produce malformed JSON. Pydantic retry loops with exact error messages enable self-healing without human intervention. |
| **Asyncio Semaphore (40)** | Debate parallelism bounded to prevent resource exhaustion. Token budgets for local models optimized at this concurrency level. |

---

## Performance Characteristics

- **Phase 1 Parsing:** ~20–50 pages/second (PDF parsing is I/O bound; use thread pools)
- **Chunk Count:** 300–500 chunks per 100-page document (200–500 token windows, no overlap)
- **Entity Resolution:** 800–1200 entities per 100-page document; Tier 1 (exact) resolves 60–70%, Tier 2 (fuzzy) adds 20–25%, Tier 3 (LLM) adds 5–10%
- **BM25 Indexing:** ~2–5 seconds per 100 chunks (Elasticsearch on commodity hardware)
- **Debate Token Budget:** ~4,000–6,000 tokens per finding (3 rounds × 6 personas × context compression)
- **Full Analysis:** 5–15 minutes end-to-end for 100-page document (Ollama on 8-core CPU)

---

## Extensibility

### Adding a New Specialist Agent

1. Create a new file in `src/agents/specialist_agents/` following the `SpecialistAgent` base class.
2. Define domain-specific prompt and vocabulary index.
3. Register in `src/agents/planner_agent.py` — add to `SPECIALIST_REGISTRY` with trigger keywords.
4. Add integration test in `tests/integration/`.

### Adding a New Clause Type

1. Add to `src/ingestion/classifier.py` — extend `CLAUSE_TYPE_RULES` dictionary.
2. Update `src/ingestion/schemas.py` — add to `ClauseType` enum.
3. Add test cases in `tests/unit/test_ingestion/test_classifier.py`.

### Custom Persona

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
- [ ] Configure Elasticsearch with persistent storage
- [ ] Run Ollama on GPU-capable hardware (NVIDIA CUDA recommended)
- [ ] Enable Redis persistence for Celery broker state
- [ ] Set up log aggregation (ELK, Datadog, etc.)
- [ ] Configure monitoring and alerting on debate round timeouts
- [ ] Enable database backups and point-in-time recovery
- [ ] Set up SSL/TLS for API and database connections

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
ollama pull qwen2.5
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

## Support

For issues, feature requests, or technical questions:
- **GitHub Issues:** [VerdictOS Issues](https://github.com/harshgupta1810/VerdictOS/issues)
- **Email:** harshgup11@gmail.com

---

**VerdictOS — Enterprise-grade determinism for high-stakes legal reasoning.**
