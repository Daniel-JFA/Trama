"""
routers/growth.py — Endpoints para seguimiento de cuentas, instantáneas y crecimiento.
Carril B: Snapshots y scheduler.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_current_project
from ..schemas import (
    CreateAccountPayload,
    AccountOut,
    AccountSnapshotOut,
    AccountGrowthResponse,
)

router = APIRouter(tags=["Crecimiento y Creadores"])


@router.post(
    "/accounts",
    response_model=AccountOut,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Registra una cuenta a seguir en el proyecto activo",
)
def create_account(
    payload: CreateAccountPayload,
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril B: Registrará una cuenta {platform, external_id, is_owned}."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril B en desarrollo: registro de cuentas pendiente.",
    )


@router.get(
    "/accounts",
    response_model=List[AccountOut],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Lista cuentas del proyecto activo",
)
def list_accounts(
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril B: Listará las cuentas seguidas en el proyecto."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril B en desarrollo: listado de cuentas pendiente.",
    )


@router.post(
    "/accounts/{id}/snapshot",
    response_model=AccountSnapshotOut,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Fuerza una instantánea para la cuenta indicada",
)
def take_account_snapshot(
    id: int,
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril B: Forzará recolección inmediata de instantánea."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril B en desarrollo: recolección manual de instantánea pendiente.",
    )


@router.get(
    "/accounts/{id}/growth",
    response_model=AccountGrowthResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Obtiene la serie temporal de crecimiento y métricas clave de la cuenta",
)
def get_account_growth(
    id: int,
    from_date: Optional[str] = Query(None, alias="from", description="Fecha inicio YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, alias="to", description="Fecha fin YYYY-MM-DD"),
    bucket: str = Query("day", description="Granularidad temporal: day | week | month"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril B: Devolverá serie temporal [{date, followers, delta, growth_pct}] y resumen."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Carril B en desarrollo: métricas de crecimiento pendientes.",
    )
