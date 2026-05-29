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
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (Elasticsearch, Redis, PostgreSQL)
docker compose -f docker/docker-compose.yml up -d

# Run dev server
uvicorn src.api.main:app --reload

# Run tests
pytest tests/
```

## Project Structure

See `memory/system_overview.md` for full architecture documentation.
