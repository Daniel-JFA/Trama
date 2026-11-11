"""
routers — Módulos de endpoints HTTP para TRAMA.
"""

from .growth import router as growth_router
from .oauth import router as oauth_router
from .trends import router as trends_router
from .niches import router as niches_router

__all__ = [
    "growth_router",
    "oauth_router",
    "trends_router",
    "niches_router",
]
