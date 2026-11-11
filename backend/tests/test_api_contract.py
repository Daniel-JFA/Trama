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


def test_skeleton_routes_return_501():
    headers = {"X-Project-Id": "demo-reforma-del-agua"}

    r_post_accounts = client.post(
        "/accounts",
        json={"platform": "youtube", "external_id": "UC12345", "is_owned": True},
        headers=headers,
    )
    assert r_post_accounts.status_code == 501

    r_get_accounts = client.get("/accounts", headers=headers)
    assert r_get_accounts.status_code == 501

    r_snapshot = client.post("/accounts/1/snapshot", headers=headers)
    assert r_snapshot.status_code == 501

    r_growth = client.get("/accounts/1/growth", headers=headers)
    assert r_growth.status_code == 501

    r_oauth_start = client.get("/oauth/meta/start", headers=headers)
    assert r_oauth_start.status_code == 501

    r_oauth_callback = client.get("/oauth/meta/callback?code=test&state=abc")
    assert r_oauth_callback.status_code == 501

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
