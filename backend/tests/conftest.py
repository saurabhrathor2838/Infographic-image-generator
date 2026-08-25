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
from app.providers.base import ProviderConfig
from app.providers.text_generator import TextGenerator, TextResult


class MockTextGenerator(TextGenerator):
    """Deterministic, in-memory LLM stand-in for tests.

    Returns canned responses in order; repeating the last one once exhausted.
    Records every prompt it receives for assertions.
    """

    def __init__(self, responses) -> None:
        super().__init__(ProviderConfig(name="MockTextGenerator"))
        self._responses = list(responses)
        self.calls = 0
        self.received_prompts: list[str] = []

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt=None,
        temperature=0.7,
        max_tokens=None,
        **kwargs,
    ) -> TextResult:
        self.received_prompts.append(prompt)
        idx = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return TextResult(text=self._responses[idx], model="mock", usage={})

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def make_text_generator():
    """Factory fixture returning a :class:`MockTextGenerator` for given responses."""

    def _make(responses) -> MockTextGenerator:
        return MockTextGenerator(responses)

    return _make


@pytest.fixture
def override_llm():
    """Override ``get_text_generator`` to return a fixed mock instance.

    Usage::

        gen = make_text_generator([VALID_JSON])
        override_llm(gen)
        response = await client.post("/api/plan", json={...})

    The override is torn down automatically after the test.
    """
    from app.providers.factory import get_text_generator

    def _set(generator) -> None:
        app.dependency_overrides[get_text_generator] = lambda: generator

    yield _set
    app.dependency_overrides.pop(get_text_generator, None)


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client for the FastAPI test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
