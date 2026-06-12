"""API key authentication middleware for A2A agent FastAPI apps (Challenge 2).

Usage in any agent __main__.py:
    app = app_builder.build()
    add_auth_middleware(app)

Configuration:
    Set A2A_API_KEY=<secret> in .env to enable authentication.
    Leave A2A_API_KEY empty (or unset) to run in open/dev mode.

Clients must send:  X-API-Key: <secret>
The agent card endpoint and /metrics are always public (no auth required).
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

API_KEY_HEADER = "X-API-Key"

# Paths that are always accessible without authentication
_PUBLIC_PATHS = frozenset({
    "/.well-known/agent.json",
    "/health",
    "/",
    "/metrics",
})


def add_auth_middleware(app: FastAPI) -> None:
    """Attach API key middleware to app if A2A_API_KEY is configured."""
    api_key = os.getenv("A2A_API_KEY", "").strip()
    if not api_key:
        return  # Auth disabled — safe for local dev/demo

    @app.middleware("http")
    async def verify_api_key(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS or request.url.path.startswith("/dashboard"):
            return await call_next(request)

        provided = request.headers.get(API_KEY_HEADER, "")
        if provided != api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "detail": f"Provide a valid API key in the '{API_KEY_HEADER}' header.",
                },
            )
        return await call_next(request)
