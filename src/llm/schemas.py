"""Pydantic schemas for LLM request/response contracts.

Defines structured input/output models for LLM API interactions,
including prompt templates and response parsing.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LLMRequest(BaseModel):
    """Structured request sent to the local Ollama LLM service."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    system_prompt: str = Field(default="")
    user_prompt: str = Field(min_length=1)
    format: Literal["json"] = "json"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class LLMResponse(BaseModel):
    """Structured response received from the local Ollama LLM service."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    raw_text: str = Field(default="")
    parsed_json: dict[str, Any] | None = None
    duration_ms: int = Field(default=0, ge=0)
