"""
Supervisor — RAG Multi-Agent Orchestrator.

Topology:
                        ┌─────────────────────────────────┐
                        │           Supervisor             │
                        │  (nhận query, điều phối, trace)  │
                        └──────┬──────────┬───────────────┘
                               │          │
                    ┌──────────▼──┐   ┌───▼────────────┐
                    │  Retrieval  │   │   PageIndex     │
                    │   Worker    │   │    Worker       │
                    │ (hybrid+    │   │ (MCP external   │
                    │  rerank)    │   │  capability)    │
                    └──────┬──────┘   └───┬─────────────┘
                           │              │ (fallback only)
                    ┌──────▼──────────────▼─────────────┐
                    │           Supervisor               │
                    │    merge → select final_chunks     │
                    └──────────────┬────────────────────┘
                                   │
                           ┌───────▼──────┐
                           │  Generation  │
                           │   Worker     │
                           │ (LLM+cite)   │
                           └──────────────┘

Luồng quyết định:
    1. Chạy RetrievalWorker (luôn luôn)
    2. Nếu best_score < threshold → chạy PageIndexWorker (fallback)
       Nếu best_score >= threshold → dùng kết quả hybrid
    3. Chọn final_chunks từ bước 1 hoặc 2
    4. Gửi final_chunks → GenerationWorker
    5. Trả kết quả + in trace

Shared state: RAGState (trace tích lũy qua mọi bước)
Message contracts: WorkerInput / WorkerOutput (xem schema.py)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src.parent))

from .schema import RAGState, WorkerInput
from . import retrieval_worker, pageindex_worker, generation_worker


def run(
    query: str,
    top_k: int = 5,
    use_reranking: bool = True,
    score_threshold: float = 0.3,
    verbose: bool = True,
) -> RAGState:
    """
    Entry point: Supervisor chạy toàn bộ pipeline.

    Args:
        query:            Câu hỏi người dùng
        top_k:            Số chunks cuối cho LLM
        use_reranking:    Có dùng Cohere rerank không
        score_threshold:  Nếu best_score < threshold → fallback PageIndex
        verbose:          In trace summary sau khi chạy

    Returns:
        RAGState đã điền đầy đủ, bao gồm .trace (log đầy đủ)
    """
    state = RAGState(
        query=query,
        top_k=top_k,
        use_reranking=use_reranking,
        score_threshold=score_threshold,
    )
    t_total = time.monotonic()

    if verbose:
        print(f"\n{'='*70}")
        print(f"[SUPERVISOR] trace_id={state.trace_id}")
        print(f"[SUPERVISOR] query='{query}'")
        print(f"[SUPERVISOR] top_k={top_k} reranking={use_reranking} threshold={score_threshold}")
        print(f"{'='*70}")

    state.log("supervisor", "init", "ok",
              detail=f"query='{query}' top_k={top_k} reranking={use_reranking}")

    # ─────────────────────────────────────────────
    # Step 1: Retrieval Worker (hybrid + rerank)
    # ─────────────────────────────────────────────
    state.log("supervisor", "dispatch_retrieval_worker", "start",
              detail="semantic_search + lexical_search + RRF + rerank")
    if verbose:
        print(f"\n[SUPERVISOR] → RetrievalWorker")

    inp1 = WorkerInput(
        query=query,
        top_k=top_k,
        trace_id=state.trace_id,
        config={"use_reranking": use_reranking},
        step="hybrid_retrieval",
    )
    t1 = time.monotonic()
    out1 = retrieval_worker.run(inp1)
    r1_ms = (time.monotonic() - t1) * 1000

    if out1.ok:
        r = out1.result
        state.dense_results = r.get("chunks", [])   # already reranked at this point
        state.reranked_results = r.get("chunks", [])
        timing = r.get("timing", {})
        state.log("retrieval_worker", "hybrid_retrieval", "ok",
                  detail=(f"dense={r.get('dense_count',0)} sparse={r.get('sparse_count',0)} "
                          f"merged={r.get('merged_count',0)} reranked={len(state.reranked_results)} "
                          f"| dense={timing.get('dense_ms',0)}ms "
                          f"sparse={timing.get('sparse_ms',0)}ms "
                          f"rrf={timing.get('rrf_ms',0)}ms "
                          f"rerank={timing.get('rerank_ms',0)}ms"),
                  latency_ms=out1.latency_ms)
        state.retrieval_done = True
        if verbose:
            print(f"  ✓ RetrievalWorker done: {len(state.reranked_results)} chunks in {r1_ms:.0f}ms")
    else:
        state.log("retrieval_worker", "hybrid_retrieval", "error",
                  detail=out1.error, latency_ms=out1.latency_ms)
        if verbose:
            print(f"  ✗ RetrievalWorker error: {out1.error}")

    # ─────────────────────────────────────────────
    # Step 2: Supervisor decides: fallback needed?
    # ─────────────────────────────────────────────
    best_score = state.reranked_results[0]["score"] if state.reranked_results else 0.0
    needs_fallback = (not state.reranked_results) or (best_score < score_threshold)

    if verbose:
        print(f"\n[SUPERVISOR] best_score={best_score:.3f} threshold={score_threshold} "
              f"→ fallback={'YES' if needs_fallback else 'NO'}")

    state.log("supervisor", "routing_decision", "ok",
              detail=(f"best_score={best_score:.3f} threshold={score_threshold} "
                      f"fallback={'yes' if needs_fallback else 'no'}"))

    # ─────────────────────────────────────────────
    # Step 3: PageIndex Worker (fallback / MCP external)
    # ─────────────────────────────────────────────
    if needs_fallback:
        state.log("supervisor", "dispatch_pageindex_worker", "start",
                  detail="MCP external capability — vectorless retrieval")
        if verbose:
            print(f"\n[SUPERVISOR] → PageIndexWorker (MCP external capability)")
            print(f"  tool: {pageindex_worker.TOOL_SPEC['name']}")
            print(f"  description: {pageindex_worker.TOOL_SPEC['description'][:70]}...")

        inp2 = WorkerInput(
            query=query,
            top_k=top_k,
            trace_id=state.trace_id,
            step="pageindex_fallback",
        )
        t2 = time.monotonic()
        out2 = pageindex_worker.run(inp2)
        r2_ms = (time.monotonic() - t2) * 1000

        if out2.ok and out2.result:
            state.pageindex_results = out2.result
            state.used_fallback = True
            state.log("pageindex_worker", "pageindex_fallback", "ok",
                      detail=f"returned={len(state.pageindex_results)} via {out2.result[0].get('source','pageindex')}",
                      latency_ms=out2.latency_ms)
            if verbose:
                print(f"  ✓ PageIndexWorker done: {len(state.pageindex_results)} chunks in {r2_ms:.0f}ms")
        else:
            state.log("pageindex_worker", "pageindex_fallback", "error",
                      detail=out2.error, latency_ms=out2.latency_ms)
            if verbose:
                print(f"  ✗ PageIndexWorker error: {out2.error}")
        state.pageindex_done = True

    # ─────────────────────────────────────────────
    # Step 4: Supervisor selects final chunks
    # ─────────────────────────────────────────────
    if state.used_fallback and state.pageindex_results:
        state.final_chunks = state.pageindex_results[:top_k]
        state.retrieval_source = state.pageindex_results[0].get("source", "pageindex")
    elif state.reranked_results:
        state.final_chunks = state.reranked_results[:top_k]
        state.retrieval_source = "hybrid"
    else:
        state.final_chunks = []
        state.retrieval_source = "none"

    state.log("supervisor", "select_final_chunks", "ok",
              detail=(f"final_chunks={len(state.final_chunks)} "
                      f"source={state.retrieval_source} "
                      f"fallback_used={state.used_fallback}"))
    if verbose:
        print(f"\n[SUPERVISOR] final_chunks={len(state.final_chunks)} "
              f"source={state.retrieval_source}")

    # ─────────────────────────────────────────────
    # Step 5: Generation Worker
    # ─────────────────────────────────────────────
    state.log("supervisor", "dispatch_generation_worker", "start",
              detail=f"chunks={len(state.final_chunks)} → GPT-4o-mini")
    if verbose:
        print(f"\n[SUPERVISOR] → GenerationWorker")

    inp3 = WorkerInput(
        query=query,
        top_k=top_k,
        trace_id=state.trace_id,
        config={"chunks": state.final_chunks},
        step="generate_with_citation",
    )
    t3 = time.monotonic()
    out3 = generation_worker.run(inp3)
    r3_ms = (time.monotonic() - t3) * 1000

    if out3.ok:
        g = out3.result
        state.answer = g.get("answer", "")
        state.sources = g.get("sources", [])
        state.generation_done = True
        timing = g.get("timing", {})
        state.log("generation_worker", "generate_with_citation", "ok",
                  detail=(f"answer_len={len(state.answer)} "
                          f"reorder={timing.get('reorder_ms',0)}ms "
                          f"llm={timing.get('llm_ms',0)}ms"),
                  latency_ms=out3.latency_ms)
        if verbose:
            print(f"  ✓ GenerationWorker done: answer={len(state.answer)} chars in {r3_ms:.0f}ms")
    else:
        state.answer = f"[Generation error: {out3.error}]"
        state.log("generation_worker", "generate_with_citation", "error",
                  detail=out3.error, latency_ms=out3.latency_ms)
        if verbose:
            print(f"  ✗ GenerationWorker error: {out3.error}")

    # ─────────────────────────────────────────────
    # Step 6: Finalize
    # ─────────────────────────────────────────────
    total_ms = (time.monotonic() - t_total) * 1000
    state.log("supervisor", "finalize", "ok",
              detail=f"total={total_ms:.0f}ms fallback={state.used_fallback}",
              latency_ms=total_ms)

    if verbose:
        print(f"\n{'='*70}")
        print(state.trace_summary())
        print(f"{'='*70}")
        print(f"\n[SUPERVISOR] TOTAL: {total_ms:.0f}ms")

    return state
