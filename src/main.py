"""
FastAPI application — Bot Sofía STICK.

Punto de entrada principal. Configura la app, lifespan, y registra routers.
Ejecutar con: uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.config import get_settings
from src.db.session import get_engine
from src.utils.logging_config import get_logger, setup_logging

# Configurar logging ANTES de todo
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: startup y shutdown.
    - Startup: verifica conexión a DB.
    - Shutdown: cierra pool de conexiones.
    """
    settings = get_settings()
    logger.info(
        "app_starting",
        environment=settings.environment,
        appsheet_app_id=settings.appsheet_app_id,
    )

    # Verificar conexión a DB
    if settings.database_url:
        try:
            db_engine = get_engine()
            async with db_engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            logger.info("database_connected")
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
    else:
        logger.warning("database_url_not_configured")

    yield

    # Shutdown — cerrar todos los clientes
    from src.clients.appsheet import shutdown_appsheet_client
    from src.clients.whatsapp import close_client as close_whatsapp_client
    from src.clients.claude_ai import close_client as close_claude_client

    for name, closer in [
        ("appsheet", shutdown_appsheet_client),
        ("whatsapp", close_whatsapp_client),
        ("claude", close_claude_client),
    ]:
        try:
            await closer()
        except Exception as e:
            logger.warning(f"shutdown_{name}_error", error=str(e))

    if settings.database_url:
        try:
            db_engine = get_engine()
            await db_engine.dispose()
        except Exception:
            pass
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="Bot Sofía — STICK Alineadores",
        description="Bot de WhatsApp para gestión de turnos, pagos y atención al paciente.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS (necesario para panel admin frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else ["https://admin.sticksmile.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registrar routers
    app.include_router(api_router)

    return app


# Instancia de la app
app = create_app()
