"""
test_api_contract.py — Validación del contrato de API HTTP para Sprint 5.5.
Verifica que OpenAPI liste todas las rutas y que devuelvan 501 en el esqueleto base.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_openapi_schema_contains_sprint_5_5_routes():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    expected_routes = [
        ("/accounts", ["post", "get"]),
        ("/accounts/{id}/snapshot", ["post"]),
        ("/accounts/{id}/growth", ["get"]),
        ("/oauth/{provider}/start", ["get"]),
        ("/oauth/{provider}/callback", ["get"]),
        ("/trends", ["get"]),
        ("/niches/discover", ["post"]),
        ("/niches/{id}", ["get"]),
    ]

    for path, methods in expected_routes:
        assert path in paths, f"Ruta {path} no encontrada en openapi.json"
        for method in methods:
            assert method in paths[path], f"Método {method.upper()} no encontrado en {path}"


def test_skeleton_routes_return_expected_status():
    headers = {"X-Project-Id": "demo-reforma-del-agua"}

    # Carril B: /accounts implementado
    r_post_accounts = client.post(
        "/accounts",
        json={"platform": "youtube", "external_id": "UC_contract_test", "is_owned": True},
        headers=headers,
    )
    assert r_post_accounts.status_code == 201

    r_get_accounts = client.get("/accounts", headers=headers)
    assert r_get_accounts.status_code == 200

    # Carril D & A: /oauth implementado para meta y google/youtube
    r_oauth_start = client.get("/oauth/meta/start", headers=headers)
    assert r_oauth_start.status_code == 200
    assert "authorization_url" in r_oauth_start.json()

    r_oauth_google_start = client.get("/oauth/google/start", headers=headers)
    assert r_oauth_google_start.status_code == 200
    assert "accounts.google.com" in r_oauth_google_start.json()["authorization_url"]

    r_oauth_yt_start = client.get("/oauth/youtube/start", headers=headers)
    assert r_oauth_yt_start.status_code == 200
    assert "accounts.google.com" in r_oauth_yt_start.json()["authorization_url"]

    r_oauth_callback = client.get("/oauth/meta/callback?code=test&state=abc")
    assert r_oauth_callback.status_code == 403  # State inválido rechazado anti-CSRF

    r_oauth_google_callback = client.get("/oauth/google/callback?code=test&state=abc")
    assert r_oauth_google_callback.status_code == 403  # State inválido rechazado anti-CSRF

    r_oauth_unsupported = client.get("/oauth/tiktok/start", headers=headers)
    assert r_oauth_unsupported.status_code == 400

    # Carril E, F: esqueletos pendientes de sub-sprint 5.5.2
    r_trends = client.get("/trends", headers=headers)
    assert r_trends.status_code == 501

    r_niches_discover = client.post(
        "/niches/discover",
        json={"seed_account_id": 1, "depth": 1},
        headers=headers,
    )
    assert r_niches_discover.status_code == 501

    r_niches_get = client.get("/niches/niche_1", headers=headers)
    assert r_niches_get.status_code == 501


def test_oauth_google_callback_success(monkeypatch):
    from app.oauth import generate_state_token
    from app.providers.youtube import YouTubeProvider

    project_id = "demo-reforma-del-agua"
    valid_state = generate_state_token(project_id)

    # Mock de intercambio de código
    def mock_exchange(*args, **kwargs):
        return {
            "access_token": "mock_google_access_token_xyz",
            "refresh_token": "mock_google_refresh_token_abc",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/yt-analytics.readonly",
        }

    monkeypatch.setattr(YouTubeProvider, "exchange_code_for_tokens", classmethod(mock_exchange))

    resp = client.get(f"/oauth/google/callback?code=mock_auth_code_123&state={valid_state}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "authorized"
    assert data["provider"] == "google"
    assert data["is_owned"] is True
    assert "access_token" not in data  # Token NUNCA devuelto por la API
    assert "refresh_token" not in data

