"""API routes.

This package contains versioned API routes.
Add new versions by creating new folders (e.g., v2/) and updating router.py.
"""

from app.api.routers.v1 import api_router as v1_router

__all__ = ["v1_router"]
