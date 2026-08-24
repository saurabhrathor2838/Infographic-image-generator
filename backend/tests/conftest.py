"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest before any tests run.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the ``backend/`` directory is on ``sys.path`` so that ``app`` can be
# imported by all test modules, regardless of where pytest is invoked from.
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client for the FastAPI test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
