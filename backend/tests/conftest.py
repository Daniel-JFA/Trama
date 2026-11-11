"""
conftest.py — Pytest fixtures for TRAMA backend tests.
Ensures tests use an isolated temporary SQLite database rather than production/local data.
Provides fixtures for Sprint 5.5 mock providers and tokens.
"""

import os
from datetime import datetime, timezone
from typing import List, Optional
import pytest
from app.storage import init_db
from app.providers.base import (
    DataProvider,
    AccountData,
    PostData,
    CommentData,
)
from app.crypto import generate_token_key


@pytest.fixture(autouse=True, scope="session")
def setup_test_database(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("trama_test")
    test_db_file = test_dir / "test_trama.db"
    os.environ["TRAMA_DB_PATH"] = str(test_db_file)
    os.environ.setdefault("TRAMA_TOKEN_KEY", generate_token_key())
    os.environ.setdefault("META_APP_ID", "dummy_meta_app_id_for_testing")
    os.environ.setdefault("META_APP_SECRET", "dummy_meta_app_secret_for_testing")
    init_db()
    yield


@pytest.fixture
def mock_token_key(monkeypatch):
    """Configura una clave válida TRAMA_TOKEN_KEY en el entorno de pruebas."""
    key = generate_token_key()
    monkeypatch.setenv("TRAMA_TOKEN_KEY", key)
    return key


@pytest.fixture
def sample_account_data() -> AccountData:
    return AccountData(
        platform="youtube",
        external_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        handle="googledevelopers",
        display_name="Google Developers",
        followers=2350000,
        following=0,
        posts_count=6200,
        total_views=250000000,
        engagement_rate=4.2,
        is_owned=True,
        raw={"country": "US"},
    )


@pytest.fixture
def sample_posts_data() -> List[PostData]:
    now = datetime.now(timezone.utc)
    return [
        PostData(
            external_post_id="vid_sample_101",
            published_at=now,
            views=15000,
            likes=1200,
            comments=85,
            shares=40,
            text="Intro to Graph Analysis #network #graph",
            hashtags=["network", "graph"],
        ),
        PostData(
            external_post_id="vid_sample_102",
            published_at=now,
            views=32000,
            likes=2400,
            comments=190,
            shares=110,
            text="FastAPI with DuckDB #fastapi #duckdb",
            hashtags=["fastapi", "duckdb"],
        ),
    ]


@pytest.fixture
def sample_comments_data() -> List[CommentData]:
    now = datetime.now(timezone.utc)
    return [
        CommentData(
            comment_id="comm_001",
            post_id="vid_sample_101",
            author_id="user_abc",
            author_name="Alice Dev",
            text="Excelente tutorial de igraph!",
            published_at=now,
            likes=15,
        ),
        CommentData(
            comment_id="comm_002",
            post_id="vid_sample_101",
            author_id="user_xyz",
            author_name="Bob Engineer",
            text="Muy claro el análisis de comunidades.",
            published_at=now,
            likes=7,
        ),
    ]


class MockGenericProvider:
    """Implementación de referencia de DataProvider para tests de los carriles."""
    platform = "mock_provider"

    def __init__(self, account: Optional[AccountData] = None, posts: Optional[List[PostData]] = None):
        self._account = account
        self._posts = posts or []

    def fetch_account(self, external_id: str) -> AccountData:
        if self._account and self._account.external_id == external_id:
            return self._account
        return AccountData(
            platform=self.platform,
            external_id=external_id,
            handle=f"user_{external_id}",
            display_name=f"Creator {external_id}",
            followers=10000,
        )

    def fetch_posts(self, external_id: str, since: Optional[datetime] = None, limit: int = 50) -> List[PostData]:
        return self._posts[:limit]

    def fetch_comments(self, post_id: str, limit: int = 100) -> List[CommentData]:
        return []

    def search_related(self, external_id: str, limit: int = 25) -> List[AccountData]:
        return [
            AccountData(
                platform=self.platform,
                external_id=f"related_{i}",
                handle=f"related_{i}",
                display_name=f"Related {i}",
                followers=5000 * i,
            )
            for i in range(1, min(limit + 1, 4))
        ]


@pytest.fixture
def mock_provider(sample_account_data, sample_posts_data) -> MockGenericProvider:
    return MockGenericProvider(account=sample_account_data, posts=sample_posts_data)
