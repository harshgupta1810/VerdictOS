# VerdictOS Component Specifications

This document outlines the detailed specifications, inputs, outputs, and interface contracts for every module in VerdictOS.

---

## 1. Document Ingestion and Parser
* **Module Path:** `src/ingestion/ingest.py`
* **Technologies:** `pdfplumber`, `python-docx`, `re`
* **Responsibilities:**
  - Ingest PDF and DOCX files.
  - Parse layout structures, coordinate mappings, and paragraph groupings.
  - Extract text and determine section boundaries (e.g. looking for text formats matching headers).
* **Expected Output:**
  ```python
  {
      "document_name": str,
      "raw_pages": [
          {"page_index": int, "text": str, "layout_info": dict}
      ]
  }
  ```

---

## 2. Section-Aware Chunker
* **Module Path:** `src/ingestion/chunker.py`
* **Responsibilities:**
  - Segment document text at clause/sentence boundaries rather than arbitrary token counts.
  - Keep chunks bounded between **200 and 500 tokens**.
  - Capture structural metadata.
* **Chunk Metadata Schema:**
  ```python
  class ChunkMetadata(BaseModel):
      section_id: str             # e.g., "Section 9.4"
      absolute_page: int          # 0-indexed page number
      references_sections: list[str] # List of regex-extracted section strings
  ```

---

## 3. Clause-Type Classifier
* **Module Path:** `src/ingestion/classifier.py`
* **Responsibilities:**
  - Run rule-based heuristic patterns (regex/keyword search) over each text chunk to map to legal/operational taxonomy.
  - Standard Taxonomy Tags: `tax_provision`, `ip_assignment`, `termination_clause`, `departure_covenant`, `non_compete`, `liability_limit`, `governing_law`.
  - Apply conservative tag `'general'` if boundaries are ambiguous.

---

## 4. 3-Tier Entity Resolution Engine
* **Module Path:** `src/graphrag/entity_resolver.py`
* **Responsibilities:**
  - Resolve naming variations (e.g., "Acme Corp", "Acme Corporation", "ACME Ltd.") across multiple documents.
* **Execution Tiers:**
  - **Tier 1:** Case-insensitive string match / punctuation stripping (~80% resolution rate).
  - **Tier 2:** Localized string distance fuzzy logic (Levenshtein distance ratio > 0.85) (~15% resolution rate).
  - **Tier 3:** Prompted LLM checks using a **local Open-Source model (e.g. Llama-3/Mistral/Qwen via Ollama)** (~5% resolution rate).
  - Unresolved links are tagged as `unconfirmed_node` to maintain audit trail.

---

## 5. GraphRAG Knowledge Graph Constructor
* **Module Path:** `src/graphrag/graph_constructor.py`
* **Technologies:** `spacy` (NER), `networkx`
* **Responsibilities:**
  - Extract entities (Organization, Person, Location, Asset, Code) in pre-flight.
  - Construct a `networkx.DiGraph` representing entities and their cross-document relationships.
  - Serialize the graph to JSON/GraphML files for localized loading by active agents.

---

## 6. Sparse Retrieval Engine (Elasticsearch)
* **Module Path:** `src/search/search_engine.py`
* **Technologies:** Elasticsearch (`elasticsearch` python client)
* **Responsibilities:**
  - Connect to a local or managed Elasticsearch cluster (port 9200).
  - Index document chunks with metadata and taxonomy tags.
  - Expose search methods returning exact term matches and structured paragraph citations.
  - Support incremental updates: when supplementary documents are added, index updates are performed without rebuilding the entire index.

---

## 7. Multi-Agent Orchestration & Debate Engine (DebateOS)
* **Module Path:** `src/debate/`
* **Core Components:**
  - `schemas.py`: Pydantic V2 definitions enforcing data contracts.
  - `personas.py`: Defines prompt structures for the 6 debate personas.
  - `orchestrator.py`: Asyncio event loop running debate lifecycles.

### LLM Runtime Engine
- All personas and judge loops are powered by a **100% open-source LLM runtime** (such as Ollama or vLLM running Llama-3, Mistral, or Qwen-2.5 models).

### Concurrency Throttling
- Execution is gated by a central **Asyncio Semaphore (max 40)** to prevent local API service rate limit bottlenecks.

### Strategic Debate Tracks & Personas
- **8 Dimensions:** Risk Exposure, Valuation Fairness, Strategic Fit, Synergy Validity, Integration Complexity, Market Timing, Regulatory Approval, Exit Scenario.
- **Dimension Gating:** Skip debates for dimensions containing fewer than 3 verified findings, writing sparse findings directly to the final gap report.
- **6 Personas:** Proponent, Critic, Devil's Advocate, Valuation Skeptic, Integration Realist, Regulator's Eye.

### The Steelman Rule Contract
- Every response from an adversarial persona must populate a non-empty `steelman` JSON property within their output schemas. If missing, the Pydantic middleware fails validation and triggers a schema retry.

### Concurrency and Termination Rules
- Max debate rounds: **3 rounds**.
- Early exit occurs if consensus is reached across 4 or more personas, terminating the loop and routing intermediate logs to Phase 5 Consensus Mapping.

### The 5 Sequential Reliability Gates
1. **Gate A: Schema Verification** (Pydantic payload validation; auto-retry on fail).
2. **Gate B: Citation Validation** (BM25 verification of all extracted quotes via Elasticsearch; unreferenced quotes are stripped).
3. **Gate C: Self-Contradiction Check** (Flags logical clashes within the same persona timeline).
4. **Gate D: Stance Calibration** (Validates that the stance score matches the argumentation).
5. **Gate E: Consensus Mapping** (Synthesizes stances and outputs findings to the Judge).

---

## 8. Database Architecture
* **Module Path:** `src/db/`
* **Engine:** PostgreSQL (Production), SQLite (Local Fallback)
* **Design Patterns:**
  - **Append-only integrity:** Revoke UPDATE and DELETE permissions on the `debate_transcripts` table.
  - **GIN Indexing Strategy:** Index key JSONB fields to accelerate search operations:
    ```sql
    CREATE INDEX idx_findings_dimension_severity ON findings USING gin (dimension, severity);
    CREATE INDEX idx_debate_transcripts_payload ON debate_transcripts USING gin (raw_payload);
    ```

---

## 9. FastAPI Gateway API Endpoints
* **Module Path:** `src/api/main.py`
* **Authentication and Security:**
  - OAuth 2.0 with JWT access token checks.
  - Granular Role-Based Access Control (RBAC) scopes are omitted in this phase to simplify gateway routes.
* **Routing Table:**
  - `POST /api/v1/deals`: Submit a deal containing a document manifest. Starts pre-flight parsing and indexing in Elasticsearch.
  - `GET /api/v1/deals/{id}/status`: Stream progress percentage, current active specialists, and rounds via WebSockets/SSE.
  - `GET /api/v1/deals/{id}/verdict`: Returns the compiled, structured JSON verdict.
  - `GET /api/v1/deals/{id}/audit`: Access immutable debate transcripts.
  - `POST /api/v1/deals/{id}/escalations/{eid}/resolve`: Resolve escalated issues (triggers 4-hour SLA alert on timeout).
  - `POST /api/v1/deals/{id}/findings/{fid}/dispute`: Record a user dispute and trigger delta re-runs.
