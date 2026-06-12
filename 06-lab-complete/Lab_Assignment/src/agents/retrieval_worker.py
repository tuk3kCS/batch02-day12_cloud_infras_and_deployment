"""
Worker 1 — RetrievalWorker.

Trách nhiệm:
    Dense retrieval (Cohere + Weaviate near_vector)
    + Sparse retrieval (Weaviate BM25)
    + RRF merge
    + Cohere/Jina reranking

Input:  WorkerInput(query, top_k, trace_id)
Output: WorkerOutput(worker_id="retrieval_worker", result=list[dict])

Không biết gì về Supervisor hay các worker khác.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure parent src/ is importable when run directly
_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src.parent))

from .schema import WorkerInput, WorkerOutput


WORKER_ID = "retrieval_worker"


def run(inp: WorkerInput) -> WorkerOutput:
    """
    Chạy hybrid retrieval pipeline.

    Steps:
        1. semantic_search  (dense)
        2. lexical_search   (sparse BM25)
        3. rerank_rrf       (merge)
        4. rerank           (cross-encoder, optional)

    Returns list[dict] với keys: content, score, metadata, source
    """
    from src.task5_semantic_search import semantic_search
    from src.task6_lexical_search import lexical_search
    from src.task7_reranking import rerank, rerank_rrf

    top_k = inp.top_k
    fetch_k = top_k * 3
    t0 = time.monotonic()

    # Step 1: Dense
    t1 = time.monotonic()
    try:
        dense = semantic_search(inp.query, top_k=fetch_k)
    except Exception as exc:
        dense = []
        print(f"  [{WORKER_ID}] semantic_search error: {exc}")
    dense_ms = (time.monotonic() - t1) * 1000

    # Step 2: Sparse
    t2 = time.monotonic()
    try:
        sparse = lexical_search(inp.query, top_k=fetch_k)
    except Exception as exc:
        sparse = []
        print(f"  [{WORKER_ID}] lexical_search error: {exc}")
    sparse_ms = (time.monotonic() - t2) * 1000

    # Step 3: RRF merge
    t3 = time.monotonic()
    lists = [l for l in [dense, sparse] if l]
    if lists:
        merged = rerank_rrf(lists, top_k=fetch_k)
        for item in merged:
            item["source"] = "hybrid"
    else:
        merged = []
    rrf_ms = (time.monotonic() - t3) * 1000

    # Step 4: Rerank
    use_reranking = inp.config.get("use_reranking", True)
    t4 = time.monotonic()
    if use_reranking and merged:
        try:
            reranked = rerank(inp.query, merged, top_k=top_k, method="cross_encoder")
        except Exception as exc:
            print(f"  [{WORKER_ID}] rerank error: {exc}")
            reranked = merged[:top_k]
    else:
        reranked = merged[:top_k]
    rerank_ms = (time.monotonic() - t4) * 1000

    total_ms = (time.monotonic() - t0) * 1000

    # Annotate timing in result metadata
    result = {
        "chunks": reranked,
        "dense_count": len(dense),
        "sparse_count": len(sparse),
        "merged_count": len(merged),
        "timing": {
            "dense_ms": round(dense_ms),
            "sparse_ms": round(sparse_ms),
            "rrf_ms": round(rrf_ms),
            "rerank_ms": round(rerank_ms),
        },
    }

    detail = (
        f"dense={len(dense)} sparse={len(sparse)} merged={len(merged)} "
        f"reranked={len(reranked)} | "
        f"dense={dense_ms:.0f}ms sparse={sparse_ms:.0f}ms "
        f"rrf={rrf_ms:.0f}ms rerank={rerank_ms:.0f}ms"
    )

    print(f"  [{WORKER_ID}] {detail}")

    return WorkerOutput(
        worker_id=WORKER_ID,
        step=inp.step,
        result=result,
        trace_id=inp.trace_id,
        latency_ms=total_ms,
    )
