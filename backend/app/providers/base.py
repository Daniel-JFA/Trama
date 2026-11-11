"""
base.py — Contrato e interfaz DataProvider para proveedores externos (YouTube, Meta, etc.).
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, List, Optional, Dict, Any, runtime_checkable


# ─── Dataclasses Canónicas Normalizadas ───────────────────────────────────────

@dataclass
class AccountData:
    platform: str
    external_id: str
    handle: str
    display_name: str
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    total_views: int = 0
    engagement_rate: Optional[float] = None
    is_owned: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PostData:
    external_post_id: str
    published_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    text: Optional[str] = None
    hashtags: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommentData:
    comment_id: str
    post_id: str
    author_id: str
    author_name: str
    text: str
    published_at: datetime
    likes: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


# ─── Excepciones Específicas de Proveedores ──────────────────────────────────

class ProviderError(Exception):
    """Excepción base para errores de proveedores de datos."""
    def __init__(self, message: str, platform: Optional[str] = None):
        super().__init__(message)
        self.platform = platform


class ProviderAuthError(ProviderError):
    """Error de autenticación o token expirado/inválido."""
    pass


class ProviderQuotaError(ProviderError):
    """Error cuando la cuota o tasa de peticiones (rate limit) se ha superado."""
    def __init__(self, message: str, platform: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message, platform=platform)
        self.retry_after = retry_after


class ProviderNotFoundError(ProviderError):
    """Recurso (cuenta, canal, publicación) no encontrado en la plataforma."""
    pass


# ─── Protocolo DataProvider ──────────────────────────────────────────────────

@runtime_checkable
class DataProvider(Protocol):
    """
    Protocolo formal que cualquier proveedor (YouTube, Meta, Mock) debe implementar.
    """
    platform: str

    def fetch_account(self, external_id: str) -> AccountData:
        """Obtiene métricas e información del perfil/canal."""
        ...

    def fetch_posts(
        self,
        external_id: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[PostData]:
        """Obtiene las publicaciones más recientes del creador."""
        ...

    def fetch_comments(
        self,
        post_id: str,
        limit: int = 100,
    ) -> List[CommentData]:
        """Obtiene comentarios recientes de una publicación."""
        ...

    def search_related(
        self,
        external_id: str,
        limit: int = 25,
    ) -> List[AccountData]:
        """Busca cuentas o canales relacionados o similares."""
        ...
