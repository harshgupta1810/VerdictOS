import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT = "INSECURE-CHANGE-IN-PRODUCTION"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Elasticsearch
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index: str = Field(default="verdictos_documents")

    # Local LLMs
    ollama_url: str = Field(default="http://localhost:11434")
    llm_reasoning_model: str = Field(default="llama3")
    llm_disambiguation_model: str = Field(default="qwen2.5")

    # Redis (Queue and Cache)
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./verdictos.db")

    # Gateway / JWT Security
    jwt_secret: str = Field(default=_INSECURE_DEFAULT)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440, ge=1)

    @field_validator("jwt_secret")
    @classmethod
    def warn_if_insecure_jwt_secret(cls, value: str) -> str:
        if value == _INSECURE_DEFAULT:
            logger.warning(
                "JWT_SECRET is set to the insecure default. "
                "Set JWT_SECRET via environment variable or .env file before deploying."
            )
        return value


settings = Settings()
