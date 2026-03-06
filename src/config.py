"""
Configuración central del proyecto usando pydantic-settings.
Todas las variables se leen de .env o variables de entorno.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del Bot Sofía — STICK."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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

    # --- PostgreSQL (Neon) ---
    database_url: str = ""

    # --- Redis (Upstash) ---
    redis_url: str = ""

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
