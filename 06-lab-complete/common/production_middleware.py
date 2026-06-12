"""Production readiness middleware (JSON logging, Redis Rate Limiting, Cost Guard, Health/Readiness checks)."""
from __future__ import annotations

import os
import time
import logging
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

logger = logging.getLogger("production_middleware")

# 1. Structured JSON logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# 2. Redis client connection
redis_client = None
redis_url = os.getenv("REDIS_URL", "").strip()
if redis_url:
    try:
        redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        logger.info("Connected to Redis at %s", redis_url)
    except Exception as e:
        logger.error("Failed to initialize Redis client: %s", e)

# 3. Rate Limiter configurations
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

# 4. Cost Guard configurations
MONTHLY_BUDGET_USD = float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
COST_PER_REQUEST = 0.002  # Flat rate of $0.002 per request for budget tracking

async def check_rate_limit(user_id: str) -> bool:
    """Returns True if request is allowed, False if rate limit is exceeded."""
    if not redis_client:
        return True  # Fallback to allow if Redis is not configured
    
    current_minute = int(time.time() / 60)
    key = f"rate:{user_id}:{current_minute}"
    
    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 60)
            res = await pipe.execute()
            count = res[0]
            if count > RATE_LIMIT_PER_MINUTE:
                return False
    except Exception as e:
        logger.error("Rate limiter error: %s", e)
    return True

async def check_cost_guard(user_id: str) -> bool:
    """Returns True if request is allowed under budget, False if budget is exceeded."""
    if not redis_client:
        return True  # Fallback to allow if Redis is not configured
        
    current_month = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{current_month}"
    
    try:
        current_spent = await redis_client.get(key)
        spent = float(current_spent) if current_spent else 0.0
        
        if spent + COST_PER_REQUEST > MONTHLY_BUDGET_USD:
            return False
            
        # Increment monthly spent
        await redis_client.set(key, spent + COST_PER_REQUEST)
    except Exception as e:
        logger.error("Cost guard error: %s", e)
    return True

def add_production_middleware(app: FastAPI, agent_name: str) -> None:
    """Registers health/readiness endpoints, dashboard state, and HTTP middleware."""
    # Setup JSON logging
    setup_logging()

    start_time = time.time()
    
    # Expose health check
    @app.get("/health", tags=["observability"])
    async def health():
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - start_time, 1),
            "version": "1.0.0",
            "agent": agent_name
        }
        
    # Expose readiness check
    @app.get("/ready", tags=["observability"])
    async def ready():
        if redis_url and not redis_client:
            return JSONResponse(status_code=503, content={"status": "error", "message": "Redis client not initialized"})
        if redis_client:
            try:
                await redis_client.ping()
            except Exception as e:
                return JSONResponse(status_code=503, content={"status": "error", "message": f"Redis connection check failed: {e}"})
        return {"ready": True}

    # Dashboard State Endpoint
    @app.get("/dashboard/state", tags=["dashboard"])
    async def get_dashboard_state():
        from common.dashboard import dashboard_state
        from common.monitoring import metrics
        
        # Check Redis connection
        redis_ok = False
        redis_info = None
        if redis_client:
            try:
                await redis_client.ping()
                redis_ok = True
                redis_info = {
                    "connected_clients": 1,
                    "used_memory_human": "unknown"
                }
            except Exception:
                redis_ok = False
                
        snap = metrics.snapshot()
        total_reqs = sum(m.get("requests_total", 0) for m in snap.values())
        total_errs = sum(m.get("errors_total", 0) for m in snap.values())
        
        settings_snapshot = {
            "host": "0.0.0.0",
            "port": int(os.getenv("PORT", "10100")),
            "environment": os.getenv("ENVIRONMENT", "production"),
            "debug": False,
            "logLevel": os.getenv("LOG_LEVEL", "INFO"),
            "rateLimitPerMinute": RATE_LIMIT_PER_MINUTE,
            "monthlyBudgetUsd": MONTHLY_BUDGET_USD,
            "redisConfigured": bool(redis_url),
            "openAIConfigured": bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
        }
        
        worker_requests = {agent: m.get("requests_total", 0) for agent, m in snap.items()}
        
        return dashboard_state(
            app_name="Legal Multi-Agent System",
            app_version="1.0.0",
            environment=os.getenv("ENVIRONMENT", "production"),
            instance_id=agent_name,
            uptime_seconds=round(time.time() - start_time, 1),
            total_requests=total_reqs,
            error_count=total_errs,
            is_ready=True,
            redis_ok=redis_ok,
            redis_info=redis_info,
            settings_snapshot=settings_snapshot,
            worker_requests=worker_requests
        )

    # Mount static dashboard files if they exist
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    
    frontend_dist = Path("/app/frontend-dist")
    if not frontend_dist.exists():
        frontend_dist = Path(__file__).resolve().parents[2] / "frontend-dist"
        
    if frontend_dist.exists():
        app.mount("/dashboard", StaticFiles(directory=str(frontend_dist), html=True), name="dashboard")
        logger.info("Mounted frontend dashboard from %s", frontend_dist)

    # Attach middleware to intercept A2A API calls
    @app.middleware("http")
    async def production_middleware(request: Request, call_next):
        # Exclude public endpoints from rate limiting and cost guard
        public_paths = {"/health", "/ready", "/metrics", "/.well-known/agent.json", "/"}
        if request.url.path in public_paths or request.url.path.startswith("/dashboard"):
            return await call_next(request)
            
        # Identify User
        api_key = request.headers.get("X-API-Key", "")
        user_id = api_key if api_key else (request.client.host if request.client else "unknown")
        
        # Check Rate Limit
        if not await check_rate_limit(user_id):
            logger.warning("Rate limit exceeded for user '%s'", user_id)
            return JSONResponse(
                status_code=429,
                content={"error": "Too Many Requests", "detail": "Rate limit exceeded. Try again in a minute."}
            )
            
        # Check Cost Guard
        if not await check_cost_guard(user_id):
            logger.warning("Cost budget exceeded for user '%s'", user_id)
            return JSONResponse(
                status_code=402,
                content={"error": "Payment Required", "detail": "Monthly cost budget limit exceeded."}
            )
            
        return await call_next(request)
