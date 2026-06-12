"""
Worker 3 — GenerationWorker.

Trách nhiệm:
    Nhận final_chunks từ Supervisor (đã merged + reranked),
    reorder để tránh lost-in-the-middle,
    format context với source labels,
    gọi OpenAI GPT-4o-mini để generate answer có citation.

Input:  WorkerInput(query, top_k, trace_id, config={"chunks": list[dict]})
Output: WorkerOutput(worker_id="generation_worker", result={"answer", "sources", "retrieval_source"})
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_src = Path(__file__).parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src.parent))

from .schema import WorkerInput, WorkerOutput


WORKER_ID = "generation_worker"


def run(inp: WorkerInput) -> WorkerOutput:
    """
    Generate answer với citation từ chunks đã được Supervisor chuẩn bị.

    Steps:
        1. reorder_for_llm (tránh lost-in-the-middle)
        2. format_context  (thêm source labels)
        3. LLM call        (GPT-4o-mini, temperature=0.3)
    """
    from src.task10_generation import reorder_for_llm, format_context, SYSTEM_PROMPT, TOP_P, TEMPERATURE
    import os

    chunks: list[dict] = inp.config.get("chunks", [])
    t0 = time.monotonic()

    if not chunks:
        latency_ms = (time.monotonic() - t0) * 1000
        return WorkerOutput(
            worker_id=WORKER_ID,
            step=inp.step,
            result={
                "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
                "sources": [],
                "retrieval_source": "none",
            },
            trace_id=inp.trace_id,
            latency_ms=latency_ms,
            error="no_chunks",
        )

    # Step 1: Reorder
    t1 = time.monotonic()
    reordered = reorder_for_llm(chunks)
    reorder_ms = (time.monotonic() - t1) * 1000

    # Step 2: Format context
    t2 = time.monotonic()
    context = format_context(reordered)
    format_ms = (time.monotonic() - t2) * 1000

    # Step 3: LLM call
    user_message = f"Context:\n{context}\n\n---\n\nQuestion: {inp.query}"
    openai_key = os.getenv("OPENAI_API_KEY", "")
    t3 = time.monotonic()

    if not openai_key or openai_key.startswith("sk-xxx"):
        answer = (
            "⚠ OpenAI API key chưa được cấu hình.\n\n"
            "Context đã retrieve:\n\n" + context[:1500]
        )
        llm_ms = 0.0
    else:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
            )
            answer = response.choices[0].message.content
            llm_ms = (time.monotonic() - t3) * 1000
        except Exception as exc:
            answer = f"[LLM error: {exc}]\n\nContext:\n" + context[:1000]
            llm_ms = (time.monotonic() - t3) * 1000

    total_ms = (time.monotonic() - t0) * 1000
    retrieval_source = chunks[0].get("source", "hybrid") if chunks else "none"

    detail = (
        f"chunks={len(chunks)} reorder={reorder_ms:.0f}ms "
        f"format={format_ms:.0f}ms llm={llm_ms:.0f}ms "
        f"answer_len={len(answer)}"
    )
    print(f"  [{WORKER_ID}] {detail}")

    return WorkerOutput(
        worker_id=WORKER_ID,
        step=inp.step,
        result={
            "answer": answer,
            "sources": chunks,
            "retrieval_source": retrieval_source,
            "timing": {
                "reorder_ms": round(reorder_ms),
                "format_ms": round(format_ms),
                "llm_ms": round(llm_ms),
            },
        },
        trace_id=inp.trace_id,
        latency_ms=total_ms,
    )
