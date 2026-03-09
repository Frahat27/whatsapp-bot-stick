"""
AsyncSession factory para Cloud SQL (clinic data).
Lazy initialization, misma arquitectura que session.py (Neon).

Uso:
    from src.db.clinic_session import get_clinic_db, get_clinic_session_factory

    # Como dependency de FastAPI:
    @app.get("/patients")
    async def patients(clinic_db: AsyncSession = Depends(get_clinic_db)):
        ...

    # Desde código standalone (ej: scheduler/reminders):
    factory = get_clinic_session_factory()
    async with factory() as session:
        ...
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

# Lazy globals
_clinic_engine: Optional[AsyncEngine] = None
_clinic_session_factory: Optional[async_sessionmaker] = None


def get_clinic_engine() -> AsyncEngine:
    """Obtener o crear el engine async para Cloud SQL (lazy)."""
    global _clinic_engine
    if _clinic_engine is None:
        settings = get_settings()
        if not settings.clinic_database_url:
            raise RuntimeError(
                "CLINIC_DATABASE_URL no configurada. "
                "Configurar en .env para conectar a Cloud SQL (nexus_clinic_os)."
            )
        _clinic_engine = create_async_engine(
            settings.clinic_database_url,
            echo=settings.log_level == "DEBUG",
            pool_size=10,       # Mayor que Neon: mas concurrencia, sin rate limit
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _clinic_engine


def get_clinic_session_factory() -> async_sessionmaker:
    """Obtener o crear la session factory para Cloud SQL (lazy)."""
    global _clinic_session_factory
    if _clinic_session_factory is None:
        _clinic_session_factory = async_sessionmaker(
            get_clinic_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _clinic_session_factory


async def get_clinic_db():
    """Dependency que provee una sesion de Cloud SQL."""
    factory = get_clinic_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def shutdown_clinic_engine() -> None:
    """Cerrar el engine de Cloud SQL (llamar en lifespan shutdown)."""
    global _clinic_engine, _clinic_session_factory
    if _clinic_engine is not None:
        await _clinic_engine.dispose()
        _clinic_engine = None
        _clinic_session_factory = None
