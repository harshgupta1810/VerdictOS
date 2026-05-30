import os

from pydantic import BaseModel


class Settings(BaseModel):
    # Elasticsearch
    elasticsearch_url: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    elasticsearch_index: str = os.getenv("ELASTICSEARCH_INDEX", "verdictos_documents")

    # Local LLMs
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    llm_reasoning_model: str = os.getenv("LLM_REASONING_MODEL", "llama3")
    llm_disambiguation_model: str = os.getenv("LLM_DISAMBIGUATION_MODEL", "qwen2.5")

    # Redis (Queue and Cache)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./verdictos.db")

    # Gateway / JWT Security
    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

settings = Settings()
