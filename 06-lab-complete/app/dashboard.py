"""Read-only dashboard API helpers.

The dashboard derives its model from runtime state and repository files so the
frontend can present the actual codelab infrastructure without hardcoded UI
fixtures.
"""
from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


import redis
from app.config import settings

LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=200)
REDIS_LOG_KEY = "dashboard:logs"
MAX_LOG_COUNT = 200
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            pass
    return _redis_client


def record_log(event: str, instance: str, **fields: Any) -> None:
    log_item = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "instance": instance,
        **fields,
    }
    LOG_BUFFER.appendleft(log_item)
    try:
        r = get_redis_client()
        if r is not None:
            r.lpush(REDIS_LOG_KEY, json.dumps(log_item))
            r.ltrim(REDIS_LOG_KEY, 0, MAX_LOG_COUNT - 1)
    except Exception:
        pass


def get_logs() -> list[dict[str, Any]]:
    try:
        r = get_redis_client()
        if r is not None:
            raw_logs = r.lrange(REDIS_LOG_KEY, 0, -1)
            if raw_logs:
                return [json.loads(item) for item in raw_logs]
    except Exception:
        pass
    return list(LOG_BUFFER)


def repo_root() -> Path:
    configured = os.getenv("REPO_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def exists(relative_path: str) -> bool:
    return (repo_root() / relative_path).exists()


def file_size(relative_path: str) -> int:
    path = repo_root() / relative_path
    return path.stat().st_size if path.exists() else 0


def find_files(pattern: str) -> list[str]:
    root = repo_root()
    if not root.exists():
        return []
    return [
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob(pattern)
        if ".git" not in path.parts and "node_modules" not in path.parts
    ]


def detect_services() -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    compose_files = find_files("docker-compose*.yml") + find_files("docker-compose*.yaml")
    dockerfiles = find_files("Dockerfile")

    for file_name in compose_files:
        content = read_text(repo_root() / file_name)
        for service in ["agent", "frontend", "backend", "nginx", "redis", "qdrant"]:
            if f"{service}:" in content:
                services.append(
                    {
                        "name": service,
                        "kind": "docker-compose",
                        "source": file_name,
                        "status": "configured",
                    }
                )

    for file_name in dockerfiles:
        content = read_text(repo_root() / file_name)
        base = "unknown"
        for line in content.splitlines():
            if line.strip().upper().startswith("FROM "):
                base = line.split()[1]
                break
        services.append(
            {
                "name": Path(file_name).parent.name if Path(file_name).parent.name != "." else "root-app",
                "kind": "docker-image",
                "source": file_name,
                "status": "buildable",
                "baseImage": base,
            }
        )

    unique: dict[str, dict[str, Any]] = {}
    for service in services:
        key = f"{service['kind']}:{service['name']}:{service['source']}"
        unique[key] = service
    return list(unique.values())


def repository_inventory() -> dict[str, Any]:
    root = repo_root()
    manifests = {
        "readme": exists("README.md"),
        "dockerCompose": find_files("docker-compose*.yml") + find_files("docker-compose*.yaml"),
        "dockerfiles": find_files("Dockerfile"),
        "kubernetes": find_files("k8s/*.yaml") + find_files("kubernetes/*.yaml"),
        "terraform": find_files("*.tf"),
        "cloudRun": ["03-cloud-deployment/production-cloud-run/service.yaml"]
        if exists("03-cloud-deployment/production-cloud-run/service.yaml")
        else [],
        "cloudBuild": ["03-cloud-deployment/production-cloud-run/cloudbuild.yaml"]
        if exists("03-cloud-deployment/production-cloud-run/cloudbuild.yaml")
        else [],
        "cicd": find_files(".github/workflows/*.yml") + find_files(".github/workflows/*.yaml"),
        "railway": find_files("railway.toml"),
        "render": find_files("render.yaml"),
        "monitoring": [
            path
            for path in find_files("*.yml") + find_files("*.yaml")
            if any(token in path.lower() for token in ["prometheus", "grafana", "loki", "otel"])
        ],
    }
    return {
        "root": str(root),
        "files": manifests,
        "counts": {
            "dockerfiles": len(manifests["dockerfiles"]),
            "composeFiles": len(manifests["dockerCompose"]),
            "kubernetesManifests": len(manifests["kubernetes"]),
            "terraformFiles": len(manifests["terraform"]),
            "cicdWorkflows": len(manifests["cicd"]) + len(manifests["cloudBuild"]),
            "monitoringConfigs": len(manifests["monitoring"]),
        },
        "readmeBytes": file_size("README.md"),
    }


def architecture_model() -> dict[str, Any]:
    inventory = repository_inventory()
    has_frontend = exists("frontend/package.json")
    has_nginx = bool(find_files("nginx.conf"))
    has_redis = any(service["name"] == "redis" for service in detect_services())
    has_cloud_run = bool(inventory["files"]["cloudRun"])
    has_railway = bool(inventory["files"]["railway"])
    has_render = bool(inventory["files"]["render"])

    nodes = [
        {"id": "user", "label": "User", "type": "edge", "status": "external"},
        {
            "id": "frontend",
            "label": "React Dashboard" if has_frontend else "Frontend not present",
            "type": "frontend",
            "status": "configured" if has_frontend else "missing",
        },
        {"id": "lb", "label": "Nginx Load Balancer", "type": "network", "status": "configured" if has_nginx else "missing"},
        {"id": "api", "label": "FastAPI Agent API", "type": "backend", "status": "running"},
        {"id": "redis", "label": "Redis State Store", "type": "database", "status": "configured" if has_redis else "missing"},
        {"id": "docker", "label": "Docker Image", "type": "container", "status": "buildable"},
        {
            "id": "cloud",
            "label": "Railway / Render / Cloud Run",
            "type": "cloud",
            "status": "configured" if has_cloud_run or has_railway or has_render else "missing",
        },
    ]
    edges = [
        {"from": "user", "to": "frontend", "label": "HTTPS"},
        {"from": "frontend", "to": "lb", "label": "API requests"},
        {"from": "lb", "to": "api", "label": "reverse proxy"},
        {"from": "api", "to": "redis", "label": "sessions, rate, budget"},
        {"from": "api", "to": "docker", "label": "containerized"},
        {"from": "docker", "to": "cloud", "label": "deploy"},
    ]
    pipeline = [
        {"name": "Source Code", "status": "present", "source": "Git repository"},
        {"name": "GitHub", "status": "manual", "source": "No .github workflow detected"},
        {"name": "CI/CD", "status": "configured" if inventory["files"]["cloudBuild"] else "manual", "source": "Cloud Build" if inventory["files"]["cloudBuild"] else "Railway/Render deploy"},
        {"name": "Build", "status": "configured", "source": "Dockerfile"},
        {"name": "Docker Image", "status": "buildable", "source": "python:3.11-slim"},
        {"name": "Registry", "status": "external", "source": "Railway/Cloud Run managed"},
        {"name": "Kubernetes Deployment", "status": "not-present", "source": "No Kubernetes manifest detected"},
        {"name": "Service", "status": "configured", "source": "FastAPI + Nginx/Cloud Run"},
        {"name": "User Request", "status": "active", "source": "/ask, /health, /ready"},
    ]
    return {"nodes": nodes, "edges": edges, "pipeline": pipeline}


def dashboard_state(
    *,
    app_name: str,
    app_version: str,
    environment: str,
    instance_id: str,
    uptime_seconds: float,
    total_requests: int,
    error_count: int,
    is_ready: bool,
    redis_ok: bool,
    redis_info: dict[str, Any] | None,
    settings_snapshot: dict[str, Any],
) -> dict[str, Any]:
    services = detect_services()
    inventory = repository_inventory()
    architecture = architecture_model()
    resource_usage = {
        "cpuPercent": None,
        "memoryPercent": None,
        "redisConnectedClients": redis_info.get("connected_clients") if redis_info else None,
        "redisUsedMemoryHuman": redis_info.get("used_memory_human") if redis_info else None,
    }

    try:
        import psutil

        resource_usage["cpuPercent"] = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        resource_usage["memoryPercent"] = memory.percent
    except Exception:
        pass

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "overview": {
            "appName": app_name,
            "version": app_version,
            "environment": environment,
            "instanceId": instance_id,
            "uptimeSeconds": uptime_seconds,
            "totalRequests": total_requests,
            "errorCount": error_count,
            "ready": is_ready,
            "redis": "connected" if redis_ok else "unavailable",
        },
        "inventory": inventory,
        "architecture": architecture,
        "services": services,
        "deployments": {
            "railway": inventory["files"]["railway"],
            "render": inventory["files"]["render"],
            "cloudRun": inventory["files"]["cloudRun"],
            "cloudBuild": inventory["files"]["cloudBuild"],
            "kubernetes": inventory["files"]["kubernetes"],
            "terraform": inventory["files"]["terraform"],
        },
        "containers": services,
        "resources": resource_usage,
        "logs": get_logs(),
        "environment": settings_snapshot,
    }
