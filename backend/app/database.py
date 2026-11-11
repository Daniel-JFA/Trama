"""
database.py — Configuración de sesión y motor SQLAlchemy para TRAMA.
Soporta SQLite y PostgreSQL con fallback automático y pooling de conexiones.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

DEFAULT_DB_PATH = Path(__file__).parent.parent / "trama_data.db"


def get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Normalizar postgres:// a postgresql:// para SQLAlchemy 2.x
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        return env_url

    env_db_path = os.getenv("TRAMA_DB_PATH")
    if env_db_path:
        return f"sqlite:///{Path(env_db_path).resolve()}"

    return f"sqlite:///{DEFAULT_DB_PATH.resolve()}"


DATABASE_URL = get_database_url()

# Crear motor según motor (SQLite requiere check_same_thread=False para FastAPI)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Crea todas las tablas declaradas en SQLAlchemy si no existen."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Generador de sesión SQLAlchemy para inyección de dependencias."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
