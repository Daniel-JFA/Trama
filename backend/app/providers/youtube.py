"""
youtube.py — Conector a YouTube Data API v3 con control de cuota y caché.
Carril A: YouTube Data API v3.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

import os
import re
import time
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


class YouTubeProvider:
    """
    Proveedor para YouTube Data API v3 que implementa el protocolo DataProvider.
    Maneja cuota diaria (por defecto 10.000 unidades), caché en memoria y mapeo canónico.
    """
    platform: str = "youtube"

    # Costos de cuota oficiales según YouTube Data API v3
    QUOTA_COSTS = {
        "channels": 1,
        "videos": 1,
        "commentThreads": 1,
        "search": 100,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        quota_limit: int = 10000,
        cache_ttl_seconds: int = 300,
        mock_client: Optional[Any] = None,
    ):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.quota_limit = quota_limit
        self.cache_ttl_seconds = cache_ttl_seconds
        self.quota_used = 0
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._mock_client = mock_client
        self._youtube_service = None

    def _get_service(self):
        """Inicializa el cliente de Google API Discovery de forma perezosa."""
        if self._mock_client:
            return self._mock_client
        if self._youtube_service:
            return self._youtube_service
        if not self.api_key:
            raise ProviderAuthError(
                "YOUTUBE_API_KEY no configurada en las variables de entorno.",
                platform=self.platform,
            )
        try:
            from googleapiclient.discovery import build
            self._youtube_service = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
            return self._youtube_service
        except Exception as exc:
            raise ProviderAuthError(f"Error al inicializar cliente de YouTube: {exc}", platform=self.platform) from exc

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
            # Reemplazar Z con +00:00 para datetime.fromisoformat
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
            # Reintentar por username si falló forHandle
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

        # Engagement rate aproximado: vistas promedio por video vs seguidores
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
            is_owned=False,
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

        # Obtener channel_id si se pasó un handle
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

        # Consultar estadísticas en lote (1 sola unidad de cuota para hasta 50 videos)
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
                    shares=0,  # YouTube API no expone métrica pública de shares
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
        Descubre canales relacionados o temáticamente afines a partir del canal objetivo.
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
