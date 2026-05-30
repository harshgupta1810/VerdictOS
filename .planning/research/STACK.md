# Stack Research

**Domain:** Deterministic multi-agent AI platform — legal document analysis (M&A due diligence, compliance auditing)
**Researched:** 2026-05-30
**Confidence:** HIGH — stack is fully mandated and Phase 1 is already implemented; versions are locked in `pyproject.toml` and `docker-compose.yml`

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | `asyncio.TaskGroup`, `tomllib` stdlib, performance improvements; 3.12+ gains are marginal and spaCy wheels lag |
| FastAPI | 0.110+ | HTTP API layer | Native async, automatic OpenAPI generation, direct Pydantic v2 integration — zero serialization boilerplate |
| Uvicorn | 0.28+ | ASGI server | Production-grade async HTTP; use `uvicorn[standard]` for WebSockets/HTTP2 readiness |
| Pydantic v2 | 2.6.4+ | Schema contracts across ALL agent/DB/API boundaries | Rust-backed validation 5-17× faster than v1; retry loops with exact field errors self-heal malformed LLM JSON output |
| SQLAlchemy | 2.0+ | ORM + async session management | 2.0 async API with `AsyncSession`; unified ORM/Core query style; Alembic migration integration |
| asyncpg | 0.29+ | PostgreSQL async driver | Fastest Python PostgreSQL driver; binary protocol; direct integration with SQLAlchemy async |
| PostgreSQL | 16 | Primary persistent store | JSONB columns for audit/override logs; row-level locking for append-only semantics; proven at scale |
| Redis | 7 | Celery broker + result backend | Celery's most reliable broker; sub-millisecond pub/sub; use `redis://` for single-node, `rediss://` for TLS |
| Celery | 5.3.6+ | Background task orchestration | CPU-heavy ingestion (PDF/DOCX parsing) must run off the async event loop; Celery worker pools handle this correctly |
| Elasticsearch | 8.12.x | BM25 sparse retrieval engine | Native BM25 with TF-IDF, field boosting, and clause taxonomy tag filters — exact term matching for legal clauses, not semantic approximation |
| spaCy | 3.7.4+ | NLP entity extraction feeding GraphRAG | Industrial NLP with named entity recognition; model `en_core_web_trf` for accuracy on legal text |
| NetworkX | 3.2.1+ | Knowledge graph (GraphRAG) | Pure-Python graph library; well-suited for in-memory clause cross-reference graphs; serializable to JSON/GraphML |
| pdfplumber | 0.11+ | PDF ingestion | Preserves layout coordinates and table structure — critical for clause boundary detection in legal PDFs |
| python-docx | 1.1.2+ | DOCX ingestion | Structural paragraph/section traversal; preserves heading hierarchy for section-aware chunking |
| rapidfuzz | 3.9+ | Fuzzy entity matching (tier 2 of 3-tier resolver) | C++ accelerated Levenshtein/Jaro-Winkler; significantly faster than `fuzzywuzzy`; no GPL dependency |
| Ollama | latest | Local LLM runtime (primary) | Zero-config local model serving; `http://localhost:11434`; supports Llama-3 and Qwen-2.5 out of the box |

### LLM Models

| Model | Runtime | Role | Why |
|-------|---------|------|-----|
| Llama-3 8B/70B | Ollama | Reasoning agent, debate personas, judge | Strong instruction following; JSON-mode compatible; no cloud egress |
| Qwen-2.5 7B | Ollama | Entity disambiguation (tier 3 resolver) | Multilingual capability; strong structured extraction for entity names in international M&A docs |
| Mistral 7B | Ollama | Fallback reasoning | Efficient; good for simpler specialist agent tasks |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | 0.20+ | SQLite async driver | Local development only — swap `DATABASE_URL` to SQLite fallback; never use in production |
| alembic | 1.13+ | Database schema migrations | Every schema change; auto-generates migration scripts from SQLAlchemy model diffs |
| python-multipart | 0.0.9+ | FastAPI file upload parsing | Required for `/documents/upload` route accepting PDF/DOCX via `multipart/form-data` |
| python-jose / PyJWT | latest | JWT token encoding/decoding | API authentication middleware; use HS256 with a secret rotated per environment |
| httpx | 0.27+ | Async HTTP client for Ollama API | Required for async `POST /api/generate` calls to Ollama; do NOT use `requests` on the event loop |
| lxml | 6.x | DOCX XML parsing acceleration | Already in the venv (spaCy dependency); use it in python-docx pipelines for speed |
| numpy | 2.x | Numerical operations in GraphRAG | NetworkX centrality algorithms and spaCy vector operations pull this in; accept as transitive dep |
| pytest | 9+ | Testing framework | Use with `asyncio_mode = "auto"` (already configured); test Celery tasks in eager mode |
| ruff | latest | Linting and formatting | Configured in `pyproject.toml`; replaces black + isort + flake8 as single tool |
| mypy | latest | Static type checking | Enforces `disallow_untyped_defs`; catches Pydantic model mismatches before runtime |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker Compose | Local infrastructure orchestration | Defined in `docker/docker-compose.yml`; brings up ES 8.12, Redis 7, Postgres 16 as one unit |
| Makefile | Developer workflow shortcuts | Use for `make start`, `make migrate`, `make test` targets |
| Alembic | DB migration management | `alembic upgrade head` must run before first API start; managed via `src/db/migrations/env.py` |
| Ollama CLI | Local model management | `ollama pull llama3` and `ollama pull qwen2.5` required before running the stack |

---

## Installation

```bash
# Core application
pip install "fastapi>=0.110.0" "uvicorn[standard]>=0.28.0" "pydantic>=2.6.4"

# Database
pip install "SQLAlchemy>=2.0.28" "asyncpg>=0.29.0" "aiosqlite>=0.20.0" alembic

# Queue
pip install "celery>=5.3.6" "redis>=5.0.3"

# Search
pip install "elasticsearch>=8.12.0,<9.0.0"

# NLP / GraphRAG
pip install "spacy>=3.7.4" "networkx>=3.2.1"
python -m spacy download en_core_web_trf

# Document parsing
pip install "pdfplumber>=0.11.0" "python-docx>=1.1.2"

# Fuzzy matching
pip install "rapidfuzz>=3.9.0"

# Dev dependencies
pip install pytest pytest-asyncio ruff mypy

# Pull LLM models (requires Ollama installed separately)
ollama pull llama3
ollama pull qwen2.5
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Elasticsearch BM25 | pgvector + embeddings | Never in this project — embedding compression causes semantic drift on exact legal clause matching |
| Elasticsearch BM25 | OpenSearch | Acceptable drop-in if AWS or licensing becomes a concern; API-compatible |
| Ollama | vLLM | Higher throughput on multi-GPU hardware; use vLLM when serving >10 concurrent agents on a real server |
| asyncpg | psycopg3 async | psycopg3 async mode is maturing; acceptable swap if asyncpg wheels become problematic |
| rapidfuzz | thefuzz (fuzzywuzzy) | Never — GPL-licensed and 10× slower; rapidfuzz is the canonical replacement |
| Celery + Redis | RQ (Redis Queue) | RQ if the task model stays simple; Celery's routing, rate limiting, and canvas needed here |
| NetworkX | igraph (python-igraph) | igraph is faster for large graphs (>100K nodes); NetworkX suffices for per-deal clause graphs |
| pdfplumber | PyMuPDF (fitz) | PyMuPDF is faster and handles scanned PDFs better; switch if OCR becomes a requirement |
| spaCy | NLTK | Never — NLTK is 15 years older, no transformer support; spaCy is the current standard |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| OpenAI / Anthropic / Gemini APIs | Legal documents are confidential; cloud egress violates client trust and data security contracts | Ollama (Llama-3, Qwen-2.5) on localhost |
| LangChain / LlamaIndex | Both frameworks default to RAG patterns built on vector stores; they actively resist vectorless BM25-only architectures and add hidden abstraction layers that make prompt injection defense harder | Direct Elasticsearch client + custom agent orchestration (already implemented) |
| Vector databases (Pinecone, Weaviate, Chroma, Qdrant) | Cosine similarity search compresses hyper-specific legal constraints (debt covenants, exact clause numbers) near semantically similar but legally distinct clauses — a known failure mode this architecture explicitly rejects | Elasticsearch BM25 with clause taxonomy field filters |
| `requests` library on the event loop | Blocking I/O stalls the entire async event loop — breaks the Asyncio Semaphore concurrency model | `httpx.AsyncClient` for all LLM and HTTP calls |
| Threading for LLM calls | Opens race conditions against the Semaphore cap of 40; asyncio is the correct concurrency primitive | `asyncio.Semaphore(40)` around debate loop coroutines |
| Raw `dict` passing between agents | Bypasses Pydantic validation; open-source LLMs produce malformed JSON that will corrupt downstream agents silently | Pydantic v2 models at every agent boundary |
| SQLite in production | No row-level locking, no JSONB, no concurrent writes at scale | PostgreSQL 16 via asyncpg |
| Pydantic v1 | 5-17× slower validation; deprecated; incompatible with FastAPI 0.110+ default behavior | Pydantic v2 with `model_config = ConfigDict(...)` |

---

## Stack Patterns by Variant

**If running on a machine with no GPU:**
- Use Ollama with 4-bit quantized models (`llama3:8b-instruct-q4_K_M`)
- Expect ~5-10 tokens/sec on CPU — adequate for batch document processing, not real-time

**If running on multi-GPU hardware (production server):**
- Replace Ollama with vLLM (`http://localhost:8000/v1`) for higher throughput
- vLLM supports tensor parallelism across GPUs; change `OLLAMA_URL` env var only

**If document volume grows to >10K documents per deal:**
- Shard Elasticsearch by deal ID rather than using a single index
- Increase `asyncio.Semaphore` cap from 40 only after profiling LLM memory pressure

**If OCR support for scanned PDFs is needed (post-MVP):**
- Add PyMuPDF (`fitz`) alongside pdfplumber as a pre-processing step
- OCR models: Tesseract via `pytesseract` or `easyocr` — both local, no cloud egress

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `elasticsearch>=8.12.0,<9.0.0` | ES server 8.12.0 (pinned in docker-compose) | `<9.0.0` upper bound is critical — ES 9.x has breaking client API changes |
| `SQLAlchemy>=2.0.28` | `asyncpg>=0.29.0` | SQLAlchemy 2.0+ async requires asyncpg for PostgreSQL; legacy 1.x API unavailable |
| `pydantic>=2.6.4` | `fastapi>=0.110.0` | FastAPI 0.110 dropped Pydantic v1 support entirely; v2 required |
| `celery>=5.3.6` | `redis>=5.0.3` | Celery 5.x requires redis-py 4+ as broker backend |
| `spacy>=3.7.4` | `numpy>=1.15,<2.1` (spaCy's stated bound) | spaCy 3.7 may emit warnings with numpy 2.x; test `en_core_web_trf` model before upgrading numpy |

---

## Sources

- `pyproject.toml` — authoritative version pins (HIGH confidence)
- `docker/docker-compose.yml` — infrastructure image versions (HIGH confidence)
- `.env.example` — runtime configuration endpoints (HIGH confidence)
- `src/config.py` — model defaults: Llama-3 for reasoning, Qwen-2.5 for disambiguation (HIGH confidence)
- Phase 1 codebase structure — confirms module boundaries: `src/ingestion`, `src/graphrag`, `src/debate`, `src/search`, `src/workers` (HIGH confidence)

---

*Stack research for: VerdictOS — deterministic multi-agent legal document analysis platform*
*Researched: 2026-05-30*
