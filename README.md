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
| Clause classifier | Rule-based taxonomy | 8 clause types + `general` fallback |
| Entity resolution | String → RapidFuzz → LLM | 3-tier, unconfirmed nodes never silently merged |
| Knowledge graph | spaCy NER + NetworkX | Pre-flight DiGraph, built before any agent runs |
| Planner agent | Term + clause-type routing | Activates only needed specialists (saves 30–60% tokens) |
| Debate engine | 6 personas, 8 tracks | Adversarial multi-round finding verification |
| LLM stack | Ollama (Llama-3, Qwen-2.5) | 100% local open-source, no external API calls |
| Schema layer | Pydantic V2 | Strict contracts at every agent-to-agent boundary |

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | |
| Docker Desktop | latest | For Elasticsearch, Redis, PostgreSQL |
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

# 4. Download the spaCy model (required for GraphRAG entity extraction)
python -m spacy download en_core_web_sm

# 5. Copy environment config
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

---

## Running Phase 1 — Pre-Flight Pipeline

Phase 1 is the synchronous pre-flight boundary. It parses documents, classifies clauses, builds the knowledge graph, indexes chunks into Elasticsearch, and emits the specialist manifest consumed by Phase 2.

### Option A — Dry run (no Docker needed)

If Elasticsearch is not running the script falls back to a dry-run mode automatically. All steps execute except the live ES write.

```bash
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
```

### Option B — Live Elasticsearch indexing

```bash
# Start Elasticsearch (first run pulls ~660 MB image)
docker compose -f docker/docker-compose.yml up elasticsearch -d

# Wait ~30 seconds for ES to initialize, then run
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
```

The script polls ES for up to 60 seconds automatically — you do not need to wait manually.

### Run against multiple documents

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

### Improving entity resolution with Ollama (optional)

With Ollama offline, ambiguous entity names stay as `unconfirmed_node`. To enable Tier 3 LLM resolution:

```bash
# Install Ollama from https://ollama.com and then pull the model
ollama pull qwen2.5

# The pipeline will pick it up automatically via OLLAMA_URL in .env
python scripts/run_pipeline.py testing_pdfs/Merger_Agreement.pdf
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

---

## Running the Test Suite

```bash
# All tests
pytest tests/

# Unit tests only (no Docker required)
pytest tests/unit/

# Phase 1 unit + integration tests specifically
pytest tests/unit/test_ingestion/ tests/unit/test_graphrag/ tests/unit/test_agents/test_planner_agent.py tests/integration/test_pipeline/ -v

# Via Makefile
make test-unit
make test-integration
make test
```

### What the Phase 1 tests cover

| Test file | Component |
|-----------|-----------|
| `tests/unit/test_ingestion/test_chunker.py` | Section tracking, cross-references, 200–500 token bounds |
| `tests/unit/test_ingestion/test_classifier.py` | All 8 clause types, conservative tie-breaking, chunk enrichment |
| `tests/unit/test_ingestion/test_ingest.py` | PDF column ordering, DOCX headings/tables/page breaks |
| `tests/unit/test_graphrag/test_entity_resolver.py` | Tier 1 exact, Tier 2 fuzzy (0.85 boundary), Tier 3 LLM accept/reject |
| `tests/unit/test_graphrag/test_graph_constructor.py` | spaCy label mapping, edge types, alias merging, JSON/GraphML round-trip |
| `tests/unit/test_agents/test_planner_agent.py` | 16-specialist registry, synonym expansion, routing, fallback |
| `tests/integration/test_pipeline/test_end_to_end.py` | Full PreflightPipeline — step order, error guards, real DOCX end-to-end |

All 66 unit and integration tests run offline (no Docker, no Ollama required).

---

## Project Structure

```
src/
  ingestion/          # Document parser, section-aware chunker, clause classifier
  graphrag/           # Entity resolver, GraphRAG constructor
  search/             # Elasticsearch indexer, BM25 search engine
  agents/             # Planner agent, base agent, judge agent
  debate/             # Orchestrator, personas, gates, consensus mapper
  workers/            # Celery task workers
  api/                # FastAPI gateway, routes, middleware
  db/                 # SQLAlchemy models, migrations, repositories
  llm/                # Ollama LLM client
  common/             # Shared models, exceptions, utils
  preflight.py        # Phase 1 pre-flight pipeline composition
  config.py           # Environment-backed settings (Pydantic)

scripts/
  run_pipeline.py         # CLI runner for Phase 1
  setup_elasticsearch.py  # Index bootstrap utility
  seed_data.py            # Development seed data

tests/
  unit/               # Per-component unit tests (no infrastructure)
  integration/        # Pipeline and API integration tests

docker/
  docker-compose.yml  # Elasticsearch, Redis, PostgreSQL
  Dockerfile          # API server image
  Dockerfile.worker   # Celery worker image

memory/
  system_overview.md  # Full architecture specification
  guidelines.md       # Coding and prompt engineering standards
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
| `DATABASE_URL` | `sqlite+aiosqlite:///./verdictos.db` | Async DB (swap for PostgreSQL in production) |
| `JWT_SECRET` | *(change in production)* | API gateway signing key |

---

## Start Full Infrastructure

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts Elasticsearch (port 9200), Redis (port 6379), and PostgreSQL (port 5432).
