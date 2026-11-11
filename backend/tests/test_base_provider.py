"""
test_base_provider.py — Pruebas del contrato DataProvider, dataclasses y excepciones.
"""

from datetime import datetime, timezone
import pytest
from app.providers.base import (
    DataProvider,
    AccountData,
    PostData,
    CommentData,
    ProviderError,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)


class DummyMockProvider:
    platform = "mock_platform"

    def fetch_account(self, external_id: str) -> AccountData:
        if external_id == "not_found":
            raise ProviderNotFoundError("Account not found", platform=self.platform)
        if external_id == "unauthorized":
            raise ProviderAuthError("Invalid credentials", platform=self.platform)
        if external_id == "quota_exceeded":
            raise ProviderQuotaError("Quota exceeded", platform=self.platform, retry_after=3600)

        return AccountData(
            platform=self.platform,
            external_id=external_id,
            handle="test_creator",
            display_name="Test Creator",
            followers=12500,
            following=150,
            posts_count=45,
            total_views=1000000,
            engagement_rate=3.5,
            is_owned=True,
        )

    def fetch_posts(self, external_id: str, since: datetime | None = None, limit: int = 50) -> list[PostData]:
        return [
            PostData(
                external_post_id="post_1",
                published_at=datetime.now(timezone.utc),
                views=5000,
                likes=300,
                comments=45,
                shares=12,
                text="Post de prueba #demo #trama",
                hashtags=["demo", "trama"],
            )
        ]

    def fetch_comments(self, post_id: str, limit: int = 100) -> list[CommentData]:
        return [
            CommentData(
                comment_id="comm_1",
                post_id=post_id,
                author_id="user_99",
                author_name="User 99",
                text="Excelente contenido",
                published_at=datetime.now(timezone.utc),
                likes=5,
            )
        ]

    def search_related(self, external_id: str, limit: int = 25) -> list[AccountData]:
        return [
            AccountData(
                platform=self.platform,
                external_id="related_1",
                handle="related_creator",
                display_name="Related Creator",
                followers=8000,
            )
        ]


def test_dummy_provider_implements_protocol():
    provider = DummyMockProvider()
    assert isinstance(provider, DataProvider)
    assert provider.platform == "mock_platform"


def test_fetch_account_success():
    provider = DummyMockProvider()
    acc = provider.fetch_account("creator_1")
    assert acc.external_id == "creator_1"
    assert acc.handle == "test_creator"
    assert acc.followers == 12500
    assert acc.is_owned is True


def test_fetch_posts_and_comments():
    provider = DummyMockProvider()
    posts = provider.fetch_posts("creator_1", limit=10)
    assert len(posts) == 1
    assert posts[0].external_post_id == "post_1"
    assert posts[0].hashtags == ["demo", "trama"]

    comments = provider.fetch_comments("post_1")
    assert len(comments) == 1
    assert comments[0].comment_id == "comm_1"
    assert comments[0].author_name == "User 99"


def test_search_related():
    provider = DummyMockProvider()
    related = provider.search_related("creator_1", limit=5)
    assert len(related) == 1
    assert related[0].external_id == "related_1"


def test_provider_errors():
    provider = DummyMockProvider()

    with pytest.raises(ProviderNotFoundError) as exc_info:
        provider.fetch_account("not_found")
    assert exc_info.value.platform == "mock_platform"

    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_account("unauthorized")
    assert "Invalid credentials" in str(exc_info.value)

    with pytest.raises(ProviderQuotaError) as exc_info:
        provider.fetch_account("quota_exceeded")
    assert exc_info.value.retry_after == 3600
