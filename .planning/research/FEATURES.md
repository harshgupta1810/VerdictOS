# Feature Research

**Domain:** Deterministic multi-agent legal document analysis platform (M&A due diligence, compliance auditing)
**Researched:** 2026-05-30
**Confidence:** HIGH — derived from project requirements, active implementation scope, and explicit architectural decisions in PROJECT.md

---

## Feature Landscape

### Table Stakes (Users Expect These)

Legal and compliance teams have a baseline expectation from any document analysis platform. Missing these makes the product feel like a prototype, not a production tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-format document ingestion (PDF, DOCX) | M&A due diligence rooms live in PDF/Word; any tool that can't ingest both is dead on arrival | MEDIUM | pdfplumber + python-docx; CPU-heavy parsing must run in thread pools, not async event loop |
| Deal/matter workspace management | Analysts organize work by transaction; documents without deal context are unqueryable | LOW | DB-backed deal model, one deal → many documents |
| Async job status tracking | Document parsing + debate loops take minutes; users need progress visibility | LOW | Celery task states exposed via REST; polling or webhook |
| Structured findings output with exact source citations | Legal teams cannot act on "the contract probably says…"; every finding must point to exact text | HIGH | BM25 retrieval ensures quoted source text, not paraphrased; citation = (document_id, section, char_offset) |
| REST API for downstream integration | Legal tech stacks (contract lifecycle managers, GRC tools) need to consume findings programmatically | MEDIUM | FastAPI routes: upload, deal CRUD, job status, findings retrieval |
| Append-only audit trail | Regulators and auditors require immutable reasoning records | LOW | DB-level constraint; human overrides are metadata additions, never mutations |
| Human review and override layer | Analysts must be able to flag, annotate, and escalate findings without overwriting AI reasoning | MEDIUM | Append-only metadata model; override events stored separately from AI execution log |
| Gap report for insufficient-evidence findings | Saying "we found nothing" confidently is as important as a positive finding in due diligence | MEDIUM | Judge agent produces explicit gap reports when 3-round debate produces no consensus |
| Document and clause search | Analysts need to retrieve specific clauses post-analysis | MEDIUM | Elasticsearch BM25 with clause taxonomy tags; exact-match over full-text |
| Analysis job re-run / incremental update | Deals evolve; new documents are added mid-process | MEDIUM | Re-ingestion pipeline with document versioning; avoids re-running full debate on unchanged chunks |

### Differentiators (Competitive Advantage)

These are the features that make VerdictOS genuinely different from generic RAG-over-PDF tools. They directly address the failure modes that motivated the architecture.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Adversarial multi-persona debate (DebateOS) | A finding that doesn't survive adversarial challenge is not a finding; debate filters hallucinations before they reach the verdict | HIGH | 6 personas, 8 strategic tracks, 3-round hard cap, dimension gating at < 3 findings, circuit breaker at 15% failure rate |
| Vectorless BM25 exact-clause retrieval | Embeddings compress "debt covenant not to exceed $50M" near generic debt language; BM25 returns the exact clause or nothing | HIGH | Elasticsearch with clause taxonomy tags; deliberate rejection of cosine similarity |
| GraphRAG cross-reference resolver | Sliding-window chunking severs cross-references ("as defined in Section 4.2"); pre-flight entity resolution re-links them before agents analyze | HIGH | 3-tier resolver: string match → fuzzy match → LLM disambiguation → NetworkX graph |
| Explicit gap reports vs. speculative consensus | If debate produces no consensus in 3 rounds, the system says "insufficient evidence" rather than inventing an answer — a hard architectural guarantee | MEDIUM | Judge agent routes unresolved findings to structured gap report JSON, not a softened positive finding |
| 16 specialist discovery agents with isolated vocabularies | Domain-isolated agents (e.g., debt covenant agent, IP assignment agent) carry curated vocabulary indexes and produce findings scoped to their domain, not a single generalist prompt | HIGH | Each agent has its own prompt + vocabulary index; results tagged by domain for downstream filtering |
| 100% local LLM execution | Legal documents are client-confidential; cloud API calls are a data security and professional responsibility risk | MEDIUM | Ollama/vLLM on localhost; no document content leaves the machine |
| Clause taxonomy classification at ingestion | Classifying chunks at ingestion time (e.g., indemnification, termination, IP assignment) enables precise agent routing and reduces noise in retrieval | MEDIUM | Applied during chunking pipeline; taxonomy tags stored as Elasticsearch field metadata |
| Prompt injection defense via XML tagging | Open-source LLMs are susceptible to instruction-following in retrieved document text; wrapping retrieved content in `<untrusted_source>` tags isolates it from the system instruction | LOW | Applied at BM25 retrieval result injection time; strict JSON-only output instructions prevent leakage |
| Pydantic v2 self-healing JSON contracts | Open-source LLMs produce malformed JSON; Pydantic retry loops with exact error feedback self-heal agent outputs without human intervention | MEDIUM | All agent-to-agent boundaries validated through Pydantic v2; retry loops with structured error messages injected back to LLM |
| Context-compressed debate history | Full debate transcripts at 3 rounds would exceed local model context windows; structured JSON summaries keep token usage manageable | MEDIUM | Debate history serialized as structured JSON summary before each round, not raw text |

### Anti-Features (Commonly Requested, Often Problematic)

These features will be requested. Resist them. The reasons are architectural, not preference.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Vector/semantic similarity search | "It's what AI does"; surface-level appeal of semantic matching | Compresses hyper-specific legal constraints near generic language → semantic drift on debt covenants and exact clause terms; defeats the core correctness guarantee | BM25 with clause taxonomy tags achieves exact matching without drift |
| Cloud LLM integration (GPT-4, Claude API) | "Better reasoning"; users accustomed to cloud model quality | Legal documents are client-confidential; cloud egress is a data security failure and professional responsibility violation; also creates external API dependency for critical-path analysis | Local Llama-3 / Qwen-2.5 via Ollama/vLLM; quality sufficient for structured extraction with adversarial validation |
| General-purpose document Q&A ("chat with your contract") | Familiarity with ChatGPT-style interfaces | Conversational Q&A produces unverified, non-traceable answers; undermines the deterministic, citation-anchored architecture; scope creep away from structured analysis | Structured findings via discovery agents + debate produces higher-quality, verifiable output |
| Real-time streaming findings | UX expectation from consumer AI tools | Findings are not valid until debate completes and judge produces verdict; streaming partial findings before adversarial validation is displaying unvalidated speculation | Async job model with status polling; deliver complete verdict, not incremental guesses |
| Mutable/editable AI execution logs | "We need to correct mistakes in the log" | Append-only audit trail is a regulatory requirement; mutable logs destroy audit integrity for legal proceedings | Human overrides are additive metadata on top of immutable AI logs; log = what the AI did, override = what the human decided |
| Automatic citation formatting (Bluebook, APA) | Adjacent legal workflow automation | Out of scope; citation format is output layer concern for the consuming UI/workflow, not the analysis engine | Findings include raw source references (doc_id, section, offset); consuming systems format as needed |
| Embedding-based semantic deduplication of findings | Reducing redundant findings sounds beneficial | Semantic deduplication using embeddings is the mechanism being avoided; structural deduplication via entity graph is the correct approach | GraphRAG entity resolver handles cross-document entity disambiguation without embeddings |
| Frontend dashboard | Users want a complete product | Frontend UI is explicitly out of scope; building it within the backend project creates maintenance coupling and scope bloat | REST API is the delivery mechanism; UI is a separate consumer application |

---

## Feature Dependencies

```
[Document Ingestion Pipeline]
    ├──requires──> [Thread Pool (CPU isolation from async loop)]
    ├──produces──> [Section-aware chunks with clause taxonomy tags]
    └──feeds──> [Elasticsearch BM25 Index]
                    └──required by──> [16 Specialist Discovery Agents]
                                          └──produces──> [Findings → DebateOS]

[3-Tier Entity Resolver]
    ├──string match → fuzzy match → LLM disambiguation
    └──produces──> [NetworkX GraphRAG]
                       └──required by──> [Discovery Agents (cross-ref resolution)]

[DebateOS Adversarial Loop]
    ├──requires──> [Findings from Discovery Agents (≥ 3 to gate on)]
    ├──requires──> [Async LLM Client (Ollama/vLLM)]
    ├──requires──> [Asyncio Semaphore cap = 40]
    └──produces──> [Debate transcript → Consensus Mapper]

[Consensus Mapper]
    ├──requires──> [DebateOS output]
    └──produces──> [Structured JSON synthesis → Judge Agent]

[Judge Agent]
    ├──requires──> [Consensus Mapper output]
    ├──produces──> [Final Verdict]
    └──produces──> [Gap Reports (unresolved findings)]

[Human Override Layer]
    ├──requires──> [Append-only Audit Log]
    └──requires──> [Final Verdict (to annotate)]

[Celery Worker Pipeline]
    └──orchestrates──> [Ingestion → Entity Resolution → BM25 Index → Discovery → Debate → Consensus → Verdict]

[REST API]
    └──exposes──> [Upload, Deal CRUD, Job Status, Findings, Escalations, Gap Reports]
```

### Dependency Notes

- **Discovery Agents require GraphRAG:** Cross-references must be resolved before agents analyze chunks or they will miss linked clause relationships — this is the pre-flight GraphRAG requirement.
- **DebateOS requires ≥ 3 findings:** Dimension gating prevents debate spin-up overhead for sparse document sections; below threshold, findings pass directly to judge.
- **Gap Reports require Judge Agent:** The judge is the only component with authority to declare "insufficient evidence" — gap reports are not a fallback path but a first-class output type.
- **Human Override requires immutable AI log:** The append-only constraint is a hard dependency; any feature that needs to "correct" AI logs is architecturally incompatible.
- **Celery Pipeline requires Redis:** Redis is the broker for both Celery task queuing and potentially caching debate state between rounds.

---

## MVP Definition

### Launch With (v1) — Phase 2–3

Minimum to deliver a verifiable, traceable legal analysis verdict on a single document.

- [x] Document ingestion: PDF + DOCX parsing, section-aware chunking (200–500 tokens), clause taxonomy classification
- [x] BM25 Elasticsearch indexing with taxonomy tags — required before any agent can search
- [x] Entity resolver (3-tier) + NetworkX GraphRAG — required before discovery agents run
- [x] 16 specialist discovery agents producing tagged findings
- [x] DebateOS adversarial loop (3-round cap, semaphore, circuit breaker, dimension gating)
- [x] Consensus mapper → Judge agent producing final verdict + gap reports
- [x] Celery pipeline connecting all stages end-to-end
- [x] REST API: document upload, job status, findings retrieval
- [x] Append-only audit log (already in DB schema)

### Add After Validation (v1.x)

Features that improve operational usability once core analysis pipeline is verified correct.

- [ ] Human override layer — essential for production but not needed to validate analysis quality
- [ ] Deal workspace management with multi-document deals — validate single-doc first, then extend
- [ ] Analysis job re-run / incremental update on new documents — depends on versioning scheme validated in v1
- [ ] Escalation routes in REST API — dependent on understanding what gap-report resolution looks like in practice

### Future Consideration (v2+)

Features that require validated production usage patterns before scoping.

- [ ] Batch deal processing (multiple deals in parallel) — defer until concurrency limits are validated at scale
- [ ] Clause-level change detection across document versions — requires document versioning infrastructure
- [ ] Multi-tenancy and access control — architectural concern for SaaS deployment; single-tenant first
- [ ] Webhook notifications for job completion — nice-to-have; polling is sufficient for v1

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Document ingestion (PDF/DOCX) | HIGH | MEDIUM | P1 |
| BM25 Elasticsearch indexing | HIGH | MEDIUM | P1 |
| Entity resolution + GraphRAG | HIGH | HIGH | P1 |
| Specialist discovery agents (×16) | HIGH | HIGH | P1 |
| DebateOS adversarial loop | HIGH | HIGH | P1 |
| Consensus mapper + Judge agent | HIGH | MEDIUM | P1 |
| Gap reports for unresolved findings | HIGH | LOW | P1 |
| Celery pipeline orchestration | HIGH | MEDIUM | P1 |
| REST API (upload, status, findings) | HIGH | LOW | P1 |
| Append-only audit log | HIGH | LOW | P1 |
| Human override / escalation layer | MEDIUM | MEDIUM | P2 |
| Deal workspace management | MEDIUM | LOW | P2 |
| Incremental re-run on new documents | MEDIUM | MEDIUM | P2 |
| Webhook job completion notifications | LOW | LOW | P3 |
| Batch deal processing | LOW | HIGH | P3 |
| Clause-level version diff | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch — without this, the system cannot produce a valid verdict
- P2: Should have — adds operational usability, add when P1 pipeline is stable
- P3: Nice to have — defer until production usage patterns are understood

---

## Competitor Feature Analysis

VerdictOS is not a general legal AI tool. The relevant comparison class is purpose-built M&A due diligence and contract analysis platforms.

| Feature | Kira Systems / Luminance (traditional) | Harvey AI / Spellbook (cloud LLM) | VerdictOS |
|---------|----------------------------------------|-----------------------------------|-----------|
| Retrieval method | ML classifier + keyword | Vector embeddings + GPT-4 | BM25 exact-match + clause taxonomy |
| Hallucination risk | Low (classifier-based) | High (generative, no adversarial check) | Low (adversarial debate + citation-anchored) |
| Data residency | Cloud SaaS | Cloud API (OpenAI/Anthropic) | 100% local; no egress |
| Multi-party adversarial validation | None | None | Core architecture (DebateOS) |
| Explicit gap reporting | Partial (low-confidence flags) | None (speculates) | Structured gap report JSON |
| Cross-reference resolution | Limited | Sliding-window only | GraphRAG pre-flight |
| Open-source / self-hosted | No | No | Yes (Ollama/vLLM) |
| Customizable specialist agents | No | No | 16 domain-specific agents |

**Our approach:** VerdictOS competes on correctness guarantees and data security, not on UX polish or general-purpose flexibility. The target buyer is the legal team that has been burned by a hallucinated clause reference in a cloud LLM tool, or whose IT/legal compliance policy prohibits cloud egress of deal documents.

---

## Sources

- VerdictOS PROJECT.md — authoritative requirements and architectural decisions (HIGH confidence)
- Active requirements list in PROJECT.md — defines what is in scope for current implementation phase
- Out-of-scope list in PROJECT.md — defines anti-features by architectural decision
- Competitor analysis: Kira Systems, Luminance, Harvey AI, Spellbook — general market knowledge (MEDIUM confidence; not independently verified for current feature sets)
- Legal AI failure modes: semantic drift on debt covenants, hallucinated citations, cross-reference fragmentation — documented as explicit solved problems in PROJECT.md (HIGH confidence)

---
*Feature research for: Deterministic multi-agent legal document analysis (M&A due diligence)*
*Researched: 2026-05-30*
