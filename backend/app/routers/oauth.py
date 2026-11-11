"""
routers/oauth.py — Endpoints para flujos de autenticación OAuth de cuentas propias.
Carril D: Meta (Instagram/Facebook) y credenciales.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_project
from ..growth import create_account
from ..oauth import (
    get_meta_auth_url,
    verify_state_token,
    exchange_code_for_short_lived_token,
    exchange_for_long_lived_token,
    store_oauth_credential,
)

router = APIRouter(prefix="/oauth", tags=["OAuth & Credenciales"])


@router.get(
    "/{provider}/start",
    status_code=status.HTTP_200_OK,
    summary="Inicia el flujo de autenticación OAuth para un proveedor soportado",
)
def oauth_start(
    provider: str,
    redirect_uri: Optional[str] = Query(None, description="URI de callback personalizada"),
    project: Dict[str, Any] = Depends(get_current_project),
):
    """
    Genera la URL de autorización con token 'state' anti-CSRF firmado criptográficamente.
    Soporta: 'meta', 'instagram', 'facebook'.
    """
    prov = provider.lower()
    if prov not in ("meta", "instagram", "facebook"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor OAuth '{provider}' no soportado. Disponibles: meta, instagram, facebook.",
        )

    cb_uri = redirect_uri or f"http://localhost:8000/oauth/{prov}/callback"

    try:
        auth_url = get_meta_auth_url(project_id=project["id"], redirect_uri=cb_uri)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuración OAuth incompleta: {exc}",
        ) from exc

    return {
        "provider": prov,
        "project_id": project["id"],
        "authorization_url": auth_url,
        "redirect_uri": cb_uri,
    }


@router.get(
    "/{provider}/callback",
    status_code=status.HTTP_200_OK,
    summary="Maneja el callback OAuth y persiste el token cifrado",
)
def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None, description="Código de autorización devuelto por el proveedor"),
    state: Optional[str] = Query(None, description="Token anti-CSRF para validación"),
    error: Optional[str] = Query(None, description="Mensaje de error si el usuario denegó permisos"),
    db: Session = Depends(get_db),
):
    """
    Recibe el código de autorización, valida el 'state', obtiene el token de larga duración
    y lo almacena estrictamente CIFRADO en reposo. Nunca retorna el token por la API.
    """
    prov = provider.lower()
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Autorización cancelada o denegada por el usuario: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parámetros 'code' y 'state' son obligatorios en el callback.",
        )

    project_id = verify_state_token(state)
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Validación anti-CSRF fallida: 'state' inválido o expirado.",
        )

    cb_uri = f"http://localhost:8000/oauth/{prov}/callback"

    try:
        # 1. Obtener token de corta duración
        short_token_data = exchange_code_for_short_lived_token(code=code, redirect_uri=cb_uri)
        short_token = short_token_data.get("access_token")

        # 2. Canjear por token de larga duración (~60 días)
        long_token_data = exchange_for_long_lived_token(short_lived_token=short_token)
        long_token = long_token_data.get("access_token", short_token)
        expires_in = long_token_data.get("expires_in", 5184000)  # 60 días aprox.

        # 3. Registrar cuenta propia vinculada si aún no existe
        account = create_account(
            project_id=project_id,
            platform="instagram" if prov == "instagram" else "facebook",
            external_id=f"{prov}_user_{code[:8]}",
            handle=f"{prov}_account",
            display_name=f"Cuenta Propia {prov.title()}",
            is_owned=True,
            db=db,
        )

        # 4. Guardar token cifrado
        store_oauth_credential(
            account_id=account.id,
            provider=prov,
            access_token=long_token,
            expires_in_seconds=expires_in,
            scopes="instagram_basic,instagram_manage_insights,pages_read_engagement,pages_show_list",
            db=db,
        )

        return {
            "status": "authorized",
            "provider": prov,
            "project_id": project_id,
            "account_id": account.id,
            "is_owned": True,
            "expires_in_seconds": expires_in,
            "message": "Token OAuth cifrado y guardado exitosamente en reposo.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fallo en el flujo OAuth con el proveedor {prov}: {exc}",
        ) from exc
