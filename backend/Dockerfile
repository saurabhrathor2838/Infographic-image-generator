FROM python:3.11-slim AS base
WORKDIR /app

# Install dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app ./app
COPY .env.example .env.example

EXPOSE 8000

# Production
FROM base AS production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development
FROM base AS development
RUN pip install --no-cache-dir pytest pytest-asyncio httpx
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
