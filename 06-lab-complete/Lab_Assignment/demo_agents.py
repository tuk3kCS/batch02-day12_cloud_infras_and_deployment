"""
Demo: Multi-Agent RAG System (Day 08 refactored).

Chạy:
    cd Day08_RAG_pipeline_cohort2
    python demo_agents.py

Yêu cầu:
    - Docker Weaviate đang chạy (docker compose up -d)
    - .env có COHERE_API_KEY (embedding + rerank)
    - .env có OPENAI_API_KEY (generation, optional — nếu thiếu vẫn in retrieved chunks)
    - Data đã được index (chạy python -m src.task4_chunking_indexing một lần)

Demo thực hiện 6 yêu cầu:
    1. Tách artifact Day 08 thành Supervisor + 3 Workers
    2. Shared state schema với trường trace
    3. PageIndexWorker dùng external capability qua MCP-style interface
    4. Message contract WorkerInput / WorkerOutput
    5. Trace toàn bộ luồng
    6. Demo kết quả cuối cùng kèm reasoning flow
"""

import os
import sys
from pathlib import Path

# Ensure project root and src/ are on path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.agents import supervisor
from src.agents.pageindex_worker import TOOL_SPEC


def print_section(title: str) -> None:
    print(f"\n{'━'*70}")
    print(f"  {title}")
    print(f"{'━'*70}")


def demo_architecture() -> None:
    """Yêu cầu 1–4: In thiết kế kiến trúc + message contracts."""
    print_section("1. Kiến trúc: Supervisor + 3 Workers")
    print("""
  Supervisor (src/agents/supervisor.py)
  ├── Worker 1: RetrievalWorker   — hybrid search (dense + BM25 + RRF + rerank)
  ├── Worker 2: PageIndexWorker  — external capability qua MCP-style interface
  └── Worker 3: GenerationWorker — LLM generation với citation

  Topology (runtime):
    Query → Supervisor
              ├→ [luôn luôn] RetrievalWorker → dense+sparse+RRF+rerank → chunks
              ├→ [nếu score < 0.3] PageIndexWorker → vectorless BM25 → fallback chunks
              └→ GenerationWorker(final_chunks) → answer + citations
""")

    print_section("2. Shared State Schema (src/agents/schema.py)")
    print("""
  RAGState:
    query, top_k, use_reranking, score_threshold    ← inputs
    trace_id: str                                   ← UUID mỗi request
    trace: list[TraceEntry]                         ← LOG đầy đủ mọi bước
      └─ TraceEntry: agent, step, status, detail, latency_ms, timestamp
    dense_results, sparse_results, merged_results   ← intermediate
    reranked_results, pageindex_results             ← intermediate
    final_chunks                                    ← chunks gửi LLM
    answer, sources, retrieval_source               ← output
    retrieval_done, pageindex_done, generation_done ← status flags
""")

    print_section("3. MCP External Capability (PageIndexWorker)")
    print("  TOOL_SPEC (giống MCP tool definition):")
    for k, v in TOOL_SPEC.items():
        print(f"    {k}: {v}")

    print_section("4. Message Contracts")
    print("""
  Supervisor → Worker:  WorkerInput
    - query: str
    - top_k: int
    - trace_id: str
    - config: dict        ← worker-specific (e.g. {"chunks": [...], "use_reranking": True})
    - step: str           ← tên bước ("hybrid_retrieval", "pageindex_fallback", ...)

  Worker → Supervisor:  WorkerOutput
    - worker_id: str      ← "retrieval_worker" | "pageindex_worker" | "generation_worker"
    - step: str
    - result: Any         ← payload cụ thể của từng worker
    - trace_id: str       ← propagated từ input
    - latency_ms: float
    - error: str          ← "" nếu success
    - ok: bool            ← property = (error == "")
""")


def demo_run(query: str, score_threshold: float = 0.3) -> None:
    """Yêu cầu 5–6: Chạy thật, trace + demo kết quả."""
    print_section(f"5 & 6. Demo Live — Query: '{query}'")

    state = supervisor.run(
        query=query,
        top_k=5,
        use_reranking=True,
        score_threshold=score_threshold,
        verbose=True,
    )

    # Final answer
    print_section("FINAL ANSWER")
    print(state.answer[:1200])
    if len(state.answer) > 1200:
        print(f"  ... [{len(state.answer) - 1200} chars truncated]")

    # Sources
    print_section("SOURCES (retrieved chunks)")
    for i, chunk in enumerate(state.final_chunks[:3], 1):
        meta = chunk.get("metadata", {})
        print(f"  [{i}] score={chunk.get('score',0):.4f} "
              f"source={meta.get('source','?')} "
              f"type={meta.get('type','?')}")
        print(f"      {chunk['content'][:100]}...")

    # Trace summary
    print_section("REASONING FLOW (Trace Log)")
    print(state.trace_summary())

    # Stats
    print_section("STATS")
    total_ms = sum(e.latency_ms for e in state.trace if e.agent == "supervisor" and e.step == "finalize")
    print(f"  trace_id:         {state.trace_id}")
    print(f"  total_steps:      {len(state.trace)}")
    print(f"  retrieval_source: {state.retrieval_source}")
    print(f"  fallback_used:    {state.used_fallback}")
    print(f"  final_chunks:     {len(state.final_chunks)}")
    print(f"  answer_length:    {len(state.answer)} chars")
    if total_ms:
        print(f"  total_latency:    {total_ms:.0f}ms")

    return state


def main() -> None:
    demo_architecture()

    queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý theo pháp luật Việt Nam?",
        "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?",
    ]

    print(f"\n\n{'#'*70}")
    print(f"  CHẠY {len(queries)} QUERIES")
    print(f"{'#'*70}")

    for i, q in enumerate(queries, 1):
        print(f"\n\n{'>'*70}")
        print(f"  Query {i}/{len(queries)}")
        print(f"{'>'*70}")
        try:
            demo_run(q)
        except Exception as exc:
            print(f"\n[ERROR] {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n\n{'='*70}")
    print("  Demo hoàn thành. Xem src/agents/ để đọc implementation.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
