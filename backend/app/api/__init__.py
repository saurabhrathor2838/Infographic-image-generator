"""
API package — HTTP router registration and route modules.

The public router is exposed as :data:`api_router`; it is included by
``app.main:app``.
"""

from app.api.routes import api_router

__all__ = ["api_router"]
