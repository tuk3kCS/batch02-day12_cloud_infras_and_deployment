"""
Shared State Schema & Message Contracts.

Mọi worker đọc/ghi vào RAGState. Supervisor là người duy nhất
tạo state mới và chạy finalize.

Message contract:
    Supervisor → Worker:  WorkerInput(query, top_k, config, trace_id, step)
    Worker → Supervisor:  WorkerOutput(worker_id, step, result, latency_ms, trace_id, error)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────
# Trace entry — appended by every worker after each action
# ─────────────────────────────────────────────────────────────────
@dataclass
class TraceEntry:
    agent: str          # "supervisor" | "retrieval_worker" | "pageindex_worker" | "generation_worker"
    step: str           # tên bước cụ thể, e.g. "semantic_search", "rrf_merge", "llm_generate"
    status: str         # "start" | "ok" | "error" | "skip"
    detail: str = ""    # thông tin bổ sung (số chunk, score, lý do skip, ...)
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.monotonic)


# ─────────────────────────────────────────────────────────────────
# Shared State — truyền qua supervisor → workers → supervisor
# ─────────────────────────────────────────────────────────────────
@dataclass
class RAGState:
    # Input
    query: str
    top_k: int = 5
    use_reranking: bool = True
    score_threshold: float = 0.3

    # Tracing
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    trace: list[TraceEntry] = field(default_factory=list)

    # Intermediate results
    dense_results: list[dict] = field(default_factory=list)
    sparse_results: list[dict] = field(default_factory=list)
    merged_results: list[dict] = field(default_factory=list)
    reranked_results: list[dict] = field(default_factory=list)
    pageindex_results: list[dict] = field(default_factory=list)
    final_chunks: list[dict] = field(default_factory=list)  # chunks fed to LLM

    # Output
    answer: str = ""
    sources: list[dict] = field(default_factory=list)
    retrieval_source: str = ""

    # Status flags set by supervisor
    retrieval_done: bool = False
    pageindex_done: bool = False
    generation_done: bool = False
    used_fallback: bool = False

    def log(self, agent: str, step: str, status: str, detail: str = "", latency_ms: float = 0.0) -> None:
        self.trace.append(TraceEntry(
            agent=agent, step=step, status=status,
            detail=detail, latency_ms=latency_ms,
        ))

    def trace_summary(self) -> str:
        lines = [f"[TRACE] trace_id={self.trace_id}  query='{self.query}'"]
        for e in self.trace:
            prefix = "  ✓" if e.status == "ok" else ("  ✗" if e.status == "error" else ("  →" if e.status == "start" else "  ⊘"))
            lines.append(f"{prefix} [{e.agent}] {e.step} — {e.detail} ({e.latency_ms:.0f}ms)")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Message contract: Supervisor → Worker
# ─────────────────────────────────────────────────────────────────
@dataclass
class WorkerInput:
    query: str
    top_k: int
    trace_id: str
    config: dict = field(default_factory=dict)   # worker-specific config
    step: str = ""                               # tên step supervisor đang giao


# ─────────────────────────────────────────────────────────────────
# Message contract: Worker → Supervisor
# ─────────────────────────────────────────────────────────────────
@dataclass
class WorkerOutput:
    worker_id: str
    step: str
    result: Any           # payload cụ thể của từng worker
    trace_id: str
    latency_ms: float = 0.0
    error: str = ""       # "" = success

    @property
    def ok(self) -> bool:
        return self.error == ""
