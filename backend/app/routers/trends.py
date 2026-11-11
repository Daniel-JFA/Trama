"""
routers/trends.py — Endpoints para tendencias y aceleración temática.
Carril E: Temas y tendencias.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_current_project
from ..schemas import TrendsResponse

router = APIRouter(tags=["Tendencias y Temas"])


@router.get(
    "/trends",
    response_model=TrendsResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Obtiene ranking de temas y hashtags con volumen y aceleración",
)
def get_trends(
    from_date: Optional[str] = Query(None, alias="from", description="Fecha inicio YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, alias="to", description="Fecha fin YYYY-MM-DD"),
    community_id: Optional[int] = Query(None, description="Filtrar por ID de comunidad Leiden"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril E: Retornará temas/hashtags con volumen y aceleración."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril E en desarrollo: cálculo de tendencias y aceleración pendiente.",
    )
