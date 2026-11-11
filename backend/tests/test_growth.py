"""
test_growth.py — Pruebas unitarias y de integración para servicios y router de crecimiento (Carril B).
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Account, AccountSnapshot, PostSnapshot
from app.database import SessionLocal
from app.growth import (
    create_account,
    list_accounts,
    take_account_snapshot,
    get_growth_series,
)
from app.scheduler import SnapshotScheduler
from app.providers.base import AccountData, PostData, ProviderQuotaError

client = TestClient(app)


def test_create_and_list_accounts(setup_test_database):
    db = SessionLocal()
    uid = uuid.uuid4().hex[:6]
    proj_id = f"proj_alpha_{uid}"
    try:
        acc1 = create_account(
            project_id=proj_id,
            platform="youtube",
            external_id=f"UC_alpha_{uid}",
            handle=f"alpha_creator_{uid}",
            display_name="Alpha Creator",
            is_owned=True,
            db=db,
        )
        assert acc1.id is not None
        assert acc1.handle == f"alpha_creator_{uid}"

        # Intento de duplicado: debe retornar la existente sin error
        acc1_dup = create_account(
            project_id=proj_id,
            platform="youtube",
            external_id=f"UC_alpha_{uid}",
            handle=f"alpha_creator_updated_{uid}",
            db=db,
        )
        assert acc1_dup.id == acc1.id

        acc2 = create_account(
            project_id=proj_id,
            platform="instagram",
            external_id=f"ig_{uid}",
            handle=f"insta_user_{uid}",
            db=db,
        )

        listed = list_accounts(project_id=proj_id, db=db)
        assert len(listed) == 2
        handles = [a.handle for a in listed]
        assert f"alpha_creator_updated_{uid}" in handles
        assert f"insta_user_{uid}" in handles
    finally:
        db.close()


def test_take_snapshot_and_idempotency(setup_test_database, mock_provider):
    db = SessionLocal()
    uid = uuid.uuid4().hex[:6]
    proj_id = f"proj_snap_{uid}"
    try:
        account = create_account(
            project_id=proj_id,
            platform="youtube",
            external_id=f"UC_snap_{uid}",
            handle=f"snap_user_{uid}",
            db=db,
        )

        base_now = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
        snap1 = take_account_snapshot(
            account_id=account.id,
            provider=mock_provider,
            db=db,
            force=False,
            now=base_now,
        )
        assert snap1.id is not None
        assert snap1.followers == 10000

        # Segunda llamada el mismo día (12:00 UTC) con force=False no duplica
        snap2 = take_account_snapshot(
            account_id=account.id,
            provider=mock_provider,
            db=db,
            force=False,
            now=base_now + timedelta(hours=2),
        )
        assert snap2.id == snap1.id

        # Con force=True sí crea una nueva
        snap3 = take_account_snapshot(
            account_id=account.id,
            provider=mock_provider,
            db=db,
            force=True,
            now=base_now + timedelta(hours=3),
        )
        assert snap3.id != snap1.id
    finally:
        db.close()


def test_seven_days_simulated_growth(setup_test_database):
    db = SessionLocal()
    uid = uuid.uuid4().hex[:6]
    proj_id = f"proj_7days_{uid}"
    try:
        account = create_account(
            project_id=proj_id,
            platform="youtube",
            external_id=f"UC_7days_{uid}",
            handle=f"growth_tester_{uid}",
            db=db,
        )

        # Simular 7 días con crecimiento de 100 seguidores por día
        base_date = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
        followers = 10000

        for day in range(7):
            snap_time = base_date + timedelta(days=day)
            snap = AccountSnapshot(
                account_id=account.id,
                taken_at=snap_time,
                followers=followers + (day * 100),
                following=50,
                posts_count=10 + day,
                total_views=50000 + (day * 2000),
                engagement_rate=3.5,
            )
            db.add(snap)

        # Añadir un post destacado
        post = PostSnapshot(
            account_id=account.id,
            external_post_id=f"best_video_{uid}",
            published_at=base_date,
            taken_at=base_date,
            views=100000,
            likes=5000,
            comments=450,
            shares=120,
            text="Video viral con crecimiento exponencial #viral #trama",
            hashtags=["viral", "trama"],
        )
        db.add(post)
        db.commit()

        # Consultar serie de crecimiento
        result = get_growth_series(account_id=account.id, db=db)
        series = result["series"]
        summary = result["summary"]

        assert len(series) == 7
        assert series[0]["followers"] == 10000
        assert series[0]["delta"] == 0

        assert series[1]["followers"] == 10100
        assert series[1]["delta"] == 100
        assert series[1]["growth_pct"] == 1.0  # 100 / 10000 * 100

        assert series[-1]["followers"] == 10600
        assert summary["growth_7d"] == 600
        assert summary["growth_7d_pct"] == 6.0

        assert len(summary["top_posts"]) == 1
        assert summary["top_posts"][0]["id"] == f"best_video_{uid}"
        assert summary["top_posts"][0]["views"] == 100000
    finally:
        db.close()


def test_scheduler_resilience_and_error_handling(setup_test_database):
    db = SessionLocal()
    try:
        acc_ok = create_account(
            project_id="proj_sched",
            platform="youtube",
            external_id="UC_ok_channel",
            handle="ok_creator",
            db=db,
        )
        acc_failing = create_account(
            project_id="proj_sched",
            platform="youtube",
            external_id="UC_quota_channel",
            handle="quota_creator",
            db=db,
        )
    finally:
        db.close()

    # Proveedor simulado que falla para el canal de cuota
    class ControlledProvider:
        platform = "youtube"

        def fetch_account(self, external_id: str) -> AccountData:
            if external_id == "UC_quota_channel":
                raise ProviderQuotaError("Daily quota exceeded", platform="youtube", retry_after=86400)
            return AccountData(
                platform="youtube",
                external_id=external_id,
                handle=external_id,
                display_name=external_id,
                followers=5000,
            )

        def fetch_posts(self, external_id, limit=50):
            return []

        def fetch_comments(self, post_id, limit=100):
            return []

        def search_related(self, external_id, limit=25):
            return []

    scheduler = SnapshotScheduler(provider_factory=lambda plat: ControlledProvider())
    stats = scheduler.run_snapshot_collection()

    assert stats["total"] >= 2
    assert stats["success"] >= 1
    assert stats["errors"] >= 1

    # Verificar que el error no detuvo el proceso y se registró
    error_channels = [e["error"] for e in stats["error_details"]]
    assert any("Daily quota exceeded" in e for e in error_channels)


def test_growth_api_endpoints_e2e(setup_test_database):
    headers = {"X-Project-Id": "demo-reforma-del-agua"}

    # 1. Crear cuenta vía API
    create_resp = client.post(
        "/accounts",
        json={
            "platform": "youtube",
            "external_id": "UC_api_test_01",
            "handle": "api_creator",
            "display_name": "API Creator Test",
            "is_owned": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    account_id = created_data["id"]
    assert created_data["handle"] == "api_creator"

    # 2. Listar cuentas vía API
    list_resp = client.get("/accounts", headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert any(a["id"] == account_id for a in accounts)

    # 3. Obtener crecimiento (inicialmente vacío o sin snapshots)
    growth_resp = client.get(f"/accounts/{account_id}/growth", headers=headers)
    assert growth_resp.status_code == 200
    growth_data = growth_resp.json()
    assert growth_data["account_id"] == account_id
    assert "series" in growth_data
    assert "summary" in growth_data
