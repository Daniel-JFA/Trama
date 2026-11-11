"""
growth.py — Servicios de recolección de instantáneas y cálculo de métricas de crecimiento.
Carril B: Snapshots y scheduler.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from .models import Account, AccountSnapshot, PostSnapshot
from .database import SessionLocal
from .providers.base import DataProvider, AccountData, PostData, ProviderError


def create_account(
    project_id: str,
    platform: str,
    external_id: str,
    handle: Optional[str] = None,
    display_name: Optional[str] = "",
    is_owned: bool = False,
    db: Optional[Session] = None,
) -> Account:
    """Registra una cuenta a seguir en un proyecto, evitando duplicados."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        clean_handle = (handle or external_id).lstrip("@")
        clean_name = display_name or clean_handle

        existing = db.execute(
            select(Account).where(
                and_(
                    Account.project_id == project_id,
                    Account.platform == platform.lower(),
                    Account.external_id == external_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            if handle:
                existing.handle = clean_handle
            if display_name:
                existing.display_name = clean_name
            existing.is_owned = is_owned
            db.commit()
            db.refresh(existing)
            return existing

        account = Account(
            project_id=project_id,
            platform=platform.lower(),
            external_id=external_id,
            handle=clean_handle,
            display_name=clean_name,
            is_owned=is_owned,
            created_at=datetime.now(timezone.utc),
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    finally:
        if close_db:
            db.close()


def list_accounts(project_id: str, db: Optional[Session] = None) -> List[Account]:
    """Lista todas las cuentas registradas en un proyecto."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        stmt = select(Account).where(Account.project_id == project_id).order_by(Account.created_at.desc())
        return list(db.execute(stmt).scalars().all())
    finally:
        if close_db:
            db.close()


def get_account_by_id(account_id: int, project_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[Account]:
    """Obtiene una cuenta por su ID numérico."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        stmt = select(Account).where(Account.id == account_id)
        if project_id:
            stmt = stmt.where(Account.project_id == project_id)
        return db.execute(stmt).scalar_one_or_none()
    finally:
        if close_db:
            db.close()


def take_account_snapshot(
    account_id: int,
    provider: DataProvider,
    db: Optional[Session] = None,
    force: bool = False,
    now: Optional[datetime] = None,
) -> AccountSnapshot:
    """
    Toma una instantánea del creador usando el DataProvider correspondiente.
    Si force=False, no duplica la instantánea si ya existe una para el mismo día UTC.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    current_time = now or datetime.now(timezone.utc)

    try:
        account = db.execute(select(Account).where(Account.id == account_id)).scalar_one_or_none()
        if not account:
            raise ValueError(f"Cuenta con id {account_id} no existe.")

        # Control de duplicados por día natural UTC
        if not force:
            latest = db.execute(
                select(AccountSnapshot)
                .where(AccountSnapshot.account_id == account_id)
                .order_by(AccountSnapshot.taken_at.desc())
            ).scalars().first()
            if latest and latest.taken_at:
                latest_str = latest.taken_at if isinstance(latest.taken_at, str) else latest.taken_at.strftime("%Y-%m-%d")
                current_str = current_time if isinstance(current_time, str) else current_time.strftime("%Y-%m-%d")
                if latest_str[:10] == current_str[:10]:
                    return latest

        # Llamar al proveedor
        acc_data: AccountData = provider.fetch_account(account.external_id)

        # Actualizar metadatos si han cambiado
        if acc_data.handle and acc_data.handle != account.handle:
            account.handle = acc_data.handle
        if acc_data.display_name and acc_data.display_name != account.display_name:
            account.display_name = acc_data.display_name

        snapshot = AccountSnapshot(
            account_id=account.id,
            taken_at=current_time,
            followers=acc_data.followers,
            following=acc_data.following,
            posts_count=acc_data.posts_count,
            total_views=acc_data.total_views,
            engagement_rate=acc_data.engagement_rate,
            raw=acc_data.raw or {},
        )
        db.add(snapshot)

        # Recolectar publicaciones recientes si el proveedor las soporta
        try:
            posts = provider.fetch_posts(account.external_id, limit=20)
            for p in posts:
                # Comprobar si ya existe la publicación
                existing_p = db.execute(
                    select(PostSnapshot).where(
                        and_(
                            PostSnapshot.account_id == account.id,
                            PostSnapshot.external_post_id == p.external_post_id,
                        )
                    )
                ).scalar_one_or_none()

                if existing_p:
                    existing_p.views = p.views
                    existing_p.likes = p.likes
                    existing_p.comments = p.comments
                    existing_p.shares = p.shares
                    existing_p.taken_at = current_time
                    if p.hashtags:
                        existing_p.hashtags = p.hashtags
                else:
                    db.add(
                        PostSnapshot(
                            account_id=account.id,
                            external_post_id=p.external_post_id,
                            published_at=p.published_at,
                            taken_at=current_time,
                            views=p.views,
                            likes=p.likes,
                            comments=p.comments,
                            shares=p.shares,
                            text=p.text,
                            hashtags=p.hashtags or [],
                        )
                    )
        except Exception:
            # Si falla la extracción secundaria de posts, el snapshot de cuenta se preserva
            pass

        db.commit()
        db.refresh(snapshot)
        return snapshot
    finally:
        if close_db:
            db.close()


def get_growth_series(
    account_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    bucket: str = "day",
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Calcula la serie temporal de crecimiento (followers, deltas y %) y métricas resumen.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        stmt = (
            select(AccountSnapshot)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.taken_at.asc())
        )

        all_snapshots = list(db.execute(stmt).scalars().all())
        if not all_snapshots:
            return {
                "account_id": account_id,
                "series": [],
                "summary": {
                    "growth_7d": 0,
                    "growth_7d_pct": 0.0,
                    "growth_30d": 0,
                    "growth_30d_pct": 0.0,
                    "top_posts": [],
                },
            }

        # Agrupación por día (YYYY-MM-DD) tomando el snapshot más reciente del día
        by_day: Dict[str, AccountSnapshot] = {}
        for snap in all_snapshots:
            d_str = snap.taken_at.strftime("%Y-%m-%d")
            # Filtrar por rango si se especificó
            if from_date and d_str < from_date:
                continue
            if to_date and d_str > to_date:
                continue
            by_day[d_str] = snap

        sorted_days = sorted(by_day.keys())
        series: List[Dict[str, Any]] = []

        prev_followers: Optional[int] = None
        for day in sorted_days:
            snap = by_day[day]
            followers = snap.followers
            if prev_followers is None:
                delta = 0
                pct = 0.0
            else:
                delta = followers - prev_followers
                pct = round((delta / prev_followers) * 100, 2) if prev_followers > 0 else 0.0

            series.append({
                "date": day,
                "followers": followers,
                "delta": delta,
                "growth_pct": pct,
            })
            prev_followers = followers

        # Resumen de 7 y 30 días
        now = datetime.now(timezone.utc)
        latest_snap = all_snapshots[-1]
        latest_followers = latest_snap.followers

        # 7 días atrás
        t_7d = latest_snap.taken_at - timedelta(days=7)
        snap_7d = None
        for s in reversed(all_snapshots):
            if s.taken_at <= t_7d:
                snap_7d = s
                break
        if not snap_7d and len(all_snapshots) > 1:
            snap_7d = all_snapshots[0]

        growth_7d = (latest_followers - snap_7d.followers) if snap_7d else 0
        growth_7d_pct = round((growth_7d / snap_7d.followers) * 100, 2) if (snap_7d and snap_7d.followers > 0) else 0.0

        # 30 días atrás
        t_30d = latest_snap.taken_at - timedelta(days=30)
        snap_30d = None
        for s in reversed(all_snapshots):
            if s.taken_at <= t_30d:
                snap_30d = s
                break
        if not snap_30d and len(all_snapshots) > 1:
            snap_30d = all_snapshots[0]

        growth_30d = (latest_followers - snap_30d.followers) if snap_30d else 0
        growth_30d_pct = round((growth_30d / snap_30d.followers) * 100, 2) if (snap_30d and snap_30d.followers > 0) else 0.0

        # Mejores publicaciones del creador
        top_posts_stmt = (
            select(PostSnapshot)
            .where(PostSnapshot.account_id == account_id)
            .order_by(desc(PostSnapshot.views), desc(PostSnapshot.likes))
            .limit(5)
        )
        top_posts = [
            {
                "id": p.external_post_id,
                "published_at": p.published_at.isoformat() if p.published_at else "",
                "views": p.views,
                "likes": p.likes,
                "comments": p.comments,
                "text": p.text[:120] if p.text else "",
                "hashtags": p.hashtags or [],
            }
            for p in db.execute(top_posts_stmt).scalars().all()
        ]

        return {
            "account_id": account_id,
            "series": series,
            "summary": {
                "growth_7d": growth_7d,
                "growth_7d_pct": growth_7d_pct,
                "growth_30d": growth_30d,
                "growth_30d_pct": growth_30d_pct,
                "top_posts": top_posts,
            },
        }
    finally:
        if close_db:
            db.close()
