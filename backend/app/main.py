"""
AI Visual Generator — FastAPI Application Entry Point.

Run with:
    cd backend && uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.exceptions import AppError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
    # Startup: initialise providers, logging, etc.
    # Phase 1: minimal — providers are lazily initialised.
    yield
    # Shutdown: cleanup connections, temp files, etc.


def create_app() -> FastAPI:
    """Application factory.

    Returns a fully configured :class:`FastAPI` instance with routing,
    CORS, and exception handlers.
    """
    app = FastAPI(
        title="AI Visual Generator",
        description=(
            "A web application that generates infographic images and "
            "complexity images using an Agentic AI workflow."
        ),
        version="0.1.0",
        contact={
            "name": "Saurabh Rathor",
            "url": "https://github.com/saurabhrathor2838/Infographic-image-generator",
        },
        lifespan=lifespan,
    )

    # ── Middleware ──────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ──────────────────────────────────────────────────────────

    app.include_router(api_router)

    # ── Exception handlers ──────────────────────────────────────────────

    @app.exception_handler(AppError)
    async def _app_error_handler(request, exc: AppError):
        """Convert AppError subclasses into structured HTTP responses."""
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": exc.message or exc.__class__.__name__,
                "details": exc.details,
            },
        )

    return app


app: FastAPI = create_app()


def main() -> None:
    """Entry point for ``python -m app.main`` or ``python app/main.py``."""
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )


if __name__ == "__main__":
    main()
