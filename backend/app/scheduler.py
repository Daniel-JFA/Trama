"""
scheduler.py — Programador periódico de instantáneas históricas con APScheduler.
Carril B: Snapshots y scheduler.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

import logging
from typing import Optional, Callable, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from .models import Account
from .database import SessionLocal
from .growth import take_account_snapshot
from .providers.base import DataProvider, ProviderError

logger = logging.getLogger("trama.scheduler")


class SnapshotScheduler:
    """
    Gestiona el ciclo de vida de la recolección periódica de instantáneas de creadores.
    Garantiza aislamiento ante fallos: el error de una cuenta/proveedor no interrumpe el resto.
    """

    def __init__(self, provider_factory: Optional[Callable[[str], Optional[DataProvider]]] = None):
        self.scheduler = BackgroundScheduler()
        self.provider_factory = provider_factory or self._default_provider_factory
        self._is_started = False

    @staticmethod
    def _default_provider_factory(platform: str) -> Optional[DataProvider]:
        """Resuelve el proveedor predeterminado según la plataforma."""
        if platform == "youtube":
            from .providers.youtube import YouTubeProvider
            return YouTubeProvider()
        # Meta y otros proveedores se integran conforme están disponibles
        return None

    def run_snapshot_collection(self) -> Dict[str, Any]:
        """
        Ejecuta una ronda de recolección para todas las cuentas registradas.
        Retorna estadísticas de éxito y fallos.
        """
        db = SessionLocal()
        stats = {"total": 0, "success": 0, "skipped": 0, "errors": 0, "error_details": []}

        try:
            accounts = list(db.execute(select(Account)).scalars().all())
            stats["total"] = len(accounts)

            for account in accounts:
                provider = self.provider_factory(account.platform)
                if not provider:
                    stats["skipped"] += 1
                    continue

                try:
                    take_account_snapshot(account.id, provider, db=db, force=False)
                    stats["success"] += 1
                except Exception as exc:
                    stats["errors"] += 1
                    err_entry = {
                        "account_id": account.id,
                        "platform": account.platform,
                        "error": str(exc),
                    }
                    stats["error_details"].append(err_entry)
                    logger.warning(
                        "Fallo al tomar instantánea de cuenta %s (%s): %s",
                        account.id,
                        account.handle,
                        exc,
                    )
                    continue

            return stats
        finally:
            db.close()

    def schedule_daily_snapshots(self, hour: int = 2, minute: int = 0) -> str:
        """Programa la ejecución diaria a una hora UTC específica."""
        job_id = "daily_account_snapshots"
        if not self.scheduler.get_job(job_id):
            self.scheduler.add_job(
                func=self.run_snapshot_collection,
                trigger=CronTrigger(hour=hour, minute=minute, timezone="UTC"),
                id=job_id,
                name="Recolección diaria de instantáneas de creadores",
                replace_existing=True,
            )
        return job_id

    def start(self) -> None:
        """Arranca el planificador si no está iniciado."""
        if not self._is_started:
            self.scheduler.start()
            self._is_started = True

    def shutdown(self, wait: bool = False) -> None:
        """Detiene el planificador si está en ejecución."""
        if self._is_started:
            self.scheduler.shutdown(wait=wait)
            self._is_started = False
