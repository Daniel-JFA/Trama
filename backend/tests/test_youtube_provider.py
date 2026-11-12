"""
test_youtube_provider.py — Pruebas unitarias para YouTubeProvider sin conexión a red.
Carril A: YouTube Data API v3 + OAuth + YouTube Analytics API v2.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.providers.base import (
    DataProvider,
    AccountData,
    PostData,
    CommentData,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)
from app.providers.youtube import (
    YouTubeProvider,
    YouTubeDailyMetric,
    YouTubeVideoAnalytics,
    TrafficSourceItem,
    DemographicsItem,
    AudienceRetentionPoint,
    BackfillResult,
    GOOGLE_OAUTH_SCOPES,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "youtube"


# ─── Fixtures de Mocks para Data API v3 y Analytics API v2 ───────────────────

@pytest.fixture
def mock_youtube_service():
    """Crea un mock del cliente Google API Discovery para Data API v3."""
    service = MagicMock()

    with open(FIXTURES_DIR / "channel_sample.json") as f:
        channel_data = json.load(f)

    with open(FIXTURES_DIR / "videos_sample.json") as f:
        search_data = json.load(f)

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

    with open(FIXTURES_DIR / "comments_sample.json") as f:
        comments_data = json.load(f)

    service.channels().list().execute.return_value = channel_data
    service.search().list().execute.return_value = search_data
    service.videos().list().execute.return_value = videos_detail_data
    service.commentThreads().list().execute.return_value = comments_data

    return service


@pytest.fixture
def mock_analytics_service():
    """Crea un mock del cliente Google API Discovery para YouTube Analytics API v2."""
    service = MagicMock()

    with open(FIXTURES_DIR / "analytics_channel_daily.json") as f:
        daily_data = json.load(f)

    with open(FIXTURES_DIR / "analytics_video_metrics.json") as f:
        video_data = json.load(f)

    with open(FIXTURES_DIR / "analytics_traffic_sources.json") as f:
        traffic_data = json.load(f)

    with open(FIXTURES_DIR / "analytics_demographics.json") as f:
        demo_data = json.load(f)

    with open(FIXTURES_DIR / "analytics_audience_retention.json") as f:
        retention_data = json.load(f)

    def side_effect_reports_query(**kwargs):
        mock_exec = MagicMock()
        dimensions = kwargs.get("dimensions", "")
        metrics = kwargs.get("metrics", "")
        filters = kwargs.get("filters", "")

        if dimensions == "day":
            mock_exec.execute.return_value = daily_data
        elif dimensions == "video":
            mock_exec.execute.return_value = video_data
        elif dimensions == "insightTrafficSourceType":
            mock_exec.execute.return_value = traffic_data
        elif dimensions == "ageGroup,gender":
            mock_exec.execute.return_value = demo_data
        elif dimensions == "elapsedVideoTimeRatio":
            mock_exec.execute.return_value = retention_data
        else:
            mock_exec.execute.return_value = daily_data
        return mock_exec

    service.reports().query.side_effect = side_effect_reports_query
    return service


# ─── Tests de Data API v3 (Protocolo DataProvider) ───────────────────────────

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
    mock_youtube_service.search().list().execute.return_value = {
        "items": [
            {
                "id": {"channelId": "UC_related_001"},
                "snippet": {"channelTitle": "Python Core", "description": "Official Python channel"},
            },
            {
                "id": {"channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw"},
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
    provider = YouTubeProvider(api_key="fake_key", quota_limit=2, mock_client=mock_youtube_service)

    provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1

    with pytest.raises(ProviderQuotaError) as exc_info:
        provider.fetch_posts("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert exc_info.value.retry_after == 86400
    assert "Límite de cuota diaria" in str(exc_info.value)


def test_response_cache_prevents_duplicate_calls(mock_youtube_service):
    provider = YouTubeProvider(api_key="fake_key", mock_client=mock_youtube_service)

    acc1 = provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1

    acc2 = provider.fetch_account("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert provider.quota_used == 1
    assert acc1 == acc2


def test_missing_api_key_raises_auth_error(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    provider = YouTubeProvider(api_key=None)

    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_account("UC_test")
    assert "YOUTUBE_API_KEY" in str(exc_info.value)


# ─── Tests de Google OAuth2 para YouTube ─────────────────────────────────────

def test_get_google_auth_url():
    auth_url = YouTubeProvider.get_google_auth_url(
        project_id="proj_trama_01",
        redirect_uri="http://localhost:8000/oauth/google/callback",
        client_id="mock_client_id_123.apps.googleusercontent.com",
    )
    assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "client_id=mock_client_id_123" in auth_url
    assert "access_type=offline" in auth_url
    assert "prompt=consent" in auth_url
    assert "response_type=code" in auth_url
    assert "yt-analytics.readonly" in auth_url
    assert "youtube.readonly" in auth_url


def test_get_google_auth_url_missing_client_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(ValueError) as exc_info:
        YouTubeProvider.get_google_auth_url(
            project_id="proj_01",
            redirect_uri="http://localhost:8000/oauth/google/callback",
            client_id=None,
        )
    assert "GOOGLE_OAUTH_CLIENT_ID" in str(exc_info.value)


def test_exchange_code_for_tokens():
    mock_http = MagicMock()
    with open(FIXTURES_DIR / "oauth_token_response.json") as f:
        token_payload = json.load(f)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = token_payload
    mock_http.post.return_value = mock_resp

    tokens = YouTubeProvider.exchange_code_for_tokens(
        code="mock_auth_code_xyz",
        redirect_uri="http://localhost:8000/oauth/google/callback",
        client_id="test_client_id",
        client_secret="test_client_secret",
        http_client=mock_http,
    )

    assert tokens["access_token"] == "ya29.sample_mock_oauth_access_token_for_tests"
    assert tokens["refresh_token"] == "1//sample_mock_refresh_token_for_tests"
    assert tokens["expires_in"] == 3599


def test_refresh_google_token():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "ya29.new_refreshed_access_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_http.post.return_value = mock_resp

    res = YouTubeProvider.refresh_google_token(
        refresh_token="1//mock_refresh",
        client_id="test_client_id",
        client_secret="test_client_secret",
        http_client=mock_http,
    )
    assert res["access_token"] == "ya29.new_refreshed_access_token"


# ─── Tests de YouTube Analytics API v2 ───────────────────────────────────────

def test_analytics_requires_oauth_token():
    provider = YouTubeProvider(api_key="public_key_only", access_token=None)
    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_channel_daily_metrics()
    assert "requiere autorización OAuth" in str(exc_info.value)


def test_fetch_channel_daily_metrics(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        mock_analytics_client=mock_analytics_service,
    )
    metrics = provider.fetch_channel_daily_metrics(
        channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        start_date="2026-11-01",
        end_date="2026-11-03",
    )

    assert len(metrics) == 3
    m1 = metrics[0]
    assert isinstance(m1, YouTubeDailyMetric)
    assert m1.date == "2026-11-01"
    assert m1.views == 1250
    assert m1.watch_time_minutes == 4375
    assert m1.average_view_duration_seconds == 210
    assert m1.average_view_percentage == 52.5
    assert m1.subscribers_gained == 38
    assert m1.subscribers_lost == 3
    assert m1.net_subscribers == 35
    assert m1.impressions == 25000
    assert m1.ctr == 5.0
    assert provider.quota_used == 1


def test_fetch_video_analytics(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        mock_analytics_client=mock_analytics_service,
    )
    video_metrics = provider.fetch_video_analytics(
        channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        video_ids=["vid_sample_101", "vid_sample_102"],
    )

    assert len(video_metrics) == 2
    v1 = video_metrics[0]
    assert isinstance(v1, YouTubeVideoAnalytics)
    assert v1.video_id == "vid_sample_101"
    assert v1.views == 15000
    assert v1.retention_rate_pct == 52.5
    assert v1.subscribers_gained == 350
    assert v1.subscribers_lost == 22
    assert v1.net_subscribers == 328
    assert v1.impressions == 250000
    assert v1.ctr == 6.0

    v2 = video_metrics[1]
    assert v2.video_id == "vid_sample_102"
    assert v2.views == 32000
    assert v2.retention_rate_pct == 60.0
    assert v2.net_subscribers == 775
    assert v2.ctr == 8.0


def test_fetch_audience_retention_curve(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        mock_analytics_client=mock_analytics_service,
    )
    retention_info = provider.fetch_audience_retention(video_id="vid_sample_101")

    assert retention_info["video_id"] == "vid_sample_101"
    assert retention_info["curve_points_count"] == 11
    assert retention_info["average_retention_pct"] > 0
    curve = retention_info["retention_curve"]
    assert isinstance(curve[0], AudienceRetentionPoint)
    assert curve[0].ratio == 0.0
    assert curve[0].watch_ratio == 1.0
    assert curve[-1].ratio == 1.0


def test_fetch_traffic_sources(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        mock_analytics_client=mock_analytics_service,
    )
    sources = provider.fetch_traffic_sources(channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

    assert len(sources) == 5
    s1 = sources[0]
    assert isinstance(s1, TrafficSourceItem)
    assert s1.source_type == "YT_SEARCH"
    assert s1.views == 24000
    assert s1.views_percentage > 0
    assert sum(s.views_percentage for s in sources) == pytest.approx(100.0, rel=1e-1)


def test_fetch_demographics(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        mock_analytics_client=mock_analytics_service,
    )
    demo = provider.fetch_demographics(channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

    assert len(demo) == 6
    d1 = demo[0]
    assert isinstance(d1, DemographicsItem)
    assert d1.age_group == "age18-24"
    assert d1.gender == "male"
    assert d1.viewer_percentage == 24.5


def test_backfill_channel_history(mock_youtube_service, mock_analytics_service):
    provider = YouTubeProvider(
        api_key="fake_key",
        access_token="mock_token",
        mock_client=mock_youtube_service,
        mock_analytics_client=mock_analytics_service,
    )

    backfill: BackfillResult = provider.backfill_channel_history(
        channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        start_date="2026-11-01",
        end_date="2026-11-03",
        chunk_days=30,
    )

    assert isinstance(backfill, BackfillResult)
    assert backfill.channel_id == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    assert backfill.start_date == "2026-11-01"
    assert backfill.end_date == "2026-11-03"
    assert backfill.days_retrieved == 3
    assert backfill.total_views == 1250 + 1420 + 1100
    assert backfill.total_impressions == 25000 + 28400 + 22000
    assert backfill.net_subscribers == 35 + 43 + 25
    assert len(backfill.daily_metrics) == 3


def test_analytics_quota_exceeded(mock_analytics_service):
    provider = YouTubeProvider(
        access_token="mock_token",
        quota_limit=1,
        mock_analytics_client=mock_analytics_service,
    )
    # Primera consulta gasta 1 unidad (total 1/1)
    provider.fetch_channel_daily_metrics()

    # Segunda consulta excede la cuota
    with pytest.raises(ProviderQuotaError) as exc_info:
        provider.fetch_traffic_sources()
    assert exc_info.value.retry_after == 86400
