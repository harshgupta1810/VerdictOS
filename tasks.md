# VerdictOS Detailed Implementation Tasks

This task list tracks the execution progress of VerdictOS development, broken down into component-level micro-tasks and subtasks.

## Phase 1: Centralized Memory System Setup (100% Complete)
- [x] Initialize memory directory in project root
  - [x] Create [system_overview.md](file:///d:/projects/VerdictOS/memory/system_overview.md) detailing high-level requirements and data boundaries
  - [x] Create [component_specifications.md](file:///d:/projects/VerdictOS/memory/component_specifications.md) specifying component parameters and schema layouts
  - [x] Create [decisions.md](file:///d:/projects/VerdictOS/memory/decisions.md) detailing architecture decisions (vectorless, Pydantic middleware, append-only, Steelman rule)
  - [x] Create [guidelines.md](file:///d:/projects/VerdictOS/memory/guidelines.md) mapping coding guidelines, prompt engineering rules, and token management
  - [x] Create [state.md](file:///d:/projects/VerdictOS/memory/state.md) to serve as the development state dashboard
  - [x] Create [workflow.md](file:///d:/projects/VerdictOS/memory/workflow.md) mapping workspace developer workflows
- [x] Update Developer Memory Files with Open-Source, Elasticsearch, and Process Tracking Updates
  - [x] Update [system_overview.md](file:///d:/projects/VerdictOS/memory/system_overview.md)
  - [x] Update [component_specifications.md](file:///d:/projects/VerdictOS/memory/component_specifications.md)
  - [x] Update [decisions.md](file:///d:/projects/VerdictOS/memory/decisions.md)
  - [x] Update [guidelines.md](file:///d:/projects/VerdictOS/memory/guidelines.md)
  - [x] Update [state.md](file:///d:/projects/VerdictOS/memory/state.md) (with progress tracker and percentage metrics)

## Phase 2: Environment and Project Bootstrapping (100% Complete)
- [x] Create project folder layout
  - [x] `/src/ingestion`, `/src/graphrag`, `/src/search`, `/src/debate`, `/src/db`, `/src/api`
  - [x] `/tests` folder
- [x] Configure `requirements.txt`
  - [x] Include dependencies: `fastapi`, `uvicorn`, `pydantic>=2.0`, `pdfplumber`, `python-docx`, `spacy`, `networkx`, `elasticsearch`, `sqlalchemy`, `asyncio`, `redis`, `celery`, `pytest`, `httpx`, `httpx-sse`
- [x] Initialize local environment configuration (`.env.example` and config parsing modules)

## Phase 3: Document Ingestion, Parsing & Chunking (100% Complete)
- [x] Implement Document Ingest & Parser (`src/ingestion/ingest.py`)
  - [x] Set up `pdfplumber` exception-safe document extraction
  - [x] Implement layout coordinate parser tracking page boundaries
  - [x] Implement sorting engine to resolve multi-column alignment sequences
  - [x] Set up `python-docx` paragraph and table ingestion
  - [x] Implement style/font triggers to isolate section header boundaries
- [x] Implement Chunker (`src/ingestion/chunker.py`)
  - [x] Build semantic clause splitter (split on periods, semicolons, and carriage returns)
  - [x] Build non-overlapping token chunk assembler limiting sizing between 200 and 500 tokens
  - [x] Enrich chunks with metadata context (`section_id`, `absolute_page`)
  - [x] Write regex parser to extract cross-referenced sections (`references_sections`)
- [x] Implement Classifier (`src/ingestion/classifier.py`)
  - [x] Define keyword mapping dictionaries for the canonical `ClauseType` taxonomy
  - [x] Write classifier lookup routing logic with fallback `'general'` tag for uncertain or sparse matches

## Phase 4: Entity Resolution & GraphRAG Constructor (100% Complete)
- [x] Implement 3-Tier Entity Resolution (`src/graphrag/entity_resolver.py`)
  - [x] Tier 1: Case-insensitive exact string match and punctuation trim
  - [x] Tier 2: Fuzzy distance match checks utilizing Levenshtein distance rules (ratio > 0.85)
  - [x] Tier 3: Local open-source model prompt (Ollama) resolving ambiguous nodes
  - [x] Implement resolution cache registry mapping duplicates to reduce LLM overhead
  - [x] Tag unresolved links as `unconfirmed_node` to maintain database separation
- [x] Implement Knowledge Graph Constructor (`src/graphrag/graph_constructor.py`)
  - [x] Set up spaCy Named Entity Recognition (NER) pipeline mapping Organizations, Persons, Locations, Assets, and Codes
  - [x] Build NetworkX DiGraph mapper tracking cross-document entity relationships
  - [x] Write serialization/deserialization utilities to load/store graph states on disk

## Phase 5: Vectorless Sparse Retrieval Index (Elasticsearch) (100% Complete)
- [x] Setup Search Engine (`src/search/search_engine.py`)
  - [x] Set up Elasticsearch connection client mapping to local port 9200
  - [x] Define Elasticsearch index mapping schema (`text`, `section_id`, `absolute_page`, `clause_type`, `references_sections`)
  - [x] Write Elasticsearch bulk indexer loading parsed chunks in batches
- [x] Implement BM25 Search Queries (`src/search/search_engine.py`)
  - [x] Build BM25 sparse matching queries filtering by document name or clause type
  - [x] Implement exact metadata filters and highlight extraction
- [x] Implement Incremental Updates (`src/search/search_engine.py`)
  - [x] Write deterministic upserts to index new document additions without rebuilding index

## Runtime Phase 2 Contract Preparation (Pulled Forward)
- [x] Define the approved 16-specialist `agent_name` registry
- [x] Define per-agent query-time synonym dictionaries
- [x] Build deterministic planner routing and all-agent fallback
- [x] Compose synchronous pre-flight execution (`src/preflight.py`)

## Phase 6: Multi-Agent Orchestration & Debate Engine (DebateOS)
- [ ] Implement Pydantic V2 schemas (`src/debate/schemas.py`)
  - [ ] Define `Finding` Pydantic model (fields: `id`, `claim`, `citation`, `confidence`)
  - [ ] Define `Stance` Pydantic model (fields: `persona`, `stance_type`, `confidence`, `arguments`)
  - [ ] Define `DebateTranscript` schema for round logging
  - [ ] Define `ContextCompression` JSON compression mapping schema
  - [ ] Define `SteelmanValidation` schema validating non-empty `steelman` text field
- [ ] Implement Personas (`src/debate/personas.py`)
  - [ ] Set up system prompt instructions for the 6 personas optimized for open-source LLM instruction following
  - [ ] Build Ollama JSON api client formatting requests
  - [ ] Write schema auto-retry middleware capturing Pydantic tracebacks on failures
- [ ] Implement Asyncio Orchestrator Loop (`src/debate/orchestrator.py`)
  - [ ] Configure `asyncio.Semaphore` throttling concurrent API connections (max 40)
  - [ ] Implement hard round cap terminating execution at Round 3
  - [ ] Build dimension gating checker (checks if dimensions have >= 3 findings to start debate)
  - [ ] Implement consensus-based early exit (stance score consensus >= 4 personas)
  - [ ] Implement the 5 sequential reliability gates:
    - [ ] Gate A: JSON Schema Verification
    - [ ] Gate B: Citation Exact Match Validation (checks quotes via Elasticsearch index search)
    - [ ] Gate C: Timeline Self-Contradiction Flags
    - [ ] Gate D: Stance Alignment validation
    - [ ] Gate E: Synthesis & Judge Mapping

## Phase 7: FastAPI REST Gateway and DB Persistence
- [ ] Setup DB Layer (`src/db/`)
  - [ ] Define SQLAlchemy database schemas in `src/db/models.py` (deals, findings, transcripts, escalations, disputes)
  - [ ] Set up DB constraints revoking UPDATE/DELETE permissions on `debate_transcripts`
  - [ ] Configure GIN indexes on JSONB database columns
  - [ ] Write database session loaders supporting async PostgreSQL and SQLite fallback
- [ ] Setup API Router Matrix (`src/api/main.py`)
  - [ ] Add `POST /api/v1/deals` job ingest router
  - [ ] Set up WebSocket/SSE real-time status update stream
  - [ ] Add `GET /api/v1/deals/{id}/verdict` compiled output route
  - [ ] Add `GET /api/v1/deals/{id}/audit` transcript route
  - [ ] Add `POST /api/v1/deals/{id}/escalations/{eid}/resolve` resolver route
  - [ ] Add `POST /api/v1/deals/{id}/findings/{fid}/dispute` dispute route
  - [ ] Setup OAuth 2.0 authentication filters (no RBAC checking for this phase)

## Phase 8: Verification & Cleanup
- [ ] Write test configurations under `/tests`
  - [x] Create parser and chunker unit tests (`tests/unit/test_ingestion/`)
  - [x] Create entity resolution and graph constructor test suites (`tests/unit/test_graphrag/`)
  - [x] Create Elasticsearch search engine test suite (`tests/unit/test_search/`)
  - [ ] Create mock API tests for the debate engine loop (`tests/test_debate.py`)
  - [ ] Create integration tests targeting API endpoints (`tests/test_api.py`)
- [ ] Validate database integrity constraints by attempting forbidden updates/deletes
- [x] Clean up temporary debug scripts or scrap files before marking complete
