"""
test_ingesta_columnar.py — Tests exhaustivos para el Sprint 5 / Bloque D:
1. Modelo Canónico InteractionEvent.
2. Conectores: Bluesky Jetstream, Telegram Export Parser y Twitter API v2 con Rate Limiting.
3. Persistencia en Parquet particionado y Analítica DuckDB (minuto, rolling windows, top actors).
4. Endpoints FastAPI de ingesta y analítica.
Todos los tests se ejecutan 100% en local con fixtures, sin requerir conexión a internet.
"""

import os
import shutil
import tempfile
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.schemas import InteractionEvent
from app.connectors import (
    BlueskyJetstreamConnector,
    TelegramExportParser,
    TwitterV2Connector,
    RateLimitExceededError,
)
from app.columnar import (
    save_events_to_parquet,
    ColumnarAnalytics,
    get_duckdb_connection,
)
from app.main import app

client = TestClient(app)


# ─── 1. Tests del Modelo Canónico ────────────────────────────────────────────

def test_canonical_interaction_event_creation():
    ev = InteractionEvent(
        id="ev-123",
        project_id="test_proj",
        actor="user_alice",
        target="user_bob",
        timestamp="2026-05-10T14:30:00Z",
        action_type="retweet",
        platform="bluesky",
        content="Mensaje de prueba",
        extra={"meta": "demo"},
    )
    assert ev.actor == "user_alice"
    assert ev.target == "user_bob"
    assert ev.action_type == "retweet"
    assert ev.platform == "bluesky"
    assert ev.content == "Mensaje de prueba"


# ─── 2. Tests del Conector Bluesky Jetstream ─────────────────────────────────

def test_bluesky_jetstream_filtering_and_parsing():
    connector = BlueskyJetstreamConnector(hashtags=["elecciones", "fraude"], terms=["debate"])

    # Evento con hashtag coincidente
    raw_post_match = {
        "did": "did:plc:actor1",
        "time_us": 1778400000000000,
        "kind": "commit",
        "commit": {
            "collection": "app.bsky.feed.post",
            "rkey": "3kxyz",
            "record": {
                "createdAt": "2026-05-10T12:00:00Z",
                "text": "Atentos a las nuevas revelaciones sobre las #Elecciones2026!",
                "reply": {
                    "parent": {"uri": "at://did:plc:target_candidate/app.bsky.feed.post/999"}
                },
            },
        },
    }

    ev = connector.parse_event(raw_post_match, project_id="proj_bsky")
    assert ev is not None
    assert ev.actor == "did:plc:actor1"
    assert ev.target == "did:plc:target_candidate"
    assert ev.action_type == "reply"
    assert ev.platform == "bluesky"
    assert "revelaciones" in ev.content

    # Evento que no coincide con los filtros
    raw_unrelated = {
        "did": "did:plc:actor2",
        "kind": "commit",
        "commit": {
            "collection": "app.bsky.feed.post",
            "record": {"text": "Receta para hacer pasta al pesto casera"},
        },
    }
    assert connector.parse_event(raw_unrelated) is None

    # Evento de Repost (amplificación)
    raw_repost = {
        "did": "did:plc:amplifier",
        "time_us": 1778400100000000,
        "kind": "commit",
        "commit": {
            "collection": "app.bsky.feed.repost",
            "rkey": "rep1",
            "record": {
                "subject": {"uri": "at://did:plc:influencer/app.bsky.feed.post/888"}
            },
        },
    }
    ev_repost = connector.parse_event(raw_repost)
    assert ev_repost is not None
    assert ev_repost.actor == "did:plc:amplifier"
    assert ev_repost.target == "did:plc:influencer"
    assert ev_repost.action_type == "retweet"


# ─── 3. Tests del Conector Telegram Export Parser ────────────────────────────

def test_telegram_export_parser():
    parser = TelegramExportParser()
    sample_tg_data = {
        "name": "Canal Político Central",
        "id": 987654,
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date": "2026-05-10T10:00:00",
                "from": "Canal Político Central",
                "forwarded_from": "Canal Matriz Primario",
                "text": "Comunicado urgente reenviado para viralizar.",
            },
            {
                "id": 2,
                "type": "message",
                "date": "2026-05-10T10:05:00",
                "from": "Operador_01",
                "reply_to_message_id": 1,
                "text": "Confirmado, ejecutando despliegue.",
            },
            {
                "id": 3,
                "type": "message",
                "date": "2026-05-10T10:10:00",
                "from": "Analista",
                "text": "Alerta sobre las declaraciones de @candidato_oficial en el debate.",
            },
        ],
    }

    events = parser.parse_data(sample_tg_data, project_id="proj_tg")
    assert len(events) == 3

    # Forward
    assert events[0].action_type == "forward"
    assert events[0].target == "tg:Canal Matriz Primario"
    assert events[0].platform == "telegram"

    # Reply
    assert events[1].action_type == "reply"
    assert events[1].target == "tg:msg_1"

    # Mention
    assert events[2].action_type == "mention"
    assert events[2].target == "tg:candidato_oficial"


# ─── 4. Tests del Conector Twitter API v2 con Rate Limiting ──────────────────

def test_twitter_v2_connector_and_rate_limiting():
    connector = TwitterV2Connector(max_calls_per_window=2)

    tweet_data = {
        "id": "tweet_12345",
        "author_id": "usr_bot99",
        "text": "RT masivo coordinado",
        "created_at": "2026-05-10T11:00:00Z",
        "referenced_tweets": [{"type": "retweeted", "id": "tweet_original_001"}],
    }

    events = connector.parse_tweet_object(tweet_data)
    assert len(events) == 1
    assert events[0].actor == "tw:usr_bot99"
    assert events[0].target == "tw:tweet_original_001"
    assert events[0].action_type == "retweet"

    # Test de Rate Limiting
    connector.check_rate_limit()
    connector.record_call()
    assert connector.remaining_calls == 1

    connector.check_rate_limit()
    connector.record_call()
    assert connector.remaining_calls == 0

    # Tercera llamada debe fallar con RateLimitExceededError
    with pytest.raises(RateLimitExceededError):
        connector.check_rate_limit()


# ─── 5. Tests de Persistencia Parquet y Analítica Columnar DuckDB ─────────────

def test_parquet_and_duckdb_analytics():
    temp_dir = tempfile.mkdtemp(prefix="trama_test_parquet_")
    try:
        events = [
            InteractionEvent(
                actor=f"user_{i%5}",
                target=f"target_{i%3}",
                timestamp=f"2026-05-10T12:{i%60:02d}:00Z",
                action_type="retweet" if i % 2 == 0 else "reply",
                platform="bluesky",
                content=f"Evento número {i}",
                project_id="proj_columnar_test",
            )
            for i in range(120)
        ]

        # Guardar en parquet particionado
        saved_count = save_events_to_parquet(events, base_dir=temp_dir, default_project_id="proj_columnar_test")
        assert saved_count == 120

        analytics = ColumnarAnalytics(base_dir=temp_dir)

        # 1. Agregación por minuto
        min_res = analytics.aggregate_by_minute("proj_columnar_test")
        assert len(min_res) > 0
        assert sum(r["event_count"] for r in min_res) == 120

        # 2. Rolling windows
        rolling_res = analytics.rolling_windows("proj_columnar_test", window_minutes=15)
        assert len(rolling_res) > 0
        assert "rolling_volume" in rolling_res[0]

        # 3. Top actors
        actors_res = analytics.top_actors("proj_columnar_test", limit=5)
        assert len(actors_res) <= 5
        assert actors_res[0]["total_actions"] > 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ─── 6. Tests de Integración Endpoints FastAPI ────────────────────────────────

def test_endpoints_ingest_and_analytics():
    events_payload = {
        "project_id": "proj_api_test",
        "events": [
            {
                "actor": "bot_agent_1",
                "target": "victim_target",
                "timestamp": "2026-05-10T15:00:00Z",
                "action_type": "mention",
                "platform": "twitter",
                "content": "Ataque coordinado",
            },
            {
                "actor": "bot_agent_2",
                "target": "victim_target",
                "timestamp": "2026-05-10T15:01:00Z",
                "action_type": "retweet",
                "platform": "bluesky",
                "content": "Amplificación",
            },
        ],
    }

    # Ingesta
    res = client.post("/api/ingest/events", json=events_payload)
    assert res.status_code == 200
    assert res.json()["ingested_count"] == 2

    # Consultas analíticas
    q_payload = {"project_id": "proj_api_test", "window_minutes": 10}
    res_min = client.post("/api/analytics/minute", json=q_payload)
    assert res_min.status_code == 200

    res_roll = client.post("/api/analytics/rolling", json=q_payload)
    assert res_roll.status_code == 200

    res_top = client.post("/api/analytics/top-actors", json=q_payload)
    assert res_top.status_code == 200
    assert "top_actors" in res_top.json()
