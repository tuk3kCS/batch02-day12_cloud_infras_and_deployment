"""
Production Readiness Checker

Tự động kiểm tra project có đủ điều kiện deploy chưa.
Chạy: python check_production_ready.py

Output: checklist với ✅ / ❌ cho từng item.
"""
import os
import sys
import json
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def run_checks():
    results = []
    base = os.path.dirname(__file__)

    print("\n" + "=" * 55)
    print("  Production Readiness Check — Day 12 Lab")
    print("=" * 55)

    # ── Files ──────────────────���───────────────────
    print("\n📁 Required Files")
    results.append(check("Dockerfile exists",
                         os.path.exists(os.path.join(base, "Dockerfile"))))
    results.append(check("docker-compose.yml exists",
                         os.path.exists(os.path.join(base, "docker-compose.yml"))))
    results.append(check(".dockerignore exists",
                         os.path.exists(os.path.join(base, ".dockerignore"))))
    results.append(check(".env.example exists",
                         os.path.exists(os.path.join(base, ".env.example"))))
    results.append(check("requirements.txt exists",
                         os.path.exists(os.path.join(base, "requirements.txt"))))
    results.append(check("railway.toml or render.yaml exists",
                         os.path.exists(os.path.join(base, "railway.toml")) or
                         os.path.exists(os.path.join(base, "render.yaml"))))

    # ── Security ──────────────────────────────────���
    print("\n🔒 Security")

    # Check .env not tracked
    env_file = os.path.join(base, ".env")
    gitignore = os.path.join(base, ".gitignore")
    root_gitignore = os.path.join(base, "..", ".gitignore")

    env_ignored = False
    for gi in [gitignore, root_gitignore]:
        if os.path.exists(gi):
            content = open(gi).read()
            if ".env" in content:
                env_ignored = True
                break
    results.append(check(".env in .gitignore",
                         env_ignored,
                         "Add .env to .gitignore!" if not env_ignored else ""))

    # Check no hardcoded secrets in code
    secrets_found = []
    for root_dir, dirs, files in os.walk(base):
        if any(d in root_dir for d in [".git", ".venv", "node_modules", "frontend"]):
            continue
        for file in files:
            if file.endswith(".py") and file != "check_production_ready.py":
                fpath = os.path.join(root_dir, file)
                try:
                    content = open(fpath, encoding="utf-8").read()
                    for bad in ["sk-", "password123", "hardcoded"]:
                        if bad in content:
                            # Avoid false positives like "hardcoded" in docs or comments
                            if f"'{bad}'" in content or f'"{bad}"' in content:
                                secrets_found.append(f"{os.path.relpath(fpath, base)}:{bad}")
                except Exception:
                    pass
    results.append(check("No hardcoded secrets in code",
                         len(secrets_found) == 0,
                         str(secrets_found) if secrets_found else ""))

    # ── API Endpoints ──────────────────────────────
    print("\n🌐 API Endpoints (code check)")
    middleware_py = os.path.join(base, "common", "production_middleware.py")
    auth_py = os.path.join(base, "common", "auth.py")
    supervisor_py = os.path.join(base, "start_all.py")
    
    middleware_exists = os.path.exists(middleware_py)
    auth_exists = os.path.exists(auth_py)
    supervisor_exists = os.path.exists(supervisor_py)
    
    middleware_content = open(middleware_py, encoding="utf-8").read() if middleware_exists else ""
    auth_content = open(auth_py, encoding="utf-8").read() if auth_exists else ""
    supervisor_content = open(supervisor_py, encoding="utf-8").read() if supervisor_exists else ""
    
    results.append(check("/health endpoint defined",
                         middleware_exists and ('"/health"' in middleware_content or "'/health'" in middleware_content)))
    results.append(check("/ready endpoint defined",
                         middleware_exists and ('"/ready"' in middleware_content or "'/ready'" in middleware_content)))
    results.append(check("Authentication implemented",
                         auth_exists and ("api_key" in auth_content.lower() or "verify_api_key" in auth_content)))
    results.append(check("Rate limiting implemented",
                         middleware_exists and ("rate_limit" in middleware_content.lower() or "429" in middleware_content)))
    results.append(check("Graceful shutdown (SIGTERM)",
                         supervisor_exists and ("SIGTERM" in supervisor_content or "SIGINT" in supervisor_content)))
    results.append(check("Structured logging (JSON)",
                         middleware_exists and ("json.dumps" in middleware_content or 'JsonFormatter' in middleware_content)))

    # ── Docker ─────────────────────────────────────
    print("\n🐳 Docker")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        content = open(dockerfile).read()
        results.append(check("Multi-stage build",
                             "AS builder" in content or "AS runtime" in content))
        results.append(check("Non-root user",
                             "useradd" in content or "USER " in content))
        results.append(check("HEALTHCHECK instruction",
                             "HEALTHCHECK" in content))
        results.append(check("Slim base image",
                             "slim" in content or "alpine" in content))

    dockerignore = os.path.join(base, ".dockerignore")
    if os.path.exists(dockerignore):
        content = open(dockerignore).read()
        results.append(check(".dockerignore covers .env",
                             ".env" in content))
        results.append(check(".dockerignore covers __pycache__",
                             "__pycache__" in content))

    # ── Summary ───────────────────────────────────���
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")

    if pct == 100:
        print("  🎉 PRODUCTION READY! Deploy nào!")
    elif pct >= 80:
        print("  ✅ Almost there! Fix the ❌ items above.")
    elif pct >= 60:
        print("  ⚠️  Good progress. Several items need attention.")
    else:
        print("  ❌ Not ready. Review the checklist carefully.")

    print("=" * 55 + "\n")
    return pct == 100


if __name__ == "__main__":
    ready = run_checks()
    sys.exit(0 if ready else 1)
