"""3-Tier Entity Resolution Engine.

Resolves naming variations across documents using:
  - Tier 1: Case-insensitive string match / punctuation stripping
  - Tier 2: Fuzzy logic (Levenshtein distance ratio > 0.85)
  - Tier 3: LLM-prompted disambiguation via Ollama
"""
