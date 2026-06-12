"""
Worker 2 — PageIndexWorker  [External Capability via MCP-style interface].

Trách nhiệm:
    Vectorless retrieval qua PageIndex API (external capability).
    Fallback: BM25 trên standardized markdown files.

MCP interface:
    Worker này mô phỏng pattern Model-Context Protocol (MCP):
    - Nó expose một tool_spec mô tả capability của mình (như MCP tool definition).
    - Supervisor "discover" tool qua tool_spec thay vì biết trực tiếp implementation.
    - Actual execution gọi PageIndex API (external service) hoặc BM25 fallback.
    - Pattern này tương đương với một MCP server expose tool "pageindex_search".

tool_spec format:
    {
        "name": "pageindex_search",
        "description": "Vectorless structural retrieval — không cần embedding",
        "parameters": {"query": str, "top_k": int},
        "external_service": "PageIndex API",
        "fallback": "BM25 local",
    }

Input:  WorkerInput(query, top_k, trace_id)
Output: WorkerOutput(worker_id="pageindex_worker", result=list[dict])
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src.parent))

from .schema import WorkerInput, WorkerOutput


WORKER_ID = "pageindex_worker"

# MCP-style tool spec — supervisor đọc spec này để quyết định có gọi worker không
TOOL_SPEC = {
    "name": "pageindex_search",
    "description": (
        "Vectorless structural retrieval using PageIndex. "
        "Does NOT require a vector database. Uses document structure understanding. "
        "Best for: short queries, structural questions (e.g., 'Điều X quy định gì?'). "
        "Falls back to BM25 if PageIndex API is unavailable."
    ),
    "parameters": {
        "query": {"type": "string", "description": "Câu truy vấn"},
        "top_k": {"type": "integer", "description": "Số kết quả", "default": 5},
    },
    "external_service": "PageIndex API (https://pageindex.io)",
    "fallback": "BM25Okapi on local standardized/ markdown files",
    "when_to_use": "best_hybrid_score < score_threshold OR as parallel fallback",
}


def run(inp: WorkerInput) -> WorkerOutput:
    """
    Gọi PageIndex (external capability qua MCP-style interface) hoặc BM25 fallback.

    PageIndex khác Weaviate:
    - Không cần vector embedding
    - Dùng structural/positional understanding của document
    - External API service (không self-hosted)
    """
    from src.task8_pageindex_vectorless import pageindex_search

    t0 = time.monotonic()
    try:
        results = pageindex_search(inp.query, top_k=inp.top_k)
        source_tag = results[0].get("source", "pageindex") if results else "pageindex"
        latency_ms = (time.monotonic() - t0) * 1000
        detail = f"returned={len(results)} source={source_tag}"
        print(f"  [{WORKER_ID}] pageindex_search: {detail} ({latency_ms:.0f}ms)")
        return WorkerOutput(
            worker_id=WORKER_ID,
            step=inp.step,
            result=results,
            trace_id=inp.trace_id,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        print(f"  [{WORKER_ID}] error: {exc}")
        return WorkerOutput(
            worker_id=WORKER_ID,
            step=inp.step,
            result=[],
            trace_id=inp.trace_id,
            latency_ms=latency_ms,
            error=str(exc),
        )
