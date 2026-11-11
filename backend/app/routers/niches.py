"""
routers/niches.py — Endpoints para descubrimiento y análisis de nichos.
Carril F: Descubrimiento de nichos.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_current_project
from ..schemas import (
    DiscoverNichePayload,
    AsyncTaskResponse,
    NicheResponse,
)

router = APIRouter(prefix="/niches", tags=["Nichos y Expansión"])


@router.post(
    "/discover",
    response_model=AsyncTaskResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Lanza tarea asíncrona de descubrimiento de nichos",
)
def discover_niche(
    payload: DiscoverNichePayload,
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril F: Lanzará tarea 202 con progreso SSE desde cuenta semilla."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril F en desarrollo: descubrimiento de nichos pendiente.",
    )


@router.get(
    "/{id}",
    response_model=NicheResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Obtiene la información estructurada de un nicho descubierto",
)
def get_niche(
    id: str,
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril F: Devolverá cuentas del nicho, temas etiquetados, líderes y posición de semilla."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Carril F en desarrollo: consulta del nicho '{id}' pendiente.",
    )
