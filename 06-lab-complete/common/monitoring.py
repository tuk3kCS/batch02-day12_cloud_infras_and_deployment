"""Lightweight in-process observability for agent monitoring (Challenge 4).

Tracks per-agent request counts, error counts, and response latencies.
Exposes a /metrics JSON endpoint via add_metrics_endpoint().

Production upgrade paths:
  - LangSmith: set LANGSMITH_API_KEY + LANGSMITH_TRACING=true in .env
    LangChain/LangGraph instruments automatically with no code changes.
  - Prometheus: replace AgentMetrics with prometheus_client Counters/Histograms
    and expose /metrics in Prometheus text format.
"""
from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List

from fastapi import FastAPI


class AgentMetrics:
    def __init__(self) -> None:
        self._requests: Dict[str, int] = defaultdict(int)
        self._errors: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)

    def record(self, agent: str, latency: float, success: bool) -> None:
        self._requests[agent] += 1
        self._latencies[agent].append(round(latency, 4))
        if not success:
            self._errors[agent] += 1

    def snapshot(self) -> dict:
        result = {}
        for agent in self._requests:
            lats = self._latencies[agent]
            sorted_lats = sorted(lats)
            n = len(sorted_lats)
            result[agent] = {
                "requests_total": self._requests[agent],
                "errors_total": self._errors[agent],
                "error_rate": round(self._errors[agent] / max(self._requests[agent], 1), 3),
                "avg_latency_s": round(sum(lats) / n, 3) if n else 0.0,
                "p50_latency_s": round(sorted_lats[int(n * 0.50)], 3) if n else 0.0,
                "p99_latency_s": round(sorted_lats[min(int(n * 0.99), n - 1)], 3) if n else 0.0,
            }
        return result


# Process-wide singleton
metrics = AgentMetrics()


def record(agent: str, latency: float, success: bool) -> None:
    """Record one request observation."""
    metrics.record(agent, latency, success)


@asynccontextmanager
async def track(agent: str) -> AsyncGenerator[None, None]:
    """Async context manager: automatically records latency and success/failure.

    Usage:
        async with track("law-agent"):
            result = await some_operation()
    """
    t0 = time.monotonic()
    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        metrics.record(agent, time.monotonic() - t0, success)


def add_metrics_endpoint(app: FastAPI, agent_name: str) -> None:
    """Register GET /metrics on a FastAPI app that returns JSON metrics."""

    @app.get("/metrics", tags=["observability"])
    async def get_metrics() -> dict:
        return {
            "agent": agent_name,
            "metrics": metrics.snapshot(),
        }
