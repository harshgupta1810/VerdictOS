# VerdictOS Coding and Development Guidelines

This document outlines key coding, prompt engineering, and operational guidelines for developers and agent runtimes.

---

## 1. Code Style and Architecture
- **Async-First Execution:** All gateway integrations, DB operations (using async SQLAlchemy), and agent-to-agent loops must utilize async/await blocks. Synchronous libraries must be executed in thread pools.
- **Strict Separation of Concerns:** Keep the pre-flight parsing/indexing boundary (CPU-intensive) isolated from the async orchestration event loop. Do not mix text parsing logic inside Celery workers or FastAPI routing threads.
- **Pydantic Contracts:** Every file interaction or network exchange should validate against a Pydantic model. Avoid using raw dictionary values.

---

## 2. Prompt Engineering Standards (Open-Source Models)
- **XML Boundaries for Raw Data:** Raw document text retrieved via BM25 from Elasticsearch must be enclosed inside `<untrusted_source>` tags within prompt contexts to prevent prompt injection:
  ```xml
  <untrusted_source doc_id="patent_assignment_agreement.pdf" page="4">
  [Ingested text here]
  </untrusted_source>
  ```
- **Strict JSON Enforcement for Local LLMs:** Open-source models (e.g. Llama-3/Mistral/Qwen) need explicit instructions to prevent conversational text leakage before or after JSON structures. Formulate system prompts to enforce strict JSON syntax:
  ```
  [System Instruction]
  You must output a single, raw JSON object matching the requested schema. 
  Do NOT include any conversational introduction, explanation, or markdown formatting (such as ```json) outside the JSON block.
  ```
- **Steelman Validation Instruction:** Persona prompts must contain explicit instructions to formulate the strongest possible arguments for opposing views in the `steelman` property.

---

## 3. Token Limits and Memory Management
- **Context Compression Memory:** Never feed raw chat transcripts from prior rounds directly to debate personas. Use the structured JSON context summary layout:
  ```json
  {
      "active_finding_id": "UUID",
      "historical_stances": {"proponent": ["for", "for"], "critic": ["against", "neutral"]},
      "strongest_counter_arguments": ["List of arguments"],
      "contradiction_flags": {"critic": false}
  }
  ```
  This reduces context usage by 90% and keeps local model inference speed high.

---

## 4. Error Handling and Rate Limiting
- **Pydantic Auto-Retry:** Wrap JSON parsing logic in try-except blocks. On validation failures, send a one-time repair prompt back to the local model endpoint with the exact validation error:
  ```
  [System Message]
  Your previous JSON output failed validation with error: {validation_error}. 
  Please output the corrected JSON structure.
  ```
- **Local Model Concurrency Management:** Local LLM engines (like Ollama) have limited parallel thread capabilities. Implement a backoff timeout handling strategy for local API timeouts when the concurrency Semaphore queue spikes.
- **Dimension Gating:** Skip processing of debate rounds for dimensions containing fewer than 3 verified findings, routing sparse findings directly to the gap report to prevent unnecessary compute.
- **Orchestration Circuit Breakers:** If LLM timeout/schema failure rates exceed 15% within a transaction, trigger the circuit breaker: halt active loops, drop Semaphore concurrent slots to 10, and generate a fallback verdict based on available logs.
