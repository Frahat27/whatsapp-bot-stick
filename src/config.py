"""
Configuración central del proyecto usando pydantic-settings.
Todas las variables se leen de .env o variables de entorno.

Prioridad personalizada: .env > env vars del sistema.
Esto es necesario porque Claude Code exporta ANTHROPIC_API_KEY=""
que pisaba nuestro valor real del .env.
"""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del Bot Sofía — STICK."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        .env tiene prioridad sobre variables de entorno del sistema.
        Orden: init args > .env file > env vars > secrets files
        """
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    # --- App ---
    environment: str = "development"
    log_level: str = "DEBUG"

    # --- WhatsApp Business API ---
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""

    # --- AppSheet API ---
    appsheet_app_id: str = "cfc7574f-e4ec-4cf4-8a63-f04d84d347d4"
    appsheet_api_key: str = ""

    # --- Claude API (Anthropic) ---
    anthropic_api_key: str = ""

    # --- PostgreSQL (Neon) — bot-internal data ---
    database_url: str = ""

    # --- PostgreSQL (Cloud SQL) — clinic data (nexus_clinic_os) ---
    clinic_database_url: str = ""

    # --- Redis (Upstash) ---
    redis_url: str = ""

    # --- Groq (Audio Transcription) ---
    groq_api_key: str = ""

    # --- Google Sheets ---
    google_sheets_credentials_file: str = "credentials/franco.json"
    google_sheets_spreadsheet_id: str = "1Ql5Li8PdpZGg7obxmEjoyH1h-rmjQw0F_WOnwn34GRU"

    # --- Admin Config ---
    admin_phones: str = "1123266671,5491171342438"
    admin_names: str = "Franco,Cynthia"

    # --- AppSheet rate limiting ---
    appsheet_min_interval_seconds: float = 45.0
    appsheet_cache_ttl_seconds: int = 300  # 5 min cache default

    # --- Conversation ---
    conversation_history_limit: int = 25  # últimos N mensajes como contexto
    conversation_summary_threshold: int = 50  # resumir al superar N mensajes
    conversation_lock_ttl_seconds: int = 120  # TTL del lock por conversación
    conversation_timeout_seconds: int = 90  # timeout global del tool calling loop

    # --- Scheduler ---
    scheduler_enabled: bool = True  # False para deshabilitar todos los jobs
    scheduler_appointment_cron_hour: int = 10  # 10:00 AM Argentina
    scheduler_lead_followup_cron_hour: int = 11  # 11:00 AM Argentina
    scheduler_lock_ttl_seconds: int = 600  # 10 min max para un job
    scheduler_confirmation_interval_minutes: int = 60  # Cada 60 min
    scheduler_birthday_cron_hour: int = 9  # 9:00 AM Argentina
    scheduler_aligner_cron_hour: int = 10  # 10:00 AM Argentina
    scheduler_review_cron_hour: int = 14  # 14:00 Argentina

    # --- Google Maps Review ---
    google_maps_review_link: str = "https://g.page/r/CXyr_5_Wv5_7EBM/review"

    # --- Admin Panel Auth (JWT) ---
    jwt_secret_key: str = "change-me-in-production-use-a-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 24
    admin_password_hash_franco: str = ""
    admin_password_hash_cynthia: str = ""

    # --- WhatsApp retry ---
    whatsapp_max_retries: int = 3  # reintentos para send_text

    @property
    def admin_phone_list(self) -> list[str]:
        """Lista de teléfonos admin (últimos 10 dígitos)."""
        return [p.strip() for p in self.admin_phones.split(",") if p.strip()]

    @property
    def admin_name_list(self) -> list[str]:
        """Lista de nombres admin."""
        return [n.strip() for n in self.admin_names.split(",") if n.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton cached de settings."""
    return Settings()
