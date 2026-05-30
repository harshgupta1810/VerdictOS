# VerdictOS

## What This Is

VerdictOS is a deterministic multi-agent AI platform for high-stakes legal document analysis — specifically M&A due diligence, transaction validation, and corporate compliance auditing. It eliminates the hallucination and semantic drift failures of standard RAG pipelines by replacing vector similarity search with BM25 sparse retrieval (Elasticsearch), structural GraphRAG (spaCy + NetworkX), and adversarial multi-persona debate (DebateOS). The target user is legal and compliance teams that cannot afford speculative conclusions.

## Core Value

Every finding must be traceable to exact source text and survive adversarial challenge — no hallucinated citations, no fabricated section references.

## Requirements

### Validated

- ✓ Project scaffold with async-first FastAPI + Celery + PostgreSQL + Redis stack — Phase 1
- ✓ Pydantic v2 schema contracts for all agent boundaries (debate schemas, LLM schemas, API schemas) — Phase 1
- ✓ Debate persona definitions (6 personas, 8 strategic tracks) and orchestrator skeleton — Phase 1
- ✓ Base agent infrastructure and judge agent foundation — Phase 1
- ✓ Async LLM client targeting local Ollama/vLLM endpoint — Phase 1
- ✓ Database models, async session management, and Alembic migration setup — Phase 1

### Active

- [ ] Document ingestion pipeline: PDF (pdfplumber) and DOCX (python-docx) parsing with section-aware chunking (200–500 token windows) and clause-type taxonomy classification
- [ ] 3-tier entity resolver: string match → fuzzy match → LLM disambiguation, feeding into NetworkX GraphRAG constructor
- [ ] Elasticsearch BM25 indexing with clause taxonomy tags (no embeddings)
- [ ] 16 specialist discovery agents with isolated prompts and vocabulary indexes running against Elasticsearch
- [ ] DebateOS adversarial loop: 3-round max, Asyncio Semaphore (max 40), dimension gating (skip if < 3 findings), circuit breaker at 15% failure rate
- [ ] Consensus mapper producing structured JSON synthesis from debate transcripts
- [ ] Judge agent producing final verdict with gap reports for insufficient-evidence findings
- [ ] REST API routes: document upload, deal management, escalations, analysis job status
- [ ] Celery worker pipeline connecting ingestion → debate → consensus → verdict
- [ ] Human override layer (append-only metadata, never overwrites AI execution logs)

### Out of Scope

- Vector embeddings / cosine similarity retrieval — core architectural rejection; BM25 + GraphRAG replaces it entirely
- Cloud LLM APIs (OpenAI, Anthropic, Gemini) for reasoning — design mandates 100% open-source local LLMs to avoid data egress on confidential legal documents
- Overwriting or mutating AI execution logs — audit integrity requires append-only design
- Frontend UI — backend API platform only; UI is a separate concern
- General-purpose Q&A over arbitrary documents — scoped to structured legal document types (contracts, agreements, compliance filings)

## Context

- **Phase 1 complete:** Core scaffolding, schemas, agent skeletons, and DB layer are in place. The system is ready for substantive implementation of the ingestion pipeline and debate engine.
- **Local-only LLM stack:** Ollama (`http://localhost:11434`) with Llama-3 for reasoning and Qwen-2.5 for entity disambiguation. vLLM is an alternative host. No cloud model calls on document content.
- **Prompt injection defense:** All BM25-retrieved document text is wrapped in `<untrusted_source>` XML tags in prompts; strict JSON-only system instructions prevent conversational leakage from open-source models.
- **Context compression:** Debate history is summarized as structured JSON (not raw transcripts) before each round to keep token usage low for local models.
- **Known failure modes addressed:** Standard RAG semantic drift on debt covenants, hallucinated citation strings, and cross-reference fragmentation from sliding-window chunking are the three explicit problems this architecture solves.

## Constraints

- **Tech stack**: Python 3.11+, FastAPI, Celery, Redis, PostgreSQL (asyncpg), Elasticsearch, NetworkX, spaCy, Pydantic v2 — no deviations without explicit decision
- **LLM runtime**: Ollama or vLLM on localhost — no external API calls for document content
- **Concurrency**: Asyncio Semaphore cap of 40 for debate loops; Celery worker pools for ingestion; CPU-heavy parsing must stay out of the async event loop (use thread pools)
- **Debate termination**: Hard cap of 3 rounds per finding; no unbounded loops
- **Schema contracts**: All agent-to-agent and DB boundaries must validate through Pydantic v2 models — no raw dict passing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vectorless BM25 retrieval over embeddings | Embeddings compress hyper-specific constraint clauses near generic text, causing semantic drift on debt covenants and exact clause matching | — Pending |
| 100% open-source local LLMs | Legal documents are confidential; cloud egress is a data security and client trust issue | — Pending |
| Pre-flight GraphRAG before debate | Cross-references broken by chunking must be resolved before agents analyze findings, not after | — Pending |
| Append-only audit log for human overrides | Regulators and legal auditors require immutable AI reasoning trails; human judgment is additive, not destructive | — Pending |
| 3-round hard cap on debate | Guarantees system termination; findings not resolved in 3 rounds route to explicit gap report rather than speculative consensus | — Pending |
| Pydantic v2 as system-wide contract layer | Open-source LLMs produce malformed JSON; Pydantic retry loops with exact error messages self-heal without human intervention | ✓ Good |

---
*Last updated: 2026-05-30 after research phase — initial PROJECT.md creation from Phase 1 codebase*
