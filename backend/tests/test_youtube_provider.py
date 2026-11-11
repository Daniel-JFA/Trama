"""
test_youtube_provider.py — Pruebas unitarias para YouTubeProvider sin conexión a red.
Usa fixtures JSON almacenadas en backend/tests/fixtures/youtube/.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.providers.base import (
    DataProvider,
    AccountData,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)
from app.providers.youtube import YouTubeProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "youtube"


@pytest.fixture
def mock_youtube_service():
    """Crea un mock del cliente Google API Discovery usando las fixtures JSON."""
    service = MagicMock()

    # Fixture de canal
    with open(FIXTURES_DIR / "channel_sample.json") as f:
        channel_data = json.load(f)

    # Fixture de videos (search list)
    with open(FIXTURES_DIR / "videos_sample.json") as f:
        search_data = json.load(f)

    # Fixture de videos detail (videos list)
    videos_detail_data = {
        "items": [
            {
                "id": "vid_sample_101",
                "snippet": {
                    "publishedAt": "2026-11-01T12:00:00Z",
                    "title": "Intro to Graph Analysis in Python",
                    "description": "Learn network analysis with Python #network #graph",
                    "tags": ["network", "graph", "python"],
                },
                "statistics": {
                    "viewCount": "15000",
                    "likeCount": "1200",
                    "commentCount": "85",
                },
            },
            {
                "id": "vid_sample_102",
                "snippet": {
                    "publishedAt": "2026-11-05T15:30:00Z",
                    "title": "FastAPI and Columnar Analytics with DuckDB",
                    "description": "High performance queries #fastapi #duckdb",
                    "tags": ["fastapi", "duckdb"],
                },
                "statistics": {
                    "viewCount": "32000",
                    "likeCount": "2400",
                    "commentCount": "190",
                },
            },
        ]
    }

    # Fixture de comentarios
    with open(FIXTURES_DIR / "comments_sample.json") as f:
        comments_data = json.load(f)

    # Configurar mocks de llamadas encadenadas
    service.channels().list().execute.return_value = channel_data
    service.search().list().execute.return_value = search_data
    service.videos().list().execute.return_value = videos_detail_data
    service.commentThreads().list().execute.return_value = comments_data

    return service


def test_youtube_provider_implements_protocol(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)
    assert isinstance(provider, DataProvider)
    assert provider.platform == "youtube"


def test_fetch_account_success(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)
    acc = provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")

    assert acc.platform == "youtube"
    assert acc.external_id == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    assert acc.handle == "googledevelopers"
    assert acc.display_name == "Google Developers"
    assert acc.followers == 2350000
    assert acc.total_views == 250000000
    assert acc.posts_count == 6200
    assert acc.engagement_rate is not None
    assert provider.quota_used == 1


def test_fetch_account_not_found():
    empty_service = MagicMock()
    empty_service.channels().list().execute.return_value = {"items": []}

    provider = YouTubeProvider(api_key="fake_key", mock_client=empty_service)
    with pytest.raises(ProviderNotFoundError) as exc_info:
        provider.fetch_account("UC_non_existent")
    assert "no encontrado" in str(exc_info.value)


def test_fetch_posts_and_extract_hashtags(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)
    posts = provider.fetch_posts("UC_x5XG1OV2P6uZZ5FSM9Ttw", limit=10)

    assert len(posts) == 2
    p1 = posts[0]
    assert p1.external_post_id == "vid_sample_101"
    assert p1.views == 15000
    assert p1.likes == 1200
    assert "network" in p1.hashtags
    assert "graph" in p1.hashtags

    p2 = posts[1]
    assert p2.external_post_id == "vid_sample_102"
    assert "fastapi" in p2.hashtags
    assert "duckdb" in p2.hashtags


def test_fetch_comments(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)
    comments = provider.fetch_comments("vid_sample_101")

    assert len(comments) == 2
    c1 = comments[0]
    assert c1.comment_id == "UgxK4W3K111"
    assert c1.author_name == "DataAnalystPro"
    assert c1.likes == 12
    assert "DuckDB" in c1.text


def test_search_related(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)
    # Simular resultados de búsqueda de canales
    mock_youtube_service.search().list().execute.return_value = {
        "items": [
            {
                "id": {"channelId": "UC_related_001"},
                "snippet": {"channelTitle": "Python Core", "description": "Official Python channel"},
            },
            {
                "id": {"channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw"},  # El mismo canal semilla, debe excluirse
                "snippet": {"channelTitle": "Google Developers", "description": ""},
            },
            {
                "id": {"channelId": "UC_related_002"},
                "snippet": {"channelTitle": "FastAPI Devs", "description": "FastAPI tutorials"},
            },
        ]
    }

    related = provider.search_related("UC_x5XG1OV2P6uZZ5FSM9Ttw", limit=5)
    assert len(related) == 2
    assert related[0].external_id == "UC_related_001"
    assert related[1].external_id == "UC_related_002"


def test_quota_limit_exceeded(mock_youtube_service):
    # Cuota mínima de 2 unidades
    provider = YouTubeProvider(api_key="fake_key", quota_limit=2, mock_client=mock_youtube_service)

    # 1. Primera consulta de canal: consume 1 unidad (total 1/2) -> OK
    provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1

    # 2. Búsqueda de videos: requiere 100 unidades (1 + 100 > 2) -> QuotaExceeded
    with pytest.raises(ProviderQuotaError) as exc_info:
        provider.fetch_posts("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert exc_info.value.retry_after == 86400
    assert "Límite de cuota diaria" in str(exc_info.value)


def test_response_cache_prevents_duplicate_calls(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)

    acc1 = provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1

    # Segunda llamada inmediata al mismo canal: usa caché, no consume cuota extra
    acc2 = provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1
    assert acc1 == acc2


def test_missing_api_key_raises_auth_error(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    provider = YouTubeProvider(api_key=None)

    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_account("UC_test")
    assert "YOUTUBE_API_KEY no configurada" in str(exc_info.value)
