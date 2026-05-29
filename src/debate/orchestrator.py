"""DebateOS Multi-Agent Orchestrator.

Coordinates the asyncio debate lifecycle across Phases 2-6:
smart dispatch, findings aggregation, adversarial debate loops,
consensus mapping, and judge synthesis.

Concurrency: Asyncio Semaphore (max 40), 3-round limit.
"""
