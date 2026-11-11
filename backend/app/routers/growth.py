"""
routers/growth.py — Endpoints para seguimiento de cuentas, instantáneas y crecimiento.
Carril B: Snapshots y scheduler.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_project
from ..models import Account
from ..growth import (
    create_account as svc_create_account,
    list_accounts as svc_list_accounts,
    get_account_by_id,
    take_account_snapshot as svc_take_snapshot,
    get_growth_series as svc_get_growth,
)
from ..schemas import (
    CreateAccountPayload,
    AccountOut,
    AccountSnapshotOut,
    AccountGrowthResponse,
)

router = APIRouter(tags=["Crecimiento y Creadores"])


def _resolve_provider_for_account(account: Account):
    """Resuelve la instancia del DataProvider según la plataforma de la cuenta."""
    if account.platform == "youtube":
        from ..providers.youtube import YouTubeProvider
        return YouTubeProvider()
    if account.platform in ("instagram", "facebook"):
        from ..providers.meta import MetaProvider
        return MetaProvider(platform=account.platform)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Plataforma '{account.platform}' no tiene un proveedor configurado.",
    )


@router.post(
    "/accounts",
    response_model=AccountOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una cuenta a seguir en el proyecto activo",
)
def create_account(
    payload: CreateAccountPayload,
    project: Dict[str, Any] = Depends(get_current_project),
    db: Session = Depends(get_db),
):
    """Registra una cuenta {platform, external_id, is_owned} en el proyecto actual."""
    account = svc_create_account(
        project_id=project["id"],
        platform=payload.platform,
        external_id=payload.external_id,
        handle=payload.handle,
        display_name=payload.display_name,
        is_owned=payload.is_owned,
        db=db,
    )
    return AccountOut(
        id=account.id,
        project_id=account.project_id,
        platform=account.platform,
        external_id=account.external_id,
        handle=account.handle,
        display_name=account.display_name,
        is_owned=account.is_owned,
        created_at=account.created_at.isoformat() if hasattr(account.created_at, "isoformat") else str(account.created_at),
    )


@router.get(
    "/accounts",
    response_model=List[AccountOut],
    status_code=status.HTTP_200_OK,
    summary="Lista cuentas del proyecto activo",
)
def list_accounts(
    project: Dict[str, Any] = Depends(get_current_project),
    db: Session = Depends(get_db),
):
    """Lista las cuentas asociadas al proyecto actual."""
    accounts = svc_list_accounts(project_id=project["id"], db=db)
    return [
        AccountOut(
            id=acc.id,
            project_id=acc.project_id,
            platform=acc.platform,
            external_id=acc.external_id,
            handle=acc.handle,
            display_name=acc.display_name,
            is_owned=acc.is_owned,
            created_at=acc.created_at.isoformat() if hasattr(acc.created_at, "isoformat") else str(acc.created_at),
        )
        for acc in accounts
    ]


@router.post(
    "/accounts/{id}/snapshot",
    response_model=AccountSnapshotOut,
    status_code=status.HTTP_200_OK,
    summary="Fuerza una instantánea para la cuenta indicada",
)
def take_account_snapshot(
    id: int,
    project: Dict[str, Any] = Depends(get_current_project),
    db: Session = Depends(get_db),
):
    """Toma inmediatamente una nueva instantánea de métricas para la cuenta."""
    account = get_account_by_id(account_id=id, project_id=project["id"], db=db)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta {id} no encontrada en el proyecto '{project['id']}'.",
        )

    provider = _resolve_provider_for_account(account)

    try:
        snapshot = svc_take_snapshot(account_id=account.id, provider=provider, db=db, force=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error del proveedor de datos al recolectar instantánea: {exc}",
        ) from exc

    return AccountSnapshotOut(
        id=snapshot.id,
        account_id=snapshot.account_id,
        taken_at=snapshot.taken_at.isoformat() if hasattr(snapshot.taken_at, "isoformat") else str(snapshot.taken_at),
        followers=snapshot.followers,
        following=snapshot.following,
        posts_count=snapshot.posts_count,
        total_views=snapshot.total_views,
        engagement_rate=snapshot.engagement_rate,
        raw=snapshot.raw or {},
    )


@router.get(
    "/accounts/{id}/growth",
    response_model=AccountGrowthResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtiene la serie temporal de crecimiento y métricas clave de la cuenta",
)
def get_account_growth(
    id: int,
    from_date: Optional[str] = Query(None, alias="from", description="Fecha inicio YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, alias="to", description="Fecha fin YYYY-MM-DD"),
    bucket: str = Query("day", description="Granularidad temporal: day | week | month"),
    project: Dict[str, Any] = Depends(get_current_project),
    db: Session = Depends(get_db),
):
    """Devuelve serie temporal [{date, followers, delta, growth_pct}] y métricas de 7/30 días."""
    account = get_account_by_id(account_id=id, project_id=project["id"], db=db)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta {id} no encontrada en el proyecto '{project['id']}'.",
        )

    data = svc_get_growth(
        account_id=account.id,
        from_date=from_date,
        to_date=to_date,
        bucket=bucket,
        db=db,
    )
    return AccountGrowthResponse(**data)
