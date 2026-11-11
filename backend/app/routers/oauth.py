"""
routers/oauth.py — Endpoints para flujos de autenticación OAuth de cuentas propias.
Carril D: Meta (Instagram/Facebook) y credenciales.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_current_project

router = APIRouter(prefix="/oauth", tags=["OAuth & Credenciales"])


@router.get(
    "/{provider}/start",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Inicia el flujo de autenticación OAuth para un proveedor soportado",
)
def oauth_start(
    provider: str,
    project: Dict[str, Any] = Depends(get_current_project),
):
    """Esqueleto Carril D: Generará URL de autorización con state anti-CSRF."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Carril D en desarrollo: flujo OAuth start para '{provider}' pendiente.",
    )


@router.get(
    "/{provider}/callback",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Maneja el callback OAuth y persiste el token cifrado",
)
def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None, description="Código de autorización devuelto por el proveedor"),
    state: Optional[str] = Query(None, description="Token anti-CSRF para validación"),
):
    """Esqueleto Carril D: Intercambiará code por token y lo guardará cifrado en reposo."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Carril D en desarrollo: callback OAuth para '{provider}' pendiente.",
    )
