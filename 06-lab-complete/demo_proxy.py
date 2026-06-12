"""Thin FastAPI proxy — bridges browser fetch() to Customer Agent A2A SDK calls.

The A2A Python SDK (Pydantic models + A2AClient) cannot run in the browser,
so this proxy translates a simple REST call into a full A2A SDK interaction.

Run:
    python demo_proxy.py          # starts on http://localhost:8765
Then open agent_interaction_demo.html (or visit http://localhost:8765/ to serve it).

Endpoints:
    GET  /               — serve agent_interaction_demo.html
    GET  /api/status     — health-check all 5 services
    POST /api/demo/send  — send question, return structured result
"""
from __future__ import annotations

import logging
import os
import time
from uuid import uuid4

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [proxy] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CUSTOMER_URL = os.getenv("CUSTOMER_AGENT_URL", "http://localhost:10100")

SERVICES = {
    "registry":         {"url": "http://localhost:10000", "health": "/health"},
    "customer-agent":   {"url": "http://localhost:10100", "health": "/.well-known/agent.json"},
    "law-agent":        {"url": "http://localhost:10101", "health": "/.well-known/agent.json"},
    "tax-agent":        {"url": "http://localhost:10102", "health": "/.well-known/agent.json"},
    "compliance-agent": {"url": "http://localhost:10103", "health": "/.well-known/agent.json"},
}

app = FastAPI(title="A2A Demo Proxy", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SendRequest(BaseModel):
    message: str


@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "agent_interaction_demo.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return JSONResponse({"error": "agent_interaction_demo.html not found"}, status_code=404)


@app.get("/api/status")
async def status():
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, cfg in SERVICES.items():
            try:
                resp = await client.get(cfg["url"] + cfg["health"])
                results[name] = {"ok": resp.status_code < 400, "code": resp.status_code, "url": cfg["url"]}
            except Exception as exc:
                results[name] = {"ok": False, "code": None, "url": cfg["url"], "error": str(exc)[:80]}
    return results


@app.post("/api/demo/send")
async def send_message(req: SendRequest):
    from a2a.client import A2AClient
    from a2a.types import AgentCard, Message, MessageSendParams, Part, Role, SendMessageRequest, TextPart

    trace_id = str(uuid4())
    context_id = str(uuid4())

    # Pass API key header if configured in .env
    api_key = os.getenv("A2A_API_KEY", "").strip()
    headers = {"X-API-Key": api_key} if api_key else {}

    t_start = time.monotonic()
    async with httpx.AsyncClient(timeout=300.0, headers=headers) as http_client:
        try:
            card_resp = await http_client.get(f"{CUSTOMER_URL}/.well-known/agent.json")
            card_resp.raise_for_status()
        except Exception as exc:
            return {"ok": False, "error": f"Cannot reach Customer Agent at {CUSTOMER_URL}: {exc}", "latency": 0}

        agent_card = AgentCard.model_validate(card_resp.json())
        client = A2AClient(httpx_client=http_client, agent_card=agent_card)

        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=req.message))],
            message_id=str(uuid4()),
            context_id=context_id,
            metadata={"trace_id": trace_id, "context_id": context_id, "delegation_depth": 0},
        )
        request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(message=message))

        try:
            response = await client.send_message(request)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "latency": round(time.monotonic() - t_start, 2)}

    latency = round(time.monotonic() - t_start, 2)
    answer = _extract_text(response)

    try:
        raw = response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)
    except Exception:
        raw = str(response)

    logger.info("Request completed | trace=%s latency=%.2fs ans_len=%d", trace_id, latency, len(answer))
    return {"ok": True, "answer": answer, "latency": latency, "trace_id": trace_id, "context_id": context_id, "raw": raw}


def _extract_text(response: object) -> str:
    """Mirrors logic in common/a2a_client.py _extract_text."""
    text = ""
    if hasattr(response, "root"):
        response = response.root
    result = getattr(response, "result", None)
    if result is None:
        return text
    artifacts = getattr(result, "artifacts", None)
    if artifacts:
        for artifact in artifacts:
            for part in getattr(artifact, "parts", []) or []:
                inner = getattr(part, "root", part)
                text += getattr(inner, "text", "") or ""
        if text:
            return text
    for part in getattr(result, "parts", []) or []:
        inner = getattr(part, "root", part)
        text += getattr(inner, "text", "") or ""
    if not text:
        for msg in getattr(result, "history", []) or []:
            for part in getattr(msg, "parts", []) or []:
                inner = getattr(part, "root", part)
                text += getattr(inner, "text", "") or ""
    return text


if __name__ == "__main__":
    logger.info("Demo proxy starting on http://localhost:8765")
    logger.info("Open http://localhost:8765 or agent_interaction_demo.html directly")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
