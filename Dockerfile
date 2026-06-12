# Root Railway Dockerfile.
# The production app lives in 06-lab-complete, but Railway is deploying this repo root.

# Stage 1: Build the frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build python dependencies
FROM python:3.11-slim AS builder
WORKDIR /build
COPY 06-lab-complete/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Runtime
FROM python:3.11-slim AS runtime
RUN groupadd -r agent && useradd -r -g agent -d /app agent
WORKDIR /app

COPY --from=builder /root/.local /home/agent/.local
COPY 06-lab-complete/app/ ./app/
# Copy the compiled frontend files from Stage 1
COPY --from=frontend-builder /06-lab-complete/frontend-dist ./frontend-dist

# Copy metadata/config files for the dashboard repository inventory
COPY README.md ./README.md
COPY Dockerfile ./Dockerfile
COPY railway.toml ./railway.toml
COPY 06-lab-complete/docker-compose.yml ./06-lab-complete/docker-compose.yml
COPY 06-lab-complete/Dockerfile ./06-lab-complete/Dockerfile
COPY 06-lab-complete/railway.toml ./06-lab-complete/railway.toml
COPY 06-lab-complete/render.yaml ./06-lab-complete/render.yaml

RUN chown -R agent:agent /app /home/agent/.local

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app:/home/agent/.local/lib/python3.11/site-packages
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV REPO_ROOT=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\", \"8000\")}/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]

