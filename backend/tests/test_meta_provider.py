"""
test_meta_provider.py — Pruebas unitarias para MetaProvider (Instagram/Facebook) y flujo OAuth2.
Pruebas 100% aisladas sin conexión a red, utilizando fixtures JSON.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import (
    DataProvider,
    AccountData,
    ProviderAuthError,
    ProviderQuotaError,
    ProviderNotFoundError,
)
from app.providers.meta import MetaProvider
from app.oauth import (
    generate_state_token,
    verify_state_token,
    get_meta_auth_url,
    store_oauth_credential,
    get_decrypted_token,
)
from app.models import OAuthCredential
from app.database import SessionLocal

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "meta"


@pytest.fixture
def mock_meta_client():
    """Mock de cliente HTTP para simular respuestas de Meta Graph API."""
    mock = MagicMock()

    with open(FIXTURES_DIR / "instagram_user_sample.json") as f:
        ig_user = json.load(f)

    with open(FIXTURES_DIR / "facebook_page_sample.json") as f:
        fb_page = json.load(f)

    with open(FIXTURES_DIR / "instagram_media_sample.json") as f:
        ig_media = json.load(f)

    def mock_get(url, params=None):
        resp = MagicMock()
        url_str = str(url)

        if "17841400000000001/media" in url_str:
            resp.json.return_value = ig_media
        elif "17841400000000001" in url_str:
            resp.json.return_value = ig_user
        elif "100987654321001" in url_str:
            resp.json.return_value = fb_page
        else:
            resp.json.return_value = {"error": {"code": 803, "message": "Object does not exist"}}
        return resp

    mock.get.side_effect = mock_get
    return mock


def test_meta_provider_implements_protocol(mock_meta_client):
    ig_prov = MetaProvider(platform="instagram", access_token="fake_token", mock_client=mock_meta_client)
    assert isinstance(ig_prov, DataProvider)
    assert ig_prov.platform == "instagram"

    fb_prov = MetaProvider(platform="facebook", access_token="fake_token", mock_client=mock_meta_client)
    assert isinstance(fb_prov, DataProvider)
    assert fb_prov.platform == "facebook"


def test_fetch_instagram_account(mock_meta_client):
    provider = MetaProvider(platform="instagram", access_token="fake_token", mock_client=mock_meta_client)
    acc = provider.fetch_account("17841400000000001")

    assert acc.platform == "instagram"
    assert acc.external_id == "17841400000000001"
    assert acc.handle == "trama_investigation"
    assert acc.followers == 8420
    assert acc.following == 310
    assert acc.posts_count == 142


def test_fetch_facebook_page(mock_meta_client):
    provider = MetaProvider(platform="facebook", access_token="fake_token", mock_client=mock_meta_client)
    acc = provider.fetch_account("100987654321001")

    assert acc.platform == "facebook"
    assert acc.external_id == "100987654321001"
    assert acc.handle == "tramaproject"
    assert acc.followers == 13400


def test_fetch_instagram_posts_and_hashtags(mock_meta_client):
    provider = MetaProvider(platform="instagram", access_token="fake_token", mock_client=mock_meta_client)
    posts = provider.fetch_posts("17841400000000001", limit=5)

    assert len(posts) == 2
    p1 = posts[0]
    assert p1.external_post_id == "17923456789012345"
    assert p1.likes == 850
    assert p1.comments == 92
    assert "osint" in p1.hashtags
    assert "trama" in p1.hashtags

    p2 = posts[1]
    assert "leiden" in p2.hashtags
    assert "fastapi" in p2.hashtags


def test_meta_error_token_expired():
    mock_client = MagicMock()
    with open(FIXTURES_DIR / "error_token_expired.json") as f:
        err_data = json.load(f)
    mock_client.get().json.return_value = err_data

    provider = MetaProvider(platform="instagram", access_token="expired_token", mock_client=mock_client)

    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_account("any_id")
    assert "expirado o inválido" in str(exc_info.value)


def test_meta_error_rate_limit():
    mock_client = MagicMock()
    with open(FIXTURES_DIR / "error_rate_limit.json") as f:
        err_data = json.load(f)
    mock_client.get().json.return_value = err_data

    provider = MetaProvider(platform="instagram", access_token="valid_token", mock_client=mock_client)

    with pytest.raises(ProviderQuotaError) as exc_info:
        provider.fetch_account("any_id")
    assert exc_info.value.retry_after == 3600
    assert "Límite de tasa" in str(exc_info.value)


def test_meta_error_permissions():
    mock_client = MagicMock()
    with open(FIXTURES_DIR / "error_permissions.json") as f:
        err_data = json.load(f)
    mock_client.get().json.return_value = err_data

    provider = MetaProvider(platform="instagram", access_token="token_missing_scope", mock_client=mock_client)

    with pytest.raises(ProviderAuthError) as exc_info:
        provider.fetch_account("any_id")
    assert "Permisos insuficientes" in str(exc_info.value)


def test_state_token_generation_and_verification():
    project_id = "test_investigation_proj"
    state = generate_state_token(project_id)

    assert isinstance(state, str)
    assert project_id in state

    # Validación exitosa
    extracted = verify_state_token(state)
    assert extracted == project_id

    # Manipulación anti-CSRF debe fallar
    tampered = state + "bad"
    assert verify_state_token(tampered) is None

    # Formato inválido debe fallar
    assert verify_state_token("invalid_state_format") is None


def test_oauth_token_encryption_in_repository(setup_test_database, mock_token_key):
    db = SessionLocal()
    try:
        raw_token = "EAABwzLIXnjYBO123456789LongTokenSecretXYZ"
        account_id = 9999

        # Almacenar credencial
        cred = store_oauth_credential(
            account_id=account_id,
            provider="meta",
            access_token=raw_token,
            expires_in_seconds=3600,
            scopes="instagram_basic,pages_show_list",
            db=db,
        )

        assert cred.id is not None
        # Verificar que el token en DB está cifrado y NO en texto plano
        assert cred.access_token_enc != raw_token
        assert raw_token not in cred.access_token_enc

        # Descifrar y recuperar token original
        decrypted = get_decrypted_token(account_id=account_id, provider="meta", db=db)
        assert decrypted == raw_token
    finally:
        db.close()


def test_oauth_routes_start_and_callback_csrf(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "123456789012345")
    headers = {"X-Project-Id": "demo-reforma-del-agua"}

    # 1. /oauth/meta/start retorna URL con state
    start_resp = client.get("/oauth/meta/start", headers=headers)
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert "authorization_url" in data
    assert "dialog/oauth" in data["authorization_url"]
    assert "state=" in data["authorization_url"]

    # 2. /oauth/meta/callback con state inválido retorna 403 Forbidden
    callback_resp = client.get("/oauth/meta/callback?code=fake_code&state=fake_state")
    assert callback_resp.status_code == 403
    assert "anti-CSRF" in callback_resp.json()["detail"]
