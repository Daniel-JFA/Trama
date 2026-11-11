"""
oauth.py — Flujo de autorización OAuth2 para Meta (Instagram Graph API / Facebook Login).
Carril D: Meta (Instagram/Facebook) y autenticación.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.

PERMISOS REQUERIDOS POR META APP REVIEW:
1. `instagram_basic`: Lectura de perfil (id, username) y métricas de publicaciones públicas.
2. `instagram_manage_insights`: Acceso a métricas de alcance, impresiones e interacción de cuentas propias.
3. `pages_read_engagement`: Lectura de publicaciones, likes y métricas de páginas de Facebook.
4. `pages_show_list`: Lista de páginas administradas por el usuario para vincular su cuenta de Instagram.
"""

import os
import hmac
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from sqlalchemy import select

from .crypto import encrypt_token, decrypt_token
from .models import OAuthCredential, Account
from .database import SessionLocal
from .providers.base import ProviderAuthError

GRAPH_API_VERSION = "v19.0"
FB_AUTH_DIALOG = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"
FB_TOKEN_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"

META_SCOPES = [
    "instagram_basic",
    "instagram_manage_insights",
    "pages_read_engagement",
    "pages_show_list",
]


def _get_signing_key(secret_key: Optional[str] = None) -> bytes:
    key = secret_key or os.getenv("META_APP_SECRET") or os.getenv("TRAMA_TOKEN_KEY", "trama_state_secret")
    return key.encode("utf-8")


def generate_state_token(project_id: str, secret_key: Optional[str] = None) -> str:
    """
    Genera un token de estado anti-CSRF firmado criptográficamente que codifica
    el project_id y una marca de tiempo UTC.
    """
    ts = int(time.time())
    payload = f"{project_id}:{ts}"
    key = _get_signing_key(secret_key)
    signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_state_token(state_token: str, max_age_seconds: int = 1800, secret_key: Optional[str] = None) -> Optional[str]:
    """
    Valida la firma anti-CSRF y vigencia del state. Retorna project_id si es válido.
    """
    if not state_token or ":" not in state_token:
        return None

    parts = state_token.split(":")
    if len(parts) != 3:
        return None

    project_id, ts_str, signature = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return None

    # Verificar vigencia (30 minutos por defecto)
    if time.time() - ts > max_age_seconds or ts > time.time() + 60:
        return None

    payload = f"{project_id}:{ts_str}"
    key = _get_signing_key(secret_key)
    expected_sig = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return None

    return project_id


def get_meta_auth_url(
    project_id: str,
    redirect_uri: str,
    app_id: Optional[str] = None,
    scopes: Optional[list] = None,
) -> str:
    """
    Construye la URL para iniciar el flujo OAuth en Meta dialog.
    """
    client_id = app_id or os.getenv("META_APP_ID")
    if not client_id:
        raise ValueError("META_APP_ID no configurada en las variables de entorno.")

    state = generate_state_token(project_id)
    scope_str = ",".join(scopes or META_SCOPES)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope_str,
        "response_type": "code",
    }
    return f"{FB_AUTH_DIALOG}?{urlencode(params)}"


def exchange_code_for_short_lived_token(
    code: str,
    redirect_uri: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    http_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Intercambia el authorization code por un token de corta duración (~1-2 horas).
    """
    client_id = app_id or os.getenv("META_APP_ID")
    client_secret = app_secret or os.getenv("META_APP_SECRET")

    if not client_id or not client_secret:
        raise ProviderAuthError("Credenciales META_APP_ID / META_APP_SECRET incompletas.", platform="meta")

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }

    if http_client:
        resp = http_client.get(FB_TOKEN_URL, params=params)
        return resp.json()

    import httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(FB_TOKEN_URL, params=params)
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err = data.get("error", {}).get("message", "Error al intercambiar código")
                raise ProviderAuthError(f"Meta OAuth error: {err}", platform="meta")
            return data
    except Exception as exc:
        raise ProviderAuthError(f"Fallo en comunicación con Meta: {exc}", platform="meta") from exc


def exchange_for_long_lived_token(
    short_lived_token: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    http_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Intercambia el token de corta duración por uno de larga duración (~60 días).
    """
    client_id = app_id or os.getenv("META_APP_ID")
    client_secret = app_secret or os.getenv("META_APP_SECRET")

    if not client_id or not client_secret:
        raise ProviderAuthError("Credenciales de Meta ausentes.", platform="meta")

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "fb_exchange_token": short_lived_token,
    }

    if http_client:
        resp = http_client.get(FB_TOKEN_URL, params=params)
        return resp.json()

    import httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(FB_TOKEN_URL, params=params)
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err = data.get("error", {}).get("message", "Error renovando token")
                raise ProviderAuthError(f"Meta Long-Lived Token error: {err}", platform="meta")
            return data
    except Exception as exc:
        raise ProviderAuthError(f"Fallo al renovar token con Meta: {exc}", platform="meta") from exc


def store_oauth_credential(
    account_id: int,
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in_seconds: Optional[int] = None,
    scopes: Optional[str] = None,
    db: Optional[Session] = None,
) -> OAuthCredential:
    """
    Guarda los tokens cifrados en reposo en la tabla oauth_credentials.
    Nunca almacena tokens en texto plano.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        token_enc = encrypt_token(access_token)
        refresh_enc = encrypt_token(refresh_token) if refresh_token else None

        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

        existing = db.execute(
            select(OAuthCredential).where(
                OAuthCredential.account_id == account_id,
                OAuthCredential.provider == provider,
            )
        ).scalar_one_or_none()

        if existing:
            existing.access_token_enc = token_enc
            existing.refresh_token_enc = refresh_enc
            existing.expires_at = expires_at
            if scopes:
                existing.scopes = scopes
            db.commit()
            db.refresh(existing)
            return existing

        cred = OAuthCredential(
            account_id=account_id,
            provider=provider,
            access_token_enc=token_enc,
            refresh_token_enc=refresh_enc,
            expires_at=expires_at,
            scopes=scopes,
        )
        db.add(cred)
        db.commit()
        db.refresh(cred)
        return cred
    finally:
        if close_db:
            db.close()


def get_decrypted_token(
    account_id: int,
    provider: str = "meta",
    db: Optional[Session] = None,
) -> Optional[str]:
    """
    Recupera y descifra el token OAuth para la cuenta especificada.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        cred = db.execute(
            select(OAuthCredential).where(
                OAuthCredential.account_id == account_id,
                OAuthCredential.provider == provider,
            )
        ).scalar_one_or_none()

        if not cred or not cred.access_token_enc:
            return None

        # Si el token ha expirado
        if cred.expires_at:
            exp = cred.expires_at.replace(tzinfo=timezone.utc) if cred.expires_at.tzinfo is None else cred.expires_at
            if exp < datetime.now(timezone.utc):
                raise ProviderAuthError("El token OAuth ha expirado y requiere renovación.", platform=provider)

        return decrypt_token(cred.access_token_enc)
    finally:
        if close_db:
            db.close()
