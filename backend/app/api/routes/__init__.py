"""
Route modules package.

The :data:`api_router` defined here aggregates all sub-routers under the
``/api`` prefix.  Individual route modules live alongside this ``__init__``
file (e.g. ``health.py``, ``generation.py``) and are imported and registered
here.
"""

from fastapi import APIRouter

# Sub-router imports
from app.api.routes.health import router as health_router
from app.api.routes.generation import router as generation_router
from app.api.routes.visualization import router as visualization_router

# Master API router — included by ``app.main:app``.
api_router: APIRouter = APIRouter(prefix="/api")

# Health / status check
api_router.include_router(health_router, tags=["health"])

# Generation endpoints
api_router.include_router(generation_router, tags=["generation"])

# Visualization / rendering endpoints
api_router.include_router(visualization_router, tags=["visualization"])

# Future route modules will be added here:
#   from app.api.routes.images import router as image_router
#   api_router.include_router(image_router, tags=["images"])
