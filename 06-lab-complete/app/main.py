"""
Production AI Agent - final codelab project.

This app combines the Day 12 production requirements:
- Environment-based config
- API key authentication
- Redis-backed conversation history, rate limiting, and budget tracking
- Health/readiness probes
- Graceful shutdown
- Structured JSON logging
"""
import json
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import redis
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

from app.config import settings


START_TIME = time.time()
INSTANCE_ID = settings.instance_id or f"agent-{uuid.uuid4().hex[:8]}"
HISTORY_TTL_SECONDS = 30 * 24 * 60 * 60
RATE_WINDOW_SECONDS = 60
ESTIMATED_COST_USD = 0.01

_is_ready = False
_request_count = 0
_error_count = 0
_redis: redis.Redis | None = None


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("agent")
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(settings.log_level)
logger.propagate = False


def get_redis() -> redis.Redis:
    if _redis is None:
        raise HTTPException(status_code=503, detail="Redis is not connected")
    return _redis


def mock_llm(question: str, history: list[dict[str, str]]) -> str:
    turn_count = len([item for item in history if item.get("role") == "user"])
    return (
        f"Mock answer for: {question}. "
        f"I can see {turn_count} previous user message(s) in this Redis-backed conversation."
    )


def month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def log_event(event: str, **fields: Any) -> None:
    logger.info(json.dumps({"event": event, "instance": INSTANCE_ID, **fields}))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready, _redis
    try:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
        _redis.ping()
        _is_ready = True
        log_event("startup", redis="connected", environment=settings.environment)
    except Exception as exc:
        _redis = None
        _is_ready = False
        log_event("startup_failed", error=str(exc))

    yield

    _is_ready = False
    if _redis is not None:
        _redis.close()
    log_event("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-User-ID"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    started = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        log_event(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.time() - started) * 1000, 2),
        )
        return response
    except Exception:
        _error_count += 1
        raise


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
    api_key: str = Security(api_key_header),
    x_user_id: str | None = Header(default=None),
) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_user_id or settings.default_user_id


def check_rate_limit(user_id: str = Depends(verify_api_key)) -> None:
    r = get_redis()
    now = time.time()
    key = f"rate_limit:{user_id}"
    r.zremrangebyscore(key, 0, now - RATE_WINDOW_SECONDS)
    current = r.zcard(key)
    if current >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} requests/minute",
            headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
        )
    r.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
    r.expire(key, RATE_WINDOW_SECONDS)


def check_budget(user_id: str = Depends(verify_api_key)) -> None:
    r = get_redis()
    key = f"budget:{user_id}:{month_key()}"
    current = float(r.get(key) or 0)
    if current + ESTIMATED_COST_USD > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "current_usd": round(current, 4),
                "budget_usd": settings.monthly_budget_usd,
            },
        )
    r.incrbyfloat(key, ESTIMATED_COST_USD)
    r.expire(key, 32 * 24 * 60 * 60)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=120)


class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    model: str
    served_by: str
    timestamp: str


def load_history(r: redis.Redis, session_id: str) -> list[dict[str, str]]:
    raw_messages = r.lrange(f"history:{session_id}", 0, -1)
    return [json.loads(item) for item in raw_messages]


def append_history(r: redis.Redis, session_id: str, role: str, content: str) -> None:
    key = f"history:{session_id}"
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(key, json.dumps(message))
    r.ltrim(key, -20, -1)
    r.expire(key, HISTORY_TTL_SECONDS)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": INSTANCE_ID,
        "endpoints": ["/ask", "/health", "/ready", "/metrics"],
    }


@app.post("/ask", response_model=AskResponse)
def ask_agent(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget),
):
    r = get_redis()
    session_id = body.session_id or f"{user_id}:{uuid.uuid4().hex}"
    history = load_history(r, session_id)
    append_history(r, session_id, "user", body.question)
    answer = mock_llm(body.question, history)
    append_history(r, session_id, "assistant", answer)
    log_event("agent_answered", user_id=user_id, session_id=session_id)
    return AskResponse(
        session_id=session_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        served_by=INSTANCE_ID,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{session_id}")
def get_history(session_id: str, _user_id: str = Depends(verify_api_key)):
    r = get_redis()
    return {"session_id": session_id, "messages": load_history(r, session_id)}


@app.delete("/history/{session_id}")
def delete_history(session_id: str, _user_id: str = Depends(verify_api_key)):
    r = get_redis()
    r.delete(f"history:{session_id}")
    return {"deleted": session_id}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "instance": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Application is not ready")
    try:
        get_redis().ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return {"status": "ready", "redis": "ok", "instance": INSTANCE_ID}


@app.get("/metrics")
def metrics(_user_id: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "instance": INSTANCE_ID,
    }


def _handle_signal(signum, _frame):
    global _is_ready
    _is_ready = False
    log_event("SIGTERM", signum=signum)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
