# ============================================================
# Production Dockerfile — Legal Multi-Agent System Supervisor
# ============================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Non-root user
RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

# Copy packages từ builder
COPY --from=builder /root/.local /home/agent/.local

# Copy application packages
COPY common/ ./common/
COPY registry/ ./registry/
COPY compliance_agent/ ./compliance_agent/
COPY customer_agent/ ./customer_agent/
COPY law_agent/ ./law_agent/
COPY tax_agent/ ./tax_agent/
COPY start_all.py ./start_all.py

RUN chown -R agent:agent /app /home/agent/.local

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app:/home/agent/.local/lib/python3.11/site-packages
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose dynamic PORT (e.g. 10100 for customer agent gateway)
EXPOSE 10100

# Health check (pointing to customer agent health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"10100\")}/health')" \
    || exit 1

CMD ["python", "start_all.py"]
