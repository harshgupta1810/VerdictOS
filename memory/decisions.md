# Architecture Decision Records (ADRs)

This document contains the core engineering decisions made for VerdictOS, detailing context, decisions, and consequences.

---

## ADR 001: Vectorless Elasticsearch Sparse BM25 Retrieval

### Context
Standard RAG pipelines utilize dense vector database models for similarity-based context searches. However, dense vectors compress text semantics and introduce semantic drift, meaning a specific liability trigger (e.g. debt limits) can be geometrically grouped near irrelevant descriptions. It also leads to hallucinated citation markers (since cosine distance always yields results) and strips document hierarchy during sliding chunking.

### Decision
We replace all vector-based search algorithms with a dedicated **Elasticsearch cluster** mapping exact keywords using BM25 sparse matching integrated with section-aware metadata pointers.

### Consequences
- **Pros:** 100% deterministic citation trace verification, zero embedding API costs, exact keyword matches, structural tag queries, and cluster-scale multi-tenant isolation.
- **Cons:** Vocabulary mismatch must be handled at the agent layer using synonyms and domain-specific query expansion rules.

---

## ADR 002: Pydantic V2 Middleware and Auto-Retry Loop

### Context
Language models outputting JSON under high context pressures can occasionally emit malformed syntax or omit required validation fields, which stalls downstream automated components.

### Decision
We bind all agent communication pathways through a middleware verification layer utilizing Pydantic V2. If parsing fails, the middleware executes an automatic single-attempt retry request containing the explicit validation traceback. If the retry also fails, the payload is isolated and a structured fallback record is issued.

### Consequences
- **Pros:** Pipeline resilience, automatic error self-correction, and schema safety.
- **Cons:** Introduces minor latency and API cost increases in the event of a validation retry.

---

## ADR 003: Append-Only DB Constraints on Debate Transcripts

### Context
Auditing legal transactions requires maintaining an untampered paper trail. If users or system runtimes could modify or delete historical debate timelines, it would invalidate the system's audit lineage.

### Decision
We configure the database tier to deny `UPDATE` and `DELETE` queries on the `debate_transcripts` table. Human loop corrections do not overwrite records; they are stored as separate metadata nodes linked by timestamps.

### Consequences
- **Pros:** Unalterable, compliance-ready database audit trail.
- **Cons:** Storage requirements increase continuously; application code must merge the base records and human modification logs at query time.

---

## ADR 004: Programmatic Steelman Validation Constraint

### Context
Language models executing analysis in a single pass are highly prone to confirmation bias, which leads to weak adversarial evaluation.

### Decision
We force every adversarial persona to populate a required `steelman` JSON property within their output schemas. This field must explicitly articulate the strongest possible argument in favor of the position they are challenging.

### Consequences
- **Pros:** Prevents strawman fallacies in AI debate; guarantees high-quality critical analysis.
- **Cons:** Slightly increases input/output token counts.

---

## ADR 005: 3-Round Debate Limit and Early Exit Criteria

### Context
Multi-agent discussions can run into circular loops or infinite conversations if agents continuously dispute minor terminology.

### Decision
We enforce a hard cap of 3 debate rounds within the custom Asyncio runtime. Additionally, we check consensus after each round: if 4 or more personas share the same stance, the debate terminates early, routing intermediate transcripts to Phase 5.

### Consequences
- **Pros:** Guaranteed execution termination, protection against unbounded API billing, and faster processing.
- **Cons:** Complex, unresolved edge cases may be force-stopped early (though the Judge Agent and human loop will flag them).

---

## ADR 006: 100% Open-Source LLM Pipeline

### Context
High-stakes due diligence requires processing highly confidential enterprise documents, including merger agreements and financial audits. Transmitting this data to proprietary closed APIs (like OpenAI or Anthropic) introduces significant data leakage risks and high operational API token billing.

### Decision
We deploy the reasoning and disambiguation LLM layers entirely on local open-source models (such as Llama-3, Mistral, or Qwen-2.5) orchestrated via a local **Ollama** (`http://localhost:11434`) or a **vLLM** runtime.

### Consequences
- **Pros:** 100% data privacy (runs entirely on local hardware), zero external API token costs, and custom prompt/schema tuning freedom.
- **Cons:** Relies on local GPU compute capacity. Model prompts must be highly optimized for open-source model syntax.

---

## ADR 007: Simplified Gateways (No RBAC Scopes for Initial Phase)

### Context
Setting up granular client permissions (e.g. JWT scope checks for `auditor`, `operator`, `system_admin`) in the bootstrap phase creates development overhead and restricts rapid API validation.

### Decision
We omit granular RBAC scope validation from the immediate FastAPI gateway implementation. A simplified OAuth 2.0 validation layer will authenticate incoming connections, leaving role segregation for future deployment milestones.

### Consequences
- **Pros:** Accelerated gateway routing development and simpler unit tests.
- **Cons:** Temporary lack of granular permission levels in early builds.
