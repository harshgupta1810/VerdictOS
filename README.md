# VerdictOS

Multi-agent system for transaction validation, corporate compliance tracking, and M&A due diligence.

VerdictOS replaces probabilistic vector-similarity retrieval with a **deterministic, vectorless architecture**: Elasticsearch BM25 sparse retrieval, pre-flight structural GraphRAG, and a 6-persona adversarial debate engine — no embeddings, no hallucinated citations.

---

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Sparse retrieval | Elasticsearch 8 BM25 | Exact keyword search, no vector DB |
| Document parsing | pdfplumber, python-docx | PDF/DOCX with layout coordinates |
| Section chunker | Custom (200–500 tokens) | Section-aware, non-overlapping chunks |
| Clause classifier | Rule-based taxonomy | 16 clause types + `general` fallback |
| Entity resolution | String → RapidFuzz → LLM | 3-tier, unconfirmed nodes never silently merged |
| Knowledge graph | spaCy NER + NetworkX | Pre-flight DiGraph, built before any agent runs |
| Planner agent | Term + clause-type routing | Activates only needed specialists (saves 30–60% tokens) |
| Debate engine | 6 personas, 8 tracks | Adversarial multi-round finding verification |
| LLM stack | Ollama (Llama-3, Qwen-2.5) | 100% local open-source, no external API calls |
| Schema layer | Pydantic V2 | Strict contracts at every agent-to-agent boundary |
| Database | PostgreSQL / SQLite | Async SQLAlchemy, append-only audit logs |
| Task broker | Redis + Celery | Asynchronous specialist task distribution |
| API gateway | FastAPI + uvicorn | JWT auth, structured REST routes |

---

## Clause Types

The system classifies document chunks into 16 clause types:

`TAX_PROVISION` · `IP_ASSIGNMENT` · `LIABILITY_CAP` · `FX_HEDGING` · `EMPLOYMENT_TERM` · `CHANGE_OF_CONTROL` · `INDEMNIFICATION` · `DATA_PROTECTION` · `INSURANCE_POLICY` · `GOVERNANCE_CLAUSE` · `RELATED_PARTY_TRANSACTION` · `CYBER_SECURITY` · `SUPPLIER_CONTRACT` · `CUSTOMER_CONTRACT` · `REPUTATION_RISK` · `ESG_OBLIGATION` · `GENERAL`

---

## Specialist Agents (16)

The planner activates only the agents relevant to each document's clause profile:

| Agent | Domain |
|-------|--------|
| `ip_agent` | Intellectual property, patents, copyright |
| `litigation_agent` | Litigation, lawsuits, arbitration |
| `regulatory_agent` | Regulatory compliance, licenses |
| `privacy_agent` | Data protection, GDPR, privacy |
| `finance_agent` | Financial covenants, FX hedging |
| `tax_agent` | Tax provisions, indemnities |
| `insurance_agent` | Insurance policies, coverage |
| `hr_agent` | Employment terms, HR obligations |
| `governance_agent` | Board governance, voting rights |
| `related_party_agent` | Related-party transactions |
| `cyber_agent` | Cybersecurity obligations |
| `assets_agent` | Asset transfers, ownership |
| `supplier_agent` | Supplier contracts, supply chain |
| `customer_agent` | Customer contracts, SLAs |
| `reputation_agent` | Reputational risk clauses |
| `esg_agent` | ESG obligations, sustainability |

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | |
| Docker Desktop | latest | For Elasticsearch, Redis, PostgreSQL, Ollama |
| Ollama | latest | Optional for Phase 1 — required for Tier 3 entity resolution and debate |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/harshgupta1810/VerdictOS.git
cd VerdictOS

# 2. Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
# or via Makefile
make install

# 4. Download the spaCy model (required for GraphRAG entity extraction)
python -m spacy download en_core_web_sm

# 5. Copy environment config
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch endpoint |
| `ELASTICSEARCH_INDEX` | `verdictos_documents` | BM25 chunk index name |
| `OLLAMA_URL` | `http://localhost:11434` | Local LLM server |
| `LLM_REASONING_MODEL` | `llama3` | Model for debate engine |
| `LLM_DISAMBIGUATION_MODEL` | `qwen2.5` | Model for Tier 3 entity resolution |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `DATABASE_URL` | `sqlite+aiosqlite:///./verdictos.db` | Async DB — swap for PostgreSQL in production |
| `JWT_SECRET` | *(change in production)* | API gateway signing key |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token expiry (24 hours) |

---

## Infrastructure

### Start Full Stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts all services:

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | FastAPI server |
| `worker` | — | Celery background worker |
| `elasticsearch` | 9200 | BM25 sparse search |
| `redis` | 6379 | Celery broker + cache |
| `postgres` | 5432 | Primary database (production) |
| `ollama` | 11434 | Local LLM server |

### Start Individual Services

```bash
# Elasticsearch only (for Phase 1 live indexing)
docker compose -f docker/docker-compose.yml up elasticsearch -d

# Full infrastructure minus the app containers
docker compose -f docker/docker-compose.yml up elasticsearch redis postgres ollama -d
```

---

## Database Setup

```bash
# Initialize the database schema
python scripts/setup_database.py

# Apply Alembic migrations
alembic upgrade head
# or via Makefile
make migrate
```

The default database is SQLite (`verdictos.db`) in the project root. To use PostgreSQL, set `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/verdictos
```

---

## Pulling Ollama Models

```bash
# Pull models using the helper script (waits for Ollama readiness automatically)
python scripts/pull_models.py

# Or pull manually
ollama pull llama3.2:1b
ollama pull qwen2.5:0.5b
```

---

## Running Phase 1 — Pre-Flight Pipeline

Phase 1 is the synchronous pre-flight boundary. It parses documents, classifies clauses, builds the knowledge graph, indexes chunks into Elasticsearch, and emits the specialist manifest consumed by Phase 2.

### Option A — Dry run (no Docker needed)

If Elasticsearch is not running the script falls back to dry-run mode automatically. All steps execute except the live ES write.

```bash
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
```

### Option B — Live Elasticsearch indexing

```bash
# Start Elasticsearch (first run pulls ~660 MB image)
docker compose -f docker/docker-compose.yml up elasticsearch -d

# The script polls ES for up to 60 seconds — no manual wait needed
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
```

### Multiple documents

```bash
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf testing_pdfs/StuPapWFMerAgree.pdf
```

### Sample output

```
[ES] Connected to http://localhost:9200 (attempt 1) — live indexing enabled.

Running Phase 1 pre-flight on 1 document(s)...

======================================================================
PHASE 1 PRE-FLIGHT REPORT
======================================================================

Documents parsed: 1
  - Merger_Agreement.pdf  (123 pages)

Chunks produced:  390

Clause-type distribution:
  general                ######################################## 253
  change_of_control      ######################################## 81
  employment_term        ######################### 25
  tax_provision          ############# 13
  ip_assignment          ########## 10
  ...

GraphRAG graph:
  Entity nodes      : 801  (5 confirmed, 796 unconfirmed)
  Section nodes     : 215
  Edges             : 21744

Indexing outcome:
  Attempted : 390
  Indexed   : 390

Planner manifest  (targeted):
  [+] ip_agent                   intellectual property, patent, copyright...
  [+] litigation_agent           litigation, lawsuit, claim, arbitration...
  ...
======================================================================
```

### Bootstrap the Elasticsearch index manually

```bash
python scripts/setup_elasticsearch.py           # create index (skip if exists)
python scripts/setup_elasticsearch.py --force   # drop and recreate
```

Verify the index and chunk count:

```
GET http://localhost:9200/verdictos_documents/_count
```

### Improving entity resolution with Ollama (optional)

With Ollama offline, ambiguous entity names stay as `unconfirmed_node`. To enable Tier 3 LLM resolution:

```bash
# Install Ollama from https://ollama.com and pull the disambiguation model
ollama pull qwen2.5

# The pipeline picks it up automatically via OLLAMA_URL in .env
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
```

---

## Running the API Server

```bash
# Via Makefile (recommended — enables hot reload)
make run

# Or directly
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/deals` | Submit a deal with document manifest |
| `GET` | `/api/v1/deals/{id}/status` | Stream progress (WebSocket / SSE) |
| `GET` | `/api/v1/deals/{id}/verdict` | Compiled structured verdict |
| `GET` | `/api/v1/deals/{id}/audit` | Immutable debate transcripts |

---

## Running the Celery Worker

The Celery worker handles asynchronous specialist agent tasks. Requires Redis.

```bash
# Via Makefile
make worker

# Or directly
celery -A src.workers.celery_app worker --loglevel=info
```

---

## Running the Test Suite

All 66 unit and integration tests run **offline** — no Docker, no Ollama required.

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With verbose output
pytest tests/ -v

# Via Makefile
make test
make test-unit
make test-integration
```

### Targeted test runs

```bash
# Ingestion pipeline
pytest tests/unit/test_ingestion/ -v

# GraphRAG
pytest tests/unit/test_graphrag/ -v

# Agents
pytest tests/unit/test_agents/ -v

# Search
pytest tests/unit/test_search/ -v

# Database models
pytest tests/unit/test_db/ -v

# Phase 1 focused (unit + integration)
pytest tests/unit/test_ingestion/ tests/unit/test_graphrag/ tests/unit/test_agents/test_planner_agent.py tests/integration/test_pipeline/ -v
```

### Test coverage by component

| Test file | Component |
|-----------|-----------|
| `tests/unit/test_ingestion/test_chunker.py` | Section tracking, cross-references, 200–500 token bounds |
| `tests/unit/test_ingestion/test_classifier.py` | All 16 clause types, conservative tie-breaking, chunk enrichment |
| `tests/unit/test_ingestion/test_ingest.py` | PDF column ordering, DOCX headings/tables/page breaks |
| `tests/unit/test_graphrag/test_entity_resolver.py` | Tier 1 exact, Tier 2 fuzzy (0.85 boundary), Tier 3 LLM accept/reject |
| `tests/unit/test_graphrag/test_graph_constructor.py` | spaCy label mapping, edge types, alias merging, JSON/GraphML round-trip |
| `tests/unit/test_agents/test_planner_agent.py` | 16-specialist registry, synonym expansion, routing, fallback |
| `tests/unit/test_agents/test_dispatcher.py` | Task routing, parallel execution |
| `tests/unit/test_agents/test_specialist_agent.py` | Domain-specific discovery, isolated prompts |
| `tests/unit/test_agents/test_schemas.py` | Agent contract validation |
| `tests/unit/test_search/test_search_engine.py` | BM25 search, clause-type filtering, section reference resolution |
| `tests/unit/test_db/test_models.py` | ORM models, state machine transitions, append-only enforcement |
| `tests/unit/test_llm/test_client.py` | LLM client, retry logic |
| `tests/unit/test_common/test_models.py` | Shared models and utilities |
| `tests/integration/test_pipeline/test_end_to_end.py` | Full PreflightPipeline — step order, error guards, real DOCX end-to-end |

---

## Code Quality

```bash
# Lint and type check
make lint

# Ruff only
ruff check src/ tests/

# Mypy only
mypy src/

# Pyright type checking (configured in pyrightconfig.json)
pyright
```

---

## Makefile Reference

```bash
make help              # Show all available targets
make install           # Install Python dependencies
make lint              # Run ruff + mypy
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make run               # Start API server with hot reload (port 8000)
make worker            # Start Celery worker
make migrate           # Apply Alembic database migrations
```

---

## Project Structure

```
VerdictOS/
├── src/
│   ├── api/                # FastAPI gateway
│   │   ├── main.py         # Application factory
│   │   ├── dependencies.py # Dependency injection
│   │   ├── middleware/
│   │   │   └── auth.py     # JWT authentication
│   │   └── routes/
│   │       ├── deals.py    # Deal submission & verdict endpoints
│   │       ├── escalations.py
│   │       └── health.py
│   ├── agents/             # Agent system
│   │   ├── planner_agent.py    # Smart dispatch (16 specialists)
│   │   ├── specialist_agent.py # Domain discovery agents
│   │   ├── judge_agent.py      # Verdict synthesis
│   │   ├── dispatcher.py       # Task routing
│   │   ├── base_agent.py       # Agent interface
│   │   └── schemas.py          # Agent contracts
│   ├── debate/             # Adversarial debate engine
│   │   ├── orchestrator.py # 6-persona, 8-track coordination
│   │   ├── personas.py     # Persona definitions
│   │   ├── gates.py        # Validation gates
│   │   └── consensus.py    # Consensus mapper
│   ├── graphrag/           # Knowledge graph
│   │   ├── entity_resolver.py  # 3-tier entity resolution
│   │   └── graph_constructor.py # NetworkX DiGraph builder
│   ├── ingestion/          # Document parsing
│   │   ├── ingest.py       # PDF/DOCX parser
│   │   ├── chunker.py      # Section-aware chunker (200–500 tokens)
│   │   ├── classifier.py   # Rule-based clause classifier
│   │   ├── defined_terms.py # Defined terms extractor
│   │   └── schemas.py
│   ├── search/             # Vectorless retrieval
│   │   ├── search_engine.py # BM25 sparse search
│   │   └── indexer.py      # Chunk indexer
│   ├── db/                 # Database layer
│   │   ├── models.py       # SQLAlchemy ORM (7 tables)
│   │   ├── session.py      # Async session factory
│   │   └── repositories.py # Data access patterns
│   ├── llm/                # Local LLM client (Ollama)
│   ├── workers/            # Celery task workers
│   ├── common/             # Shared models, exceptions, utils
│   ├── preflight.py        # Phase 1 pipeline composition
│   └── config.py           # Environment-backed settings (Pydantic)
├── scripts/
│   ├── run_pipeline.py         # CLI runner for Phase 1
│   ├── setup_elasticsearch.py  # Index bootstrap utility
│   ├── setup_database.py       # Database initializer
│   ├── pull_models.py          # Ollama model downloader
│   └── seed_data.py            # Development seed data
├── tests/
│   ├── unit/               # Per-component unit tests (no infrastructure)
│   └── integration/        # Pipeline and API integration tests
├── docker/
│   ├── docker-compose.yml  # Full-stack infrastructure
│   ├── Dockerfile          # API server image
│   └── Dockerfile.worker   # Celery worker image
├── memory/
│   ├── system_overview.md  # Full architecture specification
│   └── guidelines.md       # Coding and prompt engineering standards
├── .env.example            # Environment template
├── alembic.ini             # Database migration config
├── pyproject.toml          # Project metadata and dependencies
└── Makefile                # Build and test automation
```

---

## Database Schema

Seven SQLAlchemy ORM tables:

| Table | Description |
|-------|-------------|
| `Deal` | M&A transaction record, file manifest, status |
| `Finding` | Agent-discovered finding — claim, citation, confidence, severity |
| `DebateArg` | Individual debate argument — append-only, persona, stance, steelman |
| `AuditRecord` | Immutable audit log — append-only, event type, actor, payload |
| `Escalation` | Issue escalated for human review — status, decision, resolver |
| `Dispute` | End-user dispute against a finding |
| `DeltaRun` | Delta analysis execution for incremental index updates |

`DebateArg` and `AuditRecord` are append-only — UPDATE and DELETE are blocked at the ORM level.

### Deal State Machine

```
created → indexing → analyzing → debating → judging → complete
                                                         ↓
                              error ←──────────────────── (any state)
                              error → indexing / created  (recovery)
```
