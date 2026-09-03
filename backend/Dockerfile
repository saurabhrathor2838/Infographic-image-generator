FROM python:3.11-slim AS base
WORKDIR /app

# Install dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app ./app
COPY .env.example .env.example

EXPOSE 8000

# Development (build with: docker build --target development)
FROM base AS development
RUN pip install --no-cache-dir pytest pytest-asyncio httpx
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production (default target for `docker build` and Render).
# Cloud platforms such as Render assign a dynamic port at runtime via the
# $PORT env var; fall back to 8000 when PORT is unset (e.g. local `docker run`).
# `exec` makes uvicorn PID 1 so it receives SIGTERM for graceful shutdown.
FROM base AS production
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
