# VerdictOS System Overview

VerdictOS is a multi-agent system optimized for transaction validation, corporate compliance tracking, and complex Merger and Acquisition (M&A) due diligence.

---

## The Core Problem

Standard document review pipelines utilize vector databases coupled with cosine-similarity matching algorithms. While suitable for open-domain questions, these systems exhibit three core failures in high-stakes auditing:
1. **Semantic Proximity Space Drift:** Hyper-specific constraint clauses (e.g. debt covenants) are mathematically compressed and grouped near generic statements, omitting critical liabilities.
2. **Hallucinated Citation Strings:** Proximity scoring will always return context chunks even if no exact text exists, causing models to fabricate citation numbers (e.g. "Section 14.2(b)").
3. **Erosion of Hierarchical Structural Linkage:** Sliding-window chunking divides structural dependencies (e.g., cross-references) across arbitrary token boundaries, stripping critical parameters from agent contexts.

---

## VerdictOS Solution Vision

VerdictOS eliminates probabilistic retrieval failures through a deterministic, **vectorless multi-agent architecture** based on:
- **Vectorless sparse retrieval** utilizing an **Elasticsearch cluster** mapping exact keywords.
- **Pre-flight structural GraphRAG** utilizing spaCy and NetworkX to resolve entity cross-references before running analysis.
- **Multi-persona adversarial debate** (6 distinct personas across 8 strategic tracks) to test every finding.
- **Strict schema contract enforcement** (Pydantic v2 middleware) for all agent-to-agent and database boundaries.

---

## Seven Core Design Mandates

1. **Agent Specialization Over Generalization:** 16 narrowly scoped specialist discovery agents operate with isolated prompts and vocabulary indexes.
2. **Adversarial Verification Over Single-Pass Analysis:** Every specialist finding is a thesis that must withstand multi-round debate with a mandatory "Steelman" validation rule.
3. **Vectorless Retrieval with Structural Awareness:** Replaces embeddings with Elasticsearch queries + section/clause taxonomy mapping.
4. **Structured Output Schema as System Contract:** All agent interactions validate against strict Pydantic JSON targets.
5. **Guaranteed Termination via Hard Constraints:** Cap loops at a maximum of 3 rounds, routing directly to consensus mapping on early exits.
6. **Human Judgment as an Additive Layer:** Human overrides append separate metadata; they never overwrite or destroy original AI execution logs.
7. **Honest Architectural Self-Awareness:** Insufficient context or validation anomalies trigger explicit, unalterable gap reports instead of speculative conclusions.

---

## Architectural Boundaries

```
+------------------------------------+       +------------------------------------+
|   Synchronous Pre-Flight Boundary   |       |   Async Orchestration & Debate     |
|                                    |       |             Boundary               |
|  +------------------------------+  |       |  +------------------------------+  |
|  |       Document Parser        |  |       |  |     Asyncio Orchestrator     |  |
|  |   (pdfplumber, python-docx)  |  |       |  |  (Semaphore, 3-round Limit)  |  |
|  +--------------+---------------+  |       |  +--------------+---------------+  |
|                 |                  |       |                 |                  |
|  +--------------v---------------+  |       |  +--------------v---------------+  |
|  |    Section-Aware Chunker     |  |       |  |    Celery Worker Pools       |  |
|  |     (200-500 token size)     |  |       |  |     (Redis Task Broker)      |  |
|  +--------------+---------------+  |       |  +--------------+---------------+  |
|                 |                  |       |                 |                  |
|  +--------------v---------------+  |       |  +--------------v---------------+  |
|  |    Clause-Type Classifier    |  |       |  |        DebateOS Engine       |  |
|  |       (Taxonomy Tags)        |  |       |  |    (6 Personas, 8 Tracks)    |  |
|  +--------------+---------------+  |       |  +--------------+---------------+  |
|                 |                  |       |                 |                  |
|  +--------------v---------------+  |       |  +--------------v---------------+  |
|  |    3-Tier Entity Resolver    |  |       |  |       Consensus Mapper       |  |
|  |   (String -> Fuzzy -> LLM)   |  |       |  |       (JSON Synthesis)       |  |
|  +--------------+---------------+  |       |  +------------------------------+  |
|                 |                  |       |                                    |
|  +--------------v---------------+  |       |  +------------------------------+  |
|  |     GraphRAG Constructor     |  |------>|  |       PostgreSQL DB          |  |
|  |       (NetworkX Model)       |  |       |  |   (Append-Only Audit Log)   |  |
|  +------------------------------+  |       |  +------------------------------+  |
+------------------------------------+       +------------------------------------+
```

- **Synchronous Pre-Flight Boundary:** Isolates CPU-heavy document parsing, clause taxonomy classifying, entity resolving, and NetworkX knowledge graph mapping from the event loop.
- **Asynchronous Orchestration & Debate Boundary:** Coordinates parallel specialist task distribution, Redis broker communication, Celery worker processing, and multi-persona debate.
- **Open-Source LLM Orchestration:** All reasoning tier (Debate Engine) and disambiguation tier (Entity Resolution) processes utilize a **100% open-source LLM stack** (e.g. Llama-3, Qwen-2.5, or Mistral) hosted locally via Ollama (`http://localhost:11434`) or vLLM.
