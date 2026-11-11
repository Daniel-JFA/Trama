"""
connectors.py — Conectores de ingesta masiva y streaming para TRAMA (Sprint 5 / Bloque D).
Soporta:
1. Bluesky Jetstream (WebSocket asíncrono con filtrado de hashtags y términos léxicos).
2. Telegram Export Parser (Análisis de forwards, réplicas y menciones de chats y canales).
3. X (Twitter) API v2 con control adaptativo de Rate Limiting y token bucket.
Todos los conectores son 100% testeables en local mediante fixtures y mocks sin requerir conexión a internet.
"""

import json
import re
import time
from typing import Dict, Any, List, Optional, Callable, AsyncIterable
from datetime import datetime, timezone

from .schemas import InteractionEvent


# ─── 1. Conector Bluesky Jetstream ──────────────────────────────────────────

class BlueskyJetstreamConnector:
    """
    Conector streaming para el Jetstream del protocolo AT de Bluesky.
    Parsea commits de creación de posts, reposiciones (reposts) y menciones.
    Permite filtrar en vuelo por hashtags o términos clave.
    """

    DEFAULT_ENDPOINT = "wss://jetstream1.us-east.bsky.network/subscribe"

    def __init__(self, hashtags: Optional[List[str]] = None, terms: Optional[List[str]] = None):
        self.hashtags = [h.lower().lstrip("#") for h in (hashtags or [])]
        self.terms = [t.lower() for t in (terms or [])]

    def matches_filter(self, text: str) -> bool:
        """Determina si un texto coincide con los filtros configurados (OR semántico)."""
        if not self.hashtags and not self.terms:
            return True
        if not text:
            return False

        lower_text = text.lower()

        # Chequeo de hashtags
        for tag in self.hashtags:
            pattern = rf"(?i)#{re.escape(tag)}"
            if re.search(pattern, lower_text):
                return True

        # Chequeo de términos
        for term in self.terms:
            if term in lower_text:
                return True

        return False

    def parse_event(self, raw_data: Dict[str, Any], project_id: Optional[str] = None) -> Optional[InteractionEvent]:
        """
        Parsea un payload JSON crudo proveniente de Jetstream y lo normaliza
        en un InteractionEvent canónico.
        """
        kind = raw_data.get("kind")
        if kind != "commit":
            return None

        commit = raw_data.get("commit", {})
        collection = commit.get("collection", "")
        record = commit.get("record", {})
        actor_did = raw_data.get("did", "did:unknown")
        time_us = raw_data.get("time_us")

        if time_us:
            # Microsegundos a ISO-8601
            dt = datetime.fromtimestamp(time_us / 1_000_000, tz=timezone.utc)
            timestamp_str = dt.isoformat()
        else:
            timestamp_str = record.get("createdAt") or datetime.now(timezone.utc).isoformat()

        if collection == "app.bsky.feed.post":
            text = record.get("text", "")
            if not self.matches_filter(text):
                return None

            reply_info = record.get("reply")
            target = None
            action_type = "post"

            if reply_info:
                action_type = "reply"
                parent_uri = reply_info.get("parent", {}).get("uri", "")
                if parent_uri.startswith("at://"):
                    # Extraer did del padre
                    target = parent_uri.split("/")[2]

            # Detectar menciones en facets si no es reply
            if not target and "facets" in record:
                for f in record.get("facets", []):
                    for feature in f.get("features", []):
                        if feature.get("$type") == "app.bsky.richtext.facet#mention":
                            target = feature.get("did")
                            action_type = "mention"
                            break

            return InteractionEvent(
                id=f"bsky-{raw_data.get('did', '')}-{commit.get('rkey', '')}",
                project_id=project_id,
                actor=actor_did,
                target=target,
                timestamp=timestamp_str,
                action_type=action_type,
                platform="bluesky",
                content=text,
                extra={"rkey": commit.get("rkey"), "collection": collection},
            )

        elif collection == "app.bsky.feed.repost":
            subject_uri = record.get("subject", {}).get("uri", "")
            target_did = None
            if subject_uri.startswith("at://"):
                target_did = subject_uri.split("/")[2]

            return InteractionEvent(
                id=f"bsky-repost-{raw_data.get('did', '')}-{commit.get('rkey', '')}",
                project_id=project_id,
                actor=actor_did,
                target=target_did,
                timestamp=timestamp_str,
                action_type="retweet",
                platform="bluesky",
                content="",
                extra={"subject_uri": subject_uri},
            )

        return None

    async def consume_stream(
        self,
        event_stream: AsyncIterable[str | Dict[str, Any]],
        callback: Callable[[InteractionEvent], Any],
        max_events: Optional[int] = None,
    ) -> int:
        """
        Consume eventos de un flujo asíncrono (Websocket real o fixture simulado).
        Invoca el callback con cada InteractionEvent que supere los filtros.
        """
        count = 0
        async for item in event_stream:
            data = json.loads(item) if isinstance(item, str) else item
            event = self.parse_event(data)
            if event:
                await callback(event) if hasattr(callback, "__await__") else callback(event)
                count += 1
                if max_events and count >= max_events:
                    break
        return count


# ─── 2. Conector Telegram Export Parser ─────────────────────────────────────

class TelegramExportParser:
    """
    Parsea exportaciones JSON generadas por Telegram Desktop (chats, canales, supergrupos).
    Identifica de forma canónica forwards, respuestas (replies) y menciones textuales.
    """

    def parse_data(self, data: Dict[str, Any], project_id: Optional[str] = None) -> List[InteractionEvent]:
        """Convierte una estructura JSON de exportación de Telegram en una lista de InteractionEvents."""
        events: List[InteractionEvent] = []
        channel_name = data.get("name", "Telegram Channel")
        channel_id = str(data.get("id", "telegram_chan"))
        messages = data.get("messages", [])

        for msg in messages:
            if msg.get("type") != "message":
                continue

            msg_id = str(msg.get("id", ""))
            raw_date = msg.get("date", "")
            # Normalizar timestamp a ISO con timezone UTC si falta
            if "T" in raw_date:
                timestamp = raw_date if ("+" in raw_date or "Z" in raw_date) else f"{raw_date}+00:00"
            else:
                timestamp = datetime.now(timezone.utc).isoformat()

            from_user = msg.get("from") or channel_name
            from_id = str(msg.get("from_id", channel_id))
            actor = f"tg:{from_user}"

            # Extraer contenido de texto (en Telegram puede ser string o lista de strings/objetos)
            raw_text = msg.get("text", "")
            if isinstance(raw_text, list):
                content = "".join([t if isinstance(t, str) else t.get("text", "") for t in raw_text])
            else:
                content = str(raw_text)

            # Caso 1: Forward (Reenvío coordinado)
            forwarded_from = msg.get("forwarded_from")
            if forwarded_from:
                events.append(
                    InteractionEvent(
                        id=f"tg-{channel_id}-{msg_id}",
                        project_id=project_id,
                        actor=actor,
                        target=f"tg:{forwarded_from}",
                        timestamp=timestamp,
                        action_type="forward",
                        platform="telegram",
                        content=content,
                        extra={"forwarded_from": forwarded_from, "msg_id": msg_id},
                    )
                )
                continue

            # Caso 2: Reply
            reply_to_id = msg.get("reply_to_message_id")
            if reply_to_id:
                events.append(
                    InteractionEvent(
                        id=f"tg-{channel_id}-{msg_id}",
                        project_id=project_id,
                        actor=actor,
                        target=f"tg:msg_{reply_to_id}",
                        timestamp=timestamp,
                        action_type="reply",
                        platform="telegram",
                        content=content,
                        extra={"reply_to_message_id": reply_to_id, "msg_id": msg_id},
                    )
                )
                continue

            # Caso 3: Mención en el texto (@usuario)
            mentions = re.findall(r"@([a-zA-Z0-9_]{3,32})", content)
            if mentions:
                for mention in mentions:
                    events.append(
                        InteractionEvent(
                            id=f"tg-{channel_id}-{msg_id}-mention-{mention}",
                            project_id=project_id,
                            actor=actor,
                            target=f"tg:{mention}",
                            timestamp=timestamp,
                            action_type="mention",
                            platform="telegram",
                            content=content,
                            extra={"msg_id": msg_id},
                        )
                    )
                continue

            # Caso 4: Publicación estándar
            events.append(
                InteractionEvent(
                    id=f"tg-{channel_id}-{msg_id}",
                    project_id=project_id,
                    actor=actor,
                    target=None,
                    timestamp=timestamp,
                    action_type="post",
                    platform="telegram",
                    content=content,
                    extra={"msg_id": msg_id},
                )
            )

        return events


# ─── 3. Conector X (Twitter) API v2 con Rate Limiting ────────────────────────

class RateLimitExceededError(Exception):
    def __init__(self, reset_at: float, message: str = "Límite de tasa (Rate Limit) alcanzado"):
        super().__init__(message)
        self.reset_at = reset_at


class TwitterV2Connector:
    """
    Conector para la API v2 de X (Twitter) con gestión de cuotas y Rate Limiting.
    Transforma payloads de tweets en el modelo InteractionEvent.
    """

    def __init__(self, bearer_token: Optional[str] = None, max_calls_per_window: int = 15):
        self.bearer_token = bearer_token
        self.max_calls = max_calls_per_window
        self.remaining_calls = max_calls_per_window
        self.reset_time = time.time() + 900  # Ventana de 15 minutos

    def check_rate_limit(self) -> None:
        """Verifica y actualiza la ventana de rate limit local."""
        now = time.time()
        if now >= self.reset_time:
            self.remaining_calls = self.max_calls
            self.reset_time = now + 900

        if self.remaining_calls <= 0:
            raise RateLimitExceededError(reset_at=self.reset_time)

    def record_call(self, response_headers: Optional[Dict[str, str]] = None) -> None:
        """Actualiza el estado del rate limit a partir de cabeceras de respuesta o decremento local."""
        if response_headers:
            remaining = response_headers.get("x-rate-limit-remaining")
            reset = response_headers.get("x-rate-limit-reset")
            if remaining is not None:
                self.remaining_calls = int(remaining)
            if reset is not None:
                self.reset_time = float(reset)
            return

        self.remaining_calls = max(0, self.remaining_calls - 1)

    def parse_tweet_object(self, tweet: Dict[str, Any], project_id: Optional[str] = None) -> List[InteractionEvent]:
        """Convierte un objeto tweet de Twitter API v2 en InteractionEvents canónicos."""
        events: List[InteractionEvent] = []
        author_id = tweet.get("author_id", "tw:unknown")
        actor = f"tw:{author_id}"
        tweet_id = tweet.get("id", "")
        text = tweet.get("text", "")
        timestamp = tweet.get("created_at") or datetime.now(timezone.utc).isoformat()

        ref_tweets = tweet.get("referenced_tweets", [])
        if ref_tweets:
            for ref in ref_tweets:
                ref_type = ref.get("type")
                ref_id = ref.get("id")
                target = f"tw:{ref_id}"

                action_map = {
                    "retweeted": "retweet",
                    "replied_to": "reply",
                    "quoted": "quote",
                }
                action_type = action_map.get(ref_type, "post")

                events.append(
                    InteractionEvent(
                        id=f"tw-{tweet_id}-{action_type}",
                        project_id=project_id,
                        actor=actor,
                        target=target,
                        timestamp=timestamp,
                        action_type=action_type,
                        platform="twitter",
                        content=text,
                        extra={"tweet_id": tweet_id, "ref_id": ref_id},
                    )
                )
        else:
            # Buscar menciones en entities
            entities = tweet.get("entities", {})
            mentions = entities.get("mentions", [])
            if mentions:
                for m in mentions:
                    events.append(
                        InteractionEvent(
                            id=f"tw-{tweet_id}-mention-{m.get('username')}",
                            project_id=project_id,
                            actor=actor,
                            target=f"tw:{m.get('username')}",
                            timestamp=timestamp,
                            action_type="mention",
                            platform="twitter",
                            content=text,
                            extra={"tweet_id": tweet_id},
                        )
                    )
            else:
                events.append(
                    InteractionEvent(
                        id=f"tw-{tweet_id}",
                        project_id=project_id,
                        actor=actor,
                        target=None,
                        timestamp=timestamp,
                        action_type="post",
                        platform="twitter",
                        content=text,
                        extra={"tweet_id": tweet_id},
                    )
                )

        return events
