"""5 Sequential Reliability Gates (A-E).

Gate A: Schema Verification (Pydantic validation + auto-retry)
Gate B: Citation Validation (BM25 verification via Elasticsearch)
Gate C: Self-Contradiction Check (intra-persona timeline)
Gate D: Stance Calibration (score-argumentation alignment)
Gate E: Consensus Mapping (stance synthesis to Judge)
"""
