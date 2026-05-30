# VerdictOS

Multi-agent system for transaction validation, corporate compliance tracking, and M&A due diligence.

## Architecture

VerdictOS uses a deterministic **vectorless multi-agent architecture** with:
- **Elasticsearch BM25** sparse retrieval (no vector embeddings)
- **spaCy + NetworkX** pre-flight structural GraphRAG
- **6-persona adversarial debate engine** across 8 strategic dimensions
- **Pydantic V2** schema contracts for all agent-to-agent boundaries
- **100% open-source LLM stack** (Llama-3, Qwen-2.5, Mistral via Ollama)

## Quick Start

```bash
# Create an isolated environment and install dependencies
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m spacy download en_core_web_sm

# Start infrastructure (Elasticsearch, Redis, PostgreSQL)
docker compose -f docker/docker-compose.yml up -d

# Run dev server
.venv/Scripts/python -m uvicorn src.api.main:app --reload

# Run tests
.venv/Scripts/python -m pytest tests/
```

## Runtime Phase 1

The synchronous pre-flight pipeline is implemented in `src/preflight.py`. It parses PDF/DOCX files, creates classified section-aware chunks, constructs the NetworkX GraphRAG model, incrementally indexes Elasticsearch BM25 records, and emits the active-specialist manifest consumed by Phase 2.

Graph artifacts can be persisted as JSON or GraphML using the helpers in `src/graphrag/graph_constructor.py`.

## Project Structure

See `memory/system_overview.md` for full architecture documentation.
