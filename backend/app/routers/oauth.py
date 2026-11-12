"""
routers/oauth.py — Endpoints para flujos de autenticación OAuth de cuentas propias.
Carril D & Carril A: Meta (Instagram/Facebook) y Google (YouTube) con credenciales cifradas.
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
from ..providers.youtube import YouTubeProvider

router = APIRouter(prefix="/oauth", tags=["OAuth & Credenciales"])

SUPPORTED_PROVIDERS = ("meta", "instagram", "facebook", "google", "youtube")


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
    Soporta: 'meta', 'instagram', 'facebook', 'google', 'youtube'.
    """
    prov = provider.lower()
    if prov not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor OAuth '{provider}' no soportado. Disponibles: {', '.join(SUPPORTED_PROVIDERS)}.",
        )

    cb_uri = redirect_uri or f"http://localhost:8000/oauth/{prov}/callback"

    try:
        if prov in ("google", "youtube"):
            auth_url = YouTubeProvider.get_google_auth_url(project_id=project["id"], redirect_uri=cb_uri)
        else:
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
    Recibe el código de autorización, valida el 'state', obtiene los tokens de acceso
    y los almacena estrictamente CIFRADOS en reposo. Nunca retorna el token por la API.
    """
    prov = provider.lower()
    if prov not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor OAuth '{provider}' no soportado. Disponibles: {', '.join(SUPPORTED_PROVIDERS)}.",
        )

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
        if prov in ("google", "youtube"):
            # Flujo Google OAuth
            token_data = YouTubeProvider.exchange_code_for_tokens(code=code, redirect_uri=cb_uri)
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            scopes = token_data.get("scope", "https://www.googleapis.com/auth/yt-analytics.readonly https://www.googleapis.com/auth/youtube.readonly")

            # Intentar obtener información del canal propio o fallback determinista
            channel_id = f"youtube_channel_{code[:8]}"
            handle = "youtube_account"
            display_name = "Canal Propio YouTube"
            try:
                yt_provider = YouTubeProvider(access_token=access_token)
                acc_data = yt_provider.fetch_account("MINE")
                channel_id = acc_data.external_id
                handle = acc_data.handle
                display_name = acc_data.display_name
            except Exception:
                pass

            account = create_account(
                project_id=project_id,
                platform="youtube",
                external_id=channel_id,
                handle=handle,
                display_name=display_name,
                is_owned=True,
                db=db,
            )

            store_oauth_credential(
                account_id=account.id,
                provider="youtube",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in_seconds=expires_in,
                scopes=scopes,
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

        # Flujo Meta OAuth
        short_token_data = exchange_code_for_short_lived_token(code=code, redirect_uri=cb_uri)
        short_token = short_token_data.get("access_token")

        long_token_data = exchange_for_long_lived_token(short_lived_token=short_token)
        long_token = long_token_data.get("access_token", short_token)
        expires_in = long_token_data.get("expires_in", 5184000)

        account = create_account(
            project_id=project_id,
            platform="instagram" if prov == "instagram" else "facebook",
            external_id=f"{prov}_user_{code[:8]}",
            handle=f"{prov}_account",
            display_name=f"Cuenta Propia {prov.title()}",
            is_owned=True,
            db=db,
        )

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
