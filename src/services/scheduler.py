"""
Integracion APScheduler — jobs programados de recordatorios.

Corre dentro del proceso FastAPI. Usa CronTrigger con
timezone America/Buenos_Aires. Redis distributed lock previene
ejecucion duplicada si hay multiples instancias.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """Obtener la instancia del scheduler (puede ser None)."""
    return _scheduler


async def start_scheduler() -> None:
    """Inicializar y arrancar el scheduler. Llamar desde lifespan startup."""
    global _scheduler
    settings = get_settings()

    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled")
        return

    _scheduler = AsyncIOScheduler(timezone="America/Buenos_Aires")

    # Job 1: Recordatorios de turno (diario a la hora configurada)
    _scheduler.add_job(
        _run_appointment_reminders,
        trigger=CronTrigger(
            hour=settings.scheduler_appointment_cron_hour,
            minute=0,
            timezone="America/Buenos_Aires",
        ),
        id="appointment_reminders",
        name="Recordatorios de turnos (24h antes)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 2: Seguimiento de leads (diario a la hora configurada)
    _scheduler.add_job(
        _run_lead_followup,
        trigger=CronTrigger(
            hour=settings.scheduler_lead_followup_cron_hour,
            minute=0,
            timezone="America/Buenos_Aires",
        ),
        id="lead_followup",
        name="Seguimiento de leads (dia 3 y 7)",
        replace_existing=True,
        max_instances=1,
    )

    # Job 3: Confirmacion de turno (cada X min, para cubrir turnos recien agendados)
    _scheduler.add_job(
        _run_appointment_confirmations,
        trigger=IntervalTrigger(
            minutes=settings.scheduler_confirmation_interval_minutes,
        ),
        id="appointment_confirmations",
        name="Confirmacion de turnos agendados",
        replace_existing=True,
        max_instances=1,
    )

    # Job 4: Saludo de cumpleaños (diario)
    _scheduler.add_job(
        _run_birthday_greetings,
        trigger=CronTrigger(
            hour=settings.scheduler_birthday_cron_hour,
            minute=0,
            timezone="America/Buenos_Aires",
        ),
        id="birthday_greetings",
        name="Saludos de cumpleanos",
        replace_existing=True,
        max_instances=1,
    )

    # Job 5: Recordatorio de cambio de alineadores (diario)
    _scheduler.add_job(
        _run_aligner_reminders,
        trigger=CronTrigger(
            hour=settings.scheduler_aligner_cron_hour,
            minute=0,
            timezone="America/Buenos_Aires",
        ),
        id="aligner_reminders",
        name="Recordatorio cambio de alineadores",
        replace_existing=True,
        max_instances=1,
    )

    # Job 6: Solicitud de review en Google Maps (diario)
    _scheduler.add_job(
        _run_google_review_requests,
        trigger=CronTrigger(
            hour=settings.scheduler_review_cron_hour,
            minute=0,
            timezone="America/Buenos_Aires",
        ),
        id="google_review_requests",
        name="Solicitud review Google Maps",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "scheduler_started",
        jobs=len(_scheduler.get_jobs()),
        appointment_hour=settings.scheduler_appointment_cron_hour,
        lead_hour=settings.scheduler_lead_followup_cron_hour,
    )


async def stop_scheduler() -> None:
    """Parar el scheduler. Llamar desde lifespan shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
        _scheduler = None


async def _run_appointment_reminders() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_appointment_reminders
    await _run_with_lock("job:appointment_reminders", process_appointment_reminders)


async def _run_lead_followup() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_lead_followups
    await _run_with_lock("job:lead_followup", process_lead_followups)


async def _run_appointment_confirmations() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_appointment_confirmations
    await _run_with_lock("job:appointment_confirmations", process_appointment_confirmations)


async def _run_birthday_greetings() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_birthday_greetings
    await _run_with_lock("job:birthday_greetings", process_birthday_greetings)


async def _run_aligner_reminders() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_aligner_reminders
    await _run_with_lock("job:aligner_reminders", process_aligner_reminders)


async def _run_google_review_requests() -> None:
    """Wrapper: adquiere Redis lock, luego delega al reminder service."""
    from src.services.reminder_service import process_google_review_requests
    await _run_with_lock("job:google_review_requests", process_google_review_requests)


async def _run_with_lock(lock_key: str, func) -> None:
    """
    Adquirir Redis SETNX lock antes de ejecutar un job.
    Si el lock no se puede adquirir, skip (otra instancia lo esta corriendo).
    Si Redis no disponible, ejecutar de todos modos (asume instancia unica).
    """
    settings = get_settings()
    ttl = settings.scheduler_lock_ttl_seconds

    try:
        from src.clients.redis_client import get_redis
        redis = await get_redis()

        if redis is not None:
            # Intentar adquirir lock
            acquired = await redis.set(lock_key, "1", ex=ttl, nx=True)
            if not acquired:
                logger.info("scheduler_job_skipped_lock_held", key=lock_key)
                return
            try:
                await func()
            finally:
                # Siempre liberar el lock
                try:
                    await redis.delete(lock_key)
                except Exception:
                    pass  # Lock expirara por TTL
        else:
            # Sin Redis — ejecutar directamente (asume instancia unica)
            logger.debug("scheduler_running_without_lock", key=lock_key)
            await func()

    except Exception as e:
        logger.error("scheduler_job_error", key=lock_key, error=str(e))
