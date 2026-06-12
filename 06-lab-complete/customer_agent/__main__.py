"""Customer Agent server entry point — port 10100."""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from common.registry_client import register
from customer_agent.agent_executor import CustomerAgentExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [customer_agent] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "10100"))
AGENT_ENDPOINT = f"http://localhost:{PORT}"


async def _register_with_retry(max_attempts: int = 10, delay: float = 2.0) -> None:
    """Retry registration until the registry is up."""
    info = {
        "agent_name": "customer-agent",
        "version": "1.0",
        "description": "Entry-point legal assistant; routes user questions to the Law Agent",
        "tasks": [],  # Customer Agent is an entry point, not discovered by other agents
        "endpoint": AGENT_ENDPOINT,
        "tags": ["customer", "entry-point", "legal-assistant"],
    }
    for attempt in range(1, max_attempts + 1):
        try:
            await register(info)
            logger.info("Registered with registry (attempt %d)", attempt)
            return
        except Exception as exc:
            logger.warning(
                "Registry not ready (attempt %d/%d): %s — retrying in %.0fs",
                attempt, max_attempts, exc, delay,
            )
            await asyncio.sleep(delay)
    logger.error("Failed to register after %d attempts", max_attempts)


async def main() -> None:
    await _register_with_retry()

    agent_card = AgentCard(
        name="Customer Agent",
        description=(
            "Your legal assistant. Ask any legal question — I will route it through "
            "our network of specialist legal, tax, and compliance agents."
        ),
        url=AGENT_ENDPOINT,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="legal_assistant",
                name="Legal Assistant",
                description=(
                    "Answer legal questions by routing them to specialist agents "
                    "covering contract law, tax, and regulatory compliance."
                ),
                tags=["legal", "assistant", "multi-agent"],
            )
        ],
    )

    executor = CustomerAgentExecutor()
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )
    app_builder = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    app = app_builder.build()

    # Serve the agent_interaction_demo.html at "/"
    from fastapi.responses import HTMLResponse
    from pathlib import Path

    for r in list(app.routes):
        if r.path == "/":
            app.routes.remove(r)

    @app.get("/", response_class=HTMLResponse)
    async def serve_demo():
        demo_path = Path("/app/agent_interaction_demo.html")
        if not demo_path.exists():
            demo_path = Path(__file__).resolve().parents[1] / "agent_interaction_demo.html"
        if demo_path.exists():
            return HTMLResponse(content=demo_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>agent_interaction_demo.html not found</h1>", status_code=404)

    # ── Demo Proxy Endpoints ────────────────────────
    from pydantic import BaseModel
    import httpx
    import time
    from uuid import uuid4

    class SendRequest(BaseModel):
        message: str

    SERVICES = {
        "registry":         {"url": "http://localhost:10000", "health": "/health"},
        "customer-agent":   {"url": f"http://localhost:{PORT}", "health": "/.well-known/agent.json"},
        "law-agent":        {"url": "http://localhost:10101", "health": "/.well-known/agent.json"},
        "tax-agent":        {"url": "http://localhost:10102", "health": "/.well-known/agent.json"},
        "compliance-agent": {"url": "http://localhost:10103", "health": "/.well-known/agent.json"},
    }

    @app.get("/api/status", tags=["demo"])
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

    @app.post("/api/demo/send", tags=["demo"])
    async def send_message(req: SendRequest):
        from a2a.client import A2AClient
        from a2a.types import AgentCard, Message, MessageSendParams, Part, Role, SendMessageRequest, TextPart

        trace_id = str(uuid4())
        context_id = str(uuid4())

        # Pass API key header if configured in .env
        api_key = os.getenv("A2A_API_KEY", "").strip()
        headers = {"X-API-Key": api_key} if api_key else {}

        t_start = time.monotonic()
        customer_url = f"http://localhost:{PORT}"
        async with httpx.AsyncClient(timeout=300.0, headers=headers) as http_client:
            try:
                card_resp = await http_client.get(f"{customer_url}/.well-known/agent.json")
                card_resp.raise_for_status()
            except Exception as exc:
                return {"ok": False, "error": f"Cannot reach Customer Agent at {customer_url}: {exc}", "latency": 0}

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
        
        # Helper function to extract text
        text = ""
        res_obj = response
        if hasattr(res_obj, "root"):
            res_obj = res_obj.root
        result = getattr(res_obj, "result", None)
        if result is not None:
            artifacts = getattr(result, "artifacts", None)
            if artifacts:
                for artifact in artifacts:
                    for part in getattr(artifact, "parts", []) or []:
                        inner = getattr(part, "root", part)
                        text += getattr(inner, "text", "") or ""
            if not text:
                for part in getattr(result, "parts", []) or []:
                    inner = getattr(part, "root", part)
                    text += getattr(inner, "text", "") or ""
            if not text:
                for msg in getattr(result, "history", []) or []:
                    for part in getattr(msg, "parts", []) or []:
                        inner = getattr(part, "root", part)
                        text += getattr(inner, "text", "") or ""

        try:
            raw = response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)
        except Exception:
            raw = str(response)

        return {"ok": True, "answer": text, "latency": latency, "trace_id": trace_id, "context_id": context_id, "raw": raw}

    # Challenge 2: API key auth (enabled when A2A_API_KEY is set in .env)
    from common.auth import add_auth_middleware
    add_auth_middleware(app)

    # Challenge 4: /metrics endpoint
    from common.monitoring import add_metrics_endpoint
    add_metrics_endpoint(app, "customer-agent")

    # Production readiness: Health/Readiness, Rate Limiting, Cost Guard, JSON logging
    from common.production_middleware import add_production_middleware
    add_production_middleware(app, "customer-agent")

    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    logger.info("Customer Agent listening on port %d", PORT)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())