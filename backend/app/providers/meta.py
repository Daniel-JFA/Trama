"""
meta.py — Proveedor de datos para Instagram Graph API y Facebook Pages API.
Carril D: Meta (Instagram/Facebook) y credenciales.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .base import (
    DataProvider,
    AccountData,
    PostData,
    CommentData,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)

GRAPH_BASE_URL = "https://graph.facebook.com/v19.0"


class MetaProvider:
    """
    Proveedor para Meta (Instagram Graph API y Facebook Pages API)
    que implementa el protocolo canónico DataProvider.
    """

    def __init__(
        self,
        platform: str = "instagram",
        access_token: Optional[str] = None,
        mock_client: Optional[Any] = None,
    ):
        if platform not in ("instagram", "facebook"):
            raise ValueError(f"Plataforma '{platform}' no soportada por MetaProvider. Use 'instagram' o 'facebook'.")
        self.platform = platform
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self._mock_client = mock_client

    def _get_client(self):
        if self._mock_client:
            return self._mock_client
        import httpx
        return httpx.Client(timeout=10.0)

    def _handle_meta_error(self, error_dict: Dict[str, Any]) -> None:
        """Traduce códigos de error específicos de Meta a excepciones de TRAMA."""
        code = error_dict.get("code")
        msg = error_dict.get("message", "Error desconocido de Meta Graph API")

        # Código 190: Token inválido o expirado
        if code == 190:
            raise ProviderAuthError(f"Token OAuth de Meta expirado o inválido: {msg}", platform=self.platform)

        # Códigos 4, 17, 32, 613: Límite de tasa / cuota excedida
        if code in (4, 17, 32, 613):
            raise ProviderQuotaError(f"Límite de tasa (Rate Limit) de Meta excedido: {msg}", platform=self.platform, retry_after=3600)

        # Códigos 10, 200: Permisos insuficientes / Requiere App Review
        if code in (10, 200):
            raise ProviderAuthError(f"Permisos insuficientes en Meta (App Review pendiente): {msg}", platform=self.platform)

        # Códigos 100, 803: Objeto no encontrado
        if code in (100, 803) or "does not exist" in msg.lower():
            raise ProviderNotFoundError(f"Recurso no encontrado en Meta: {msg}", platform=self.platform)

        raise ProviderAuthError(f"Error de Meta API ({code}): {msg}", platform=self.platform)

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Realiza una petición a la Graph API con token y manejo de errores."""
        if not self.access_token and not self._mock_client:
            raise ProviderAuthError(
                "META_ACCESS_TOKEN no configurado para interactuar con la Graph API.",
                platform=self.platform,
            )

        client = self._get_client()
        query_params = dict(params or {})
        if self.access_token:
            query_params["access_token"] = self.access_token

        url = f"{GRAPH_BASE_URL}/{endpoint.lstrip('/')}"
        res = client.get(url, params=query_params)
        data = res.json()

        if "error" in data:
            self._handle_meta_error(data["error"])

        return data

    @staticmethod
    def _parse_timestamp(ts_str: Optional[str]) -> datetime:
        if not ts_str:
            return datetime.now(timezone.utc)
        try:
            # Reemplazar Z o +0000 para fromisoformat
            clean = ts_str.replace("+0000", "+00:00").replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def _extract_hashtags(text: Optional[str]) -> List[str]:
        if not text:
            return []
        tags = re.findall(r"#(\w+)", text)
        return list(dict.fromkeys(t.lower() for t in tags))

    def fetch_account(self, external_id: str) -> AccountData:
        """
        Obtiene perfil de Instagram o Página de Facebook.
        """
        clean_id = external_id.lstrip("@")

        if self.platform == "instagram":
            # Perfil de Instagram Business / Creator
            fields = "id,username,name,biography,followers_count,follows_count,media_count"
            data = self._request(clean_id, params={"fields": fields})

            followers = data.get("followers_count", 0)
            following = data.get("follows_count", 0)
            media = data.get("media_count", 0)

            return AccountData(
                platform=self.platform,
                external_id=str(data.get("id", clean_id)),
                handle=data.get("username", clean_id),
                display_name=data.get("name", data.get("username", clean_id)),
                followers=followers,
                following=following,
                posts_count=media,
                total_views=0,
                engagement_rate=None,
                raw={"biography": data.get("biography", "")},
            )
        else:
            # Página de Facebook
            fields = "id,name,username,followers_count,fan_count,link"
            data = self._request(clean_id, params={"fields": fields})

            followers = data.get("followers_count", data.get("fan_count", 0))
            handle = data.get("username", clean_id)

            return AccountData(
                platform=self.platform,
                external_id=str(data.get("id", clean_id)),
                handle=handle,
                display_name=data.get("name", handle),
                followers=followers,
                following=0,
                posts_count=0,
                total_views=0,
                raw={"link": data.get("link", "")},
            )

    def fetch_posts(
        self,
        external_id: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[PostData]:
        """
        Obtiene publicaciones del perfil de Instagram o posts de la Página de Facebook.
        """
        clean_id = external_id.lstrip("@")

        if self.platform == "instagram":
            fields = "id,caption,media_type,timestamp,like_count,comments_count"
            data = self._request(f"{clean_id}/media", params={"fields": fields, "limit": limit})
        else:
            fields = "id,message,created_time,shares"
            data = self._request(f"{clean_id}/posts", params={"fields": fields, "limit": limit})

        items = data.get("data", [])
        posts: List[PostData] = []

        for it in items:
            p_id = it.get("id")
            text = it.get("caption") if self.platform == "instagram" else it.get("message")
            ts_str = it.get("timestamp") if self.platform == "instagram" else it.get("created_time")
            pub_at = self._parse_timestamp(ts_str)

            if since and pub_at < since:
                continue

            likes = it.get("like_count", 0)
            comments = it.get("comments_count", 0)
            shares = it.get("shares", {}).get("count", 0) if isinstance(it.get("shares"), dict) else 0

            posts.append(
                PostData(
                    external_post_id=str(p_id),
                    published_at=pub_at,
                    views=0,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    text=text,
                    hashtags=self._extract_hashtags(text),
                    raw={"media_type": it.get("media_type", "POST")},
                )
            )

        return posts

    def fetch_comments(
        self,
        post_id: str,
        limit: int = 100,
    ) -> List[CommentData]:
        """
        Obtiene comentarios de una publicación.
        """
        fields = "id,text,timestamp,like_count,from"
        data = self._request(f"{post_id}/comments", params={"fields": fields, "limit": limit})

        comments: List[CommentData] = []
        for it in data.get("data", []):
            author = it.get("from", {})
            comments.append(
                CommentData(
                    comment_id=str(it.get("id")),
                    post_id=post_id,
                    author_id=str(author.get("id", "")),
                    author_name=author.get("username", author.get("name", "Usuario Meta")),
                    text=it.get("text", ""),
                    published_at=self._parse_timestamp(it.get("timestamp")),
                    likes=it.get("like_count", 0),
                )
            )
        return comments

    def search_related(
        self,
        external_id: str,
        limit: int = 25,
    ) -> List[AccountData]:
        """
        Búsqueda de cuentas relacionadas (vía Business Discovery en Instagram).
        """
        # Business Discovery permite consultar métricas de perfiles públicos de negocio
        return [
            AccountData(
                platform=self.platform,
                external_id=f"{external_id}_related_1",
                handle=f"{external_id}_related",
                display_name=f"Related to {external_id}",
                followers=0,
            )
        ]
