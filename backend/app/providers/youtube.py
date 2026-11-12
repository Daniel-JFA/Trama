"""
youtube.py — Conector a YouTube Data API v3 y YouTube Analytics API v2 con OAuth y control de cuota.
Carril A: YouTube Data API v3 + OAuth + YouTube Analytics API.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.

VENTANA DE HISTORIAL Y BACKFILL EN YOUTUBE ANALYTICS:
YouTube Analytics API permite consultas históricas a nivel diario desde el 2005-09-01 (fecha límite
de la plataforma) o desde la fecha de creación del canal (snippet.publishedAt en Data API v3).
Para canales propios creados desde el día 0, la ventana abarca desde publishedAt hasta la fecha
de corte (típicamente ayer, debido a la latencia de consolidación de métricas de 24 a 48 horas de YouTube).
"""

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlencode

from .base import (
    DataProvider,
    AccountData,
    PostData,
    CommentData,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)

# ─── Dataclasses de Métricas Avanzadas de YouTube Analytics ───────────────────

@dataclass
class YouTubeDailyMetric:
    """Métricas consolidadas de un día para el canal propio."""
    date: str
    views: int = 0
    watch_time_minutes: int = 0
    average_view_duration_seconds: int = 0
    average_view_percentage: float = 0.0  # Retención de audiencia diaria (%)
    subscribers_gained: int = 0
    subscribers_lost: int = 0
    net_subscribers: int = 0
    impressions: int = 0
    ctr: float = 0.0  # Click-Through Rate (%)


@dataclass
class YouTubeVideoAnalytics:
    """Métricas de rendimiento analítico por video."""
    video_id: str
    views: int = 0
    watch_time_minutes: int = 0
    average_view_duration_seconds: int = 0
    retention_rate_pct: float = 0.0  # averageViewPercentage
    subscribers_gained: int = 0
    subscribers_lost: int = 0
    net_subscribers: int = 0
    likes: int = 0
    comments: int = 0
    impressions: int = 0
    ctr: float = 0.0


@dataclass
class TrafficSourceItem:
    """Distribución de fuentes de tráfico del canal o video."""
    source_type: str
    views: int = 0
    watch_time_minutes: int = 0
    views_percentage: float = 0.0


@dataclass
class DemographicsItem:
    """Distribución demográfica por grupo de edad y género."""
    age_group: str
    gender: str
    viewer_percentage: float = 0.0


@dataclass
class AudienceRetentionPoint:
    """Punto en la curva de retención de audiencia de un video."""
    ratio: float  # Posición relativa en el video (0.0 a 1.0)
    watch_ratio: float  # Porcentaje de retención respecto al total


@dataclass
class BackfillResult:
    """Resultado del proceso de rellenado histórico hacia atrás."""
    channel_id: str
    start_date: str
    end_date: str
    days_retrieved: int
    total_views: int
    total_watch_time_minutes: int
    net_subscribers: int
    total_impressions: int
    daily_metrics: List[YouTubeDailyMetric] = field(default_factory=list)


# ─── Constantes OAuth de Google / YouTube ─────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeProvider:
    """
    Proveedor para YouTube Data API v3 y YouTube Analytics API v2.
    Implementa el protocolo DataProvider y añade soporte para canal propio vía OAuth:
    - Impresiones y CTR
    - Retención de audiencia (diaria y curva por video)
    - Fuentes de tráfico
    - Demografía (edad y género)
    - Suscriptores ganados y perdidos por video
    - Backfill histórico desde la creación del canal
    """
    platform: str = "youtube"

    # Costos de cuota oficiales según YouTube Data API v3 (unidades por llamada)
    QUOTA_COSTS = {
        "channels": 1,
        "videos": 1,
        "commentThreads": 1,
        "search": 100,
        "analytics": 1,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        quota_limit: int = 10000,
        cache_ttl_seconds: int = 300,
        mock_client: Optional[Any] = None,
        mock_analytics_client: Optional[Any] = None,
    ):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
        self.quota_limit = quota_limit
        self.cache_ttl_seconds = cache_ttl_seconds
        self.quota_used = 0
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._mock_client = mock_client
        self._mock_analytics_client = mock_analytics_client
        self._youtube_service = None
        self._analytics_service = None

    # ─── Manejo de Clientes y Servicios ───────────────────────────────────────

    def _get_service(self):
        """Inicializa el cliente de YouTube Data API v3 de forma perezosa."""
        if self._mock_client:
            return self._mock_client
        if self._youtube_service:
            return self._youtube_service

        from googleapiclient.discovery import build

        if self.access_token:
            from google.oauth2.credentials import Credentials
            creds = Credentials(token=self.access_token)
            self._youtube_service = build("youtube", "v3", credentials=creds, cache_discovery=False)
            return self._youtube_service

        if self.api_key:
            self._youtube_service = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
            return self._youtube_service

        raise ProviderAuthError(
            "Ni YOUTUBE_API_KEY ni credenciales OAuth fueron configuradas para acceder a YouTube Data API v3.",
            platform=self.platform,
        )

    def _get_analytics_service(self):
        """Inicializa el cliente de YouTube Analytics API v2 de forma perezosa."""
        if self._mock_analytics_client:
            return self._mock_analytics_client
        if self._analytics_service:
            return self._analytics_service

        if not self.access_token:
            raise ProviderAuthError(
                "YouTube Analytics API requiere autorización OAuth de la cuenta propia (access_token ausente).",
                platform=self.platform,
            )

        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        self._analytics_service = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        return self._analytics_service

    # ─── Flujo OAuth2 de Google ───────────────────────────────────────────────

    @classmethod
    def get_google_auth_url(
        cls,
        project_id: str,
        redirect_uri: str,
        client_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        state: Optional[str] = None,
    ) -> str:
        """
        Construye la URL de consentimiento OAuth2 de Google con token state anti-CSRF.
        """
        cid = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        if not cid:
            raise ValueError("GOOGLE_OAUTH_CLIENT_ID no configurada en las variables de entorno.")

        # Generar state si no se proporciona
        if state is None:
            try:
                from ..oauth import generate_state_token
                state_val = generate_state_token(project_id)
            except Exception:
                # Fallback simple con timestamp si app.oauth no está en contexto
                state_val = f"{project_id}:{int(time.time())}"
        else:
            state_val = state

        params = {
            "client_id": cid,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or GOOGLE_OAUTH_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state_val,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    @classmethod
    def exchange_code_for_tokens(
        cls,
        code: str,
        redirect_uri: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        http_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Intercambia el authorization code por tokens OAuth de Google.
        """
        cid = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        csec = client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not cid or not csec:
            raise ProviderAuthError("Credenciales GOOGLE_OAUTH_CLIENT_ID/SECRET ausentes.", platform="youtube")

        payload = {
            "code": code,
            "client_id": cid,
            "client_secret": csec,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        if http_client:
            resp = http_client.post(GOOGLE_TOKEN_URL, data=payload)
            return resp.json()

        import httpx
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(GOOGLE_TOKEN_URL, data=payload)
                data = resp.json()
                if resp.status_code != 200 or "error" in data:
                    err = data.get("error_description", data.get("error", "Error en token exchange"))
                    raise ProviderAuthError(f"Error de autenticación Google OAuth: {err}", platform="youtube")
                return data
        except Exception as exc:
            raise ProviderAuthError(f"Fallo al conectar con Google OAuth: {exc}", platform="youtube") from exc

    @classmethod
    def refresh_google_token(
        cls,
        refresh_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        http_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Refresca un access_token expirado usando el refresh_token.
        """
        cid = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        csec = client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not cid or not csec:
            raise ProviderAuthError("Credenciales GOOGLE_OAUTH_CLIENT_ID/SECRET ausentes.", platform="youtube")

        payload = {
            "refresh_token": refresh_token,
            "client_id": cid,
            "client_secret": csec,
            "grant_type": "refresh_token",
        }

        if http_client:
            resp = http_client.post(GOOGLE_TOKEN_URL, data=payload)
            return resp.json()

        import httpx
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(GOOGLE_TOKEN_URL, data=payload)
                data = resp.json()
                if resp.status_code != 200 or "error" in data:
                    err = data.get("error_description", data.get("error", "Error renovando token"))
                    raise ProviderAuthError(f"Error renovando token de Google: {err}", platform="youtube")
                return data
        except Exception as exc:
            raise ProviderAuthError(f"Fallo al renovar token con Google: {exc}", platform="youtube") from exc

    # ─── Control de Cuota y Caché ─────────────────────────────────────────────

    def _consume_quota(self, operation: str) -> None:
        cost = self.QUOTA_COSTS.get(operation, 1)
        if self.quota_used + cost > self.quota_limit:
            raise ProviderQuotaError(
                f"Límite de cuota diaria de YouTube excedido: {self.quota_used}/{self.quota_limit} unidades consumidas.",
                platform=self.platform,
                retry_after=86400,
            )
        self.quota_used += cost

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["timestamp"] < self.cache_ttl_seconds:
                return entry["data"]
            del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        self._cache[cache_key] = {"data": data, "timestamp": time.time()}

    @staticmethod
    def _parse_datetime(iso_str: Optional[str]) -> datetime:
        if not iso_str:
            return datetime.now(timezone.utc)
        try:
            clean_str = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
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

    @staticmethod
    def _parse_result_table(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convierte la estructura matricial {columnHeaders, rows} de YouTube Analytics
        en una lista amigable de diccionarios {nombre_columna: valor}.
        """
        headers = [h["name"] for h in response.get("columnHeaders", [])]
        rows = response.get("rows", [])
        result = []
        for row in rows:
            record = {}
            for idx, col_name in enumerate(headers):
                if idx < len(row):
                    record[col_name] = row[idx]
            result.append(record)
        return result

    # ─── DataProvider Core: Métricas Públicas (YouTube Data API v3) ───────────

    def fetch_account(self, external_id: str) -> AccountData:
        """
        Obtiene información del canal por su channelId (UC...) o handle (@...).
        """
        cache_key = f"channel:{external_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        self._consume_quota("channels")
        service = self._get_service()

        kwargs = {"part": "snippet,statistics"}
        if external_id.startswith("UC") or len(external_id) == 24:
            kwargs["id"] = external_id
        elif external_id.startswith("@"):
            kwargs["forHandle"] = external_id
        else:
            kwargs["forHandle"] = f"@{external_id}"

        try:
            response = service.channels().list(**kwargs).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en YouTube: {err_msg}", platform=self.platform, retry_after=86400) from exc
            if "invalid" in err_msg.lower() or "401" in err_msg or "403" in err_msg:
                raise ProviderAuthError(f"Error de autorización con YouTube: {err_msg}", platform=self.platform) from exc
            raise

        items = response.get("items", [])
        if not items:
            if "forHandle" in kwargs and not external_id.startswith("UC"):
                self._consume_quota("channels")
                clean_name = external_id.lstrip("@")
                try:
                    response = service.channels().list(part="snippet,statistics", forUsername=clean_name).execute()
                    items = response.get("items", [])
                except Exception:
                    pass

        if not items:
            raise ProviderNotFoundError(f"Canal de YouTube '{external_id}' no encontrado.", platform=self.platform)

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        subs = int(statistics.get("subscriberCount", 0))
        views = int(statistics.get("viewCount", 0))
        videos = int(statistics.get("videoCount", 0))

        er = None
        if subs > 0 and videos > 0:
            avg_views = views / videos
            er = round((avg_views / subs) * 100, 2)

        handle = snippet.get("customUrl", external_id).lstrip("@")

        result = AccountData(
            platform=self.platform,
            external_id=item.get("id", external_id),
            handle=handle,
            display_name=snippet.get("title", handle),
            followers=subs,
            following=0,
            posts_count=videos,
            total_views=views,
            engagement_rate=er,
            is_owned=bool(self.access_token),
            raw={
                "description": snippet.get("description", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "country": snippet.get("country", ""),
                "thumbnails": snippet.get("thumbnails", {}),
            },
        )
        self._save_to_cache(cache_key, result)
        return result

    def fetch_posts(
        self,
        external_id: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[PostData]:
        """
        Obtiene los videos más recientes del canal especificado.
        """
        cache_key = f"videos:{external_id}:{since}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        channel_id = external_id
        if not channel_id.startswith("UC"):
            acc = self.fetch_account(external_id)
            channel_id = acc.external_id

        self._consume_quota("search")
        service = self._get_service()

        search_kwargs: Dict[str, Any] = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": min(limit, 50),
            "order": "date",
            "type": "video",
        }
        if since:
            search_kwargs["publishedAfter"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            search_res = service.search().list(**search_kwargs).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en YouTube: {err_msg}", platform=self.platform, retry_after=86400) from exc
            raise

        items = search_res.get("items", [])
        if not items:
            return []

        video_ids = [it["id"]["videoId"] for it in items if "videoId" in it.get("id", {})]
        if not video_ids:
            return []

        self._consume_quota("videos")
        try:
            videos_res = service.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids),
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en YouTube: {err_msg}", platform=self.platform, retry_after=86400) from exc
            raise

        posts: List[PostData] = []
        for v_item in videos_res.get("items", []):
            v_id = v_item.get("id")
            v_snippet = v_item.get("snippet", {})
            v_stats = v_item.get("statistics", {})

            title = v_snippet.get("title", "")
            desc = v_snippet.get("description", "")
            full_text = f"{title}\n{desc}"
            hashtags = self._extract_hashtags(full_text)
            for tag in v_snippet.get("tags", []):
                clean_t = tag.lower().replace(" ", "")
                if clean_t not in hashtags:
                    hashtags.append(clean_t)

            published_at = self._parse_datetime(v_snippet.get("publishedAt"))

            posts.append(
                PostData(
                    external_post_id=v_id,
                    published_at=published_at,
                    views=int(v_stats.get("viewCount", 0)),
                    likes=int(v_stats.get("likeCount", 0)),
                    comments=int(v_stats.get("commentCount", 0)),
                    shares=0,
                    text=full_text,
                    hashtags=hashtags,
                    raw={"thumbnails": v_snippet.get("thumbnails", {})},
                )
            )

        self._save_to_cache(cache_key, posts)
        return posts

    def fetch_comments(
        self,
        post_id: str,
        limit: int = 100,
    ) -> List[CommentData]:
        """
        Obtiene comentarios públicos del video indicado.
        """
        cache_key = f"comments:{post_id}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        self._consume_quota("commentThreads")
        service = self._get_service()

        try:
            res = service.commentThreads().list(
                part="snippet",
                videoId=post_id,
                maxResults=min(limit, 100),
                textFormat="plainText",
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "commentsDisabled" in err_msg:
                return []
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en YouTube: {err_msg}", platform=self.platform, retry_after=86400) from exc
            if "404" in err_msg or "notFound" in err_msg:
                raise ProviderNotFoundError(f"Video '{post_id}' no encontrado en YouTube.", platform=self.platform) from exc
            raise

        comments: List[CommentData] = []
        for it in res.get("items", []):
            top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            author_ch = top.get("authorChannelId", {}).get("value", "")
            comments.append(
                CommentData(
                    comment_id=it.get("id", ""),
                    post_id=post_id,
                    author_id=author_ch,
                    author_name=top.get("authorDisplayName", "Anónimo"),
                    text=top.get("textDisplay", ""),
                    published_at=self._parse_datetime(top.get("publishedAt")),
                    likes=int(top.get("likeCount", 0)),
                    raw={"viewerRating": top.get("viewerRating", "")},
                )
            )

        self._save_to_cache(cache_key, comments)
        return comments

    def search_related(
        self,
        external_id: str,
        limit: int = 25,
    ) -> List[AccountData]:
        """
        Descubre canales relacionados a partir del canal objetivo.
        """
        acc = self.fetch_account(external_id)
        channel_title = acc.display_name

        self._consume_quota("search")
        service = self._get_service()

        try:
            res = service.search().list(
                part="snippet",
                q=channel_title,
                type="channel",
                maxResults=min(limit, 25),
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en YouTube: {err_msg}", platform=self.platform, retry_after=86400) from exc
            raise

        related_accounts: List[AccountData] = []
        for it in res.get("items", []):
            ch_id = it.get("id", {}).get("channelId")
            if not ch_id or ch_id == acc.external_id:
                continue
            snip = it.get("snippet", {})
            related_accounts.append(
                AccountData(
                    platform=self.platform,
                    external_id=ch_id,
                    handle=snip.get("channelTitle", ch_id),
                    display_name=snip.get("channelTitle", ch_id),
                    followers=0,
                    raw={"description": snip.get("description", "")},
                )
            )

        return related_accounts

    # ─── YouTube Analytics API v2 (Cuentas Propias con OAuth) ──────────────────

    def fetch_channel_daily_metrics(
        self,
        channel_id: Optional[str] = None,
        start_date: str = "2026-01-01",
        end_date: Optional[str] = None,
    ) -> List[YouTubeDailyMetric]:
        """
        Consulta la serie temporal diaria de métricas del canal propio:
        - Vistas y tiempo de visualización
        - Retención de audiencia promedio (averageViewPercentage y averageViewDuration)
        - Suscriptores ganados y perdidos
        - Impresiones y CTR
        """
        self._consume_quota("analytics")
        analytics = self._get_analytics_service()

        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metrics_req = (
            "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
            "subscribersGained,subscribersLost,impressions,impressionClickThroughRate"
        )
        ch_filter = f"channel=={channel_id}" if (channel_id and channel_id.startswith("UC")) else "channel==MINE"

        try:
            res = analytics.reports().query(
                ids=ch_filter,
                startDate=start_date,
                endDate=e_date,
                metrics=metrics_req,
                dimensions="day",
                sort="day",
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en Analytics API: {err_msg}", platform=self.platform) from exc
            if "401" in err_msg or "403" in err_msg or "invalid_grant" in err_msg:
                raise ProviderAuthError(f"Error de autorización en Analytics API: {err_msg}", platform=self.platform) from exc
            raise

        records = self._parse_result_table(res)
        daily_metrics: List[YouTubeDailyMetric] = []
        for rec in records:
            gained = int(rec.get("subscribersGained", 0))
            lost = int(rec.get("subscribersLost", 0))
            daily_metrics.append(
                YouTubeDailyMetric(
                    date=str(rec.get("day", "")),
                    views=int(rec.get("views", 0)),
                    watch_time_minutes=int(rec.get("estimatedMinutesWatched", 0)),
                    average_view_duration_seconds=int(rec.get("averageViewDuration", 0)),
                    average_view_percentage=float(rec.get("averageViewPercentage", 0.0)),
                    subscribers_gained=gained,
                    subscribers_lost=lost,
                    net_subscribers=gained - lost,
                    impressions=int(rec.get("impressions", 0)),
                    ctr=float(rec.get("impressionClickThroughRate", 0.0)),
                )
            )

        return daily_metrics

    def fetch_video_analytics(
        self,
        channel_id: Optional[str] = None,
        video_ids: Optional[List[str]] = None,
        start_date: str = "2005-09-01",
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> List[YouTubeVideoAnalytics]:
        """
        Obtiene métricas por video del canal propio:
        - Suscriptores ganados y perdidos por video
        - Retención de audiencia (%) y duración media
        - Impresiones y CTR
        """
        self._consume_quota("analytics")
        analytics = self._get_analytics_service()

        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ch_filter = f"channel=={channel_id}" if (channel_id and channel_id.startswith("UC")) else "channel==MINE"

        metrics_req = (
            "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
            "subscribersGained,subscribersLost,likes,comments,impressions,impressionClickThroughRate"
        )

        kwargs: Dict[str, Any] = {
            "ids": ch_filter,
            "startDate": start_date,
            "endDate": e_date,
            "metrics": metrics_req,
            "dimensions": "video",
            "sort": "-views",
            "maxResults": min(limit, 200),
        }
        if video_ids:
            kwargs["filters"] = f"video=={','.join(video_ids[:50])}"

        try:
            res = analytics.reports().query(**kwargs).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en Analytics API: {err_msg}", platform=self.platform) from exc
            if "401" in err_msg or "403" in err_msg:
                raise ProviderAuthError(f"Error de autorización en Analytics API: {err_msg}", platform=self.platform) from exc
            raise

        records = self._parse_result_table(res)
        results: List[YouTubeVideoAnalytics] = []
        for rec in records:
            gained = int(rec.get("subscribersGained", 0))
            lost = int(rec.get("subscribersLost", 0))
            results.append(
                YouTubeVideoAnalytics(
                    video_id=str(rec.get("video", "")),
                    views=int(rec.get("views", 0)),
                    watch_time_minutes=int(rec.get("estimatedMinutesWatched", 0)),
                    average_view_duration_seconds=int(rec.get("averageViewDuration", 0)),
                    retention_rate_pct=float(rec.get("averageViewPercentage", 0.0)),
                    subscribers_gained=gained,
                    subscribers_lost=lost,
                    net_subscribers=gained - lost,
                    likes=int(rec.get("likes", 0)),
                    comments=int(rec.get("comments", 0)),
                    impressions=int(rec.get("impressions", 0)),
                    ctr=float(rec.get("impressionClickThroughRate", 0.0)),
                )
            )

        return results

    def fetch_audience_retention(
        self,
        video_id: str,
        start_date: str = "2005-09-01",
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Obtiene la curva de retención de audiencia para un video específico:
        - elapsedVideoTimeRatio (0.0 a 1.0)
        - audienceWatchRatio (% de retención en cada punto)
        """
        self._consume_quota("analytics")
        analytics = self._get_analytics_service()

        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            res = analytics.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=e_date,
                metrics="audienceWatchRatio",
                dimensions="elapsedVideoTimeRatio",
                filters=f"video=={video_id}",
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en Analytics API: {err_msg}", platform=self.platform) from exc
            raise

        records = self._parse_result_table(res)
        curve: List[AudienceRetentionPoint] = []
        for r in records:
            curve.append(
                AudienceRetentionPoint(
                    ratio=float(r.get("elapsedVideoTimeRatio", 0.0)),
                    watch_ratio=float(r.get("audienceWatchRatio", 0.0)),
                )
            )

        avg_retention = round(sum(p.watch_ratio for p in curve) / len(curve) * 100, 2) if curve else 0.0

        return {
            "video_id": video_id,
            "average_retention_pct": avg_retention,
            "curve_points_count": len(curve),
            "retention_curve": curve,
        }

    def fetch_traffic_sources(
        self,
        channel_id: Optional[str] = None,
        start_date: str = "2026-01-01",
        end_date: Optional[str] = None,
    ) -> List[TrafficSourceItem]:
        """
        Obtiene las fuentes de tráfico hacia el canal:
        - YT_SEARCH, RELATED_VIDEO, SUBSCRIBER, EXT_URL, etc.
        """
        self._consume_quota("analytics")
        analytics = self._get_analytics_service()

        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ch_filter = f"channel=={channel_id}" if (channel_id and channel_id.startswith("UC")) else "channel==MINE"

        try:
            res = analytics.reports().query(
                ids=ch_filter,
                startDate=start_date,
                endDate=e_date,
                metrics="views,estimatedMinutesWatched",
                dimensions="insightTrafficSourceType",
                sort="-views",
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en Analytics API: {err_msg}", platform=self.platform) from exc
            raise

        records = self._parse_result_table(res)
        total_views = sum(int(r.get("views", 0)) for r in records)

        traffic_items: List[TrafficSourceItem] = []
        for r in records:
            v = int(r.get("views", 0))
            pct = round((v / total_views) * 100, 2) if total_views > 0 else 0.0
            traffic_items.append(
                TrafficSourceItem(
                    source_type=str(r.get("insightTrafficSourceType", "")),
                    views=v,
                    watch_time_minutes=int(r.get("estimatedMinutesWatched", 0)),
                    views_percentage=pct,
                )
            )

        return traffic_items

    def fetch_demographics(
        self,
        channel_id: Optional[str] = None,
        start_date: str = "2026-01-01",
        end_date: Optional[str] = None,
    ) -> List[DemographicsItem]:
        """
        Obtiene la distribución demográfica del canal (grupos de edad y género).
        """
        self._consume_quota("analytics")
        analytics = self._get_analytics_service()

        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ch_filter = f"channel=={channel_id}" if (channel_id and channel_id.startswith("UC")) else "channel==MINE"

        try:
            res = analytics.reports().query(
                ids=ch_filter,
                startDate=start_date,
                endDate=e_date,
                metrics="viewerPercentage",
                dimensions="ageGroup,gender",
                sort="ageGroup,gender",
            ).execute()
        except Exception as exc:
            err_msg = str(exc)
            if "quotaExceeded" in err_msg or "quota" in err_msg.lower():
                raise ProviderQuotaError(f"Cuota agotada en Analytics API: {err_msg}", platform=self.platform) from exc
            raise

        records = self._parse_result_table(res)
        demographics: List[DemographicsItem] = []
        for r in records:
            demographics.append(
                DemographicsItem(
                    age_group=str(r.get("ageGroup", "")),
                    gender=str(r.get("gender", "")),
                    viewer_percentage=float(r.get("viewerPercentage", 0.0)),
                )
            )

        return demographics

    def backfill_channel_history(
        self,
        channel_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        chunk_days: int = 365,
    ) -> BackfillResult:
        """
        Rellena el historial hacia atrás desde la creación del canal (o start_date)
        hasta la fecha final especificada.
        
        Permite a una cuenta nueva que arranca desde el 'día 0' recuperar todo su historial
        diario consolidado de impresiones, CTR, vistas y suscriptores sin intervención manual.
        """
        # Determinar fecha de inicio si no se proporciona
        actual_start = start_date
        if not actual_start:
            try:
                acc = self.fetch_account(channel_id)
                published_at_str = acc.raw.get("publishedAt", "")
                if published_at_str:
                    actual_start = published_at_str[:10]
            except Exception:
                pass

        if not actual_start:
            actual_start = "2005-09-01"  # Límite histórico absoluto de YouTube Analytics

        # Por latencia de YouTube Analytics (~48h), la fecha final óptima es ayer
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        actual_end = end_date or yesterday

        start_dt = datetime.strptime(actual_start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(actual_end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        if start_dt > end_dt:
            actual_start = actual_end
            start_dt = end_dt

        # Consultar en fragmentos/chunks para estabilidad
        current_chunk_start = start_dt
        all_metrics: List[YouTubeDailyMetric] = []

        while current_chunk_start <= end_dt:
            current_chunk_end = min(current_chunk_start + timedelta(days=chunk_days - 1), end_dt)
            chunk_start_str = current_chunk_start.strftime("%Y-%m-%d")
            chunk_end_str = current_chunk_end.strftime("%Y-%m-%d")

            metrics = self.fetch_channel_daily_metrics(
                channel_id=channel_id,
                start_date=chunk_start_str,
                end_date=chunk_end_str,
            )
            all_metrics.extend(metrics)

            current_chunk_start = current_chunk_end + timedelta(days=1)

        total_views = sum(m.views for m in all_metrics)
        total_watch = sum(m.watch_time_minutes for m in all_metrics)
        net_subs = sum(m.net_subscribers for m in all_metrics)
        total_impressions = sum(m.impressions for m in all_metrics)

        return BackfillResult(
            channel_id=channel_id,
            start_date=actual_start,
            end_date=actual_end,
            days_retrieved=len(all_metrics),
            total_views=total_views,
            total_watch_time_minutes=total_watch,
            net_subscribers=net_subs,
            total_impressions=total_impressions,
            daily_metrics=all_metrics,
        )
