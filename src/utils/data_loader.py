"""
Carga de archivos de datos (.md) para el contexto de Claude.

Archivos que se cargan:
- sofia_system_prompt.md  → System prompt principal
- tratamientos_stick.md   → Base de conocimiento de tratamientos
- protocolos_quejas.md    → Protocolo de manejo de quejas
"""

from pathlib import Path
from functools import lru_cache

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Directorio de datos (relativo a la raíz del proyecto)
DATA_DIR = Path(__file__).parent.parent.parent / "data"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Carga el system prompt de Sofía."""
    return _load_file("sofia_system_prompt.md")


@lru_cache(maxsize=1)
def load_tratamientos() -> str:
    """Carga la base de conocimiento de tratamientos."""
    return _load_file("tratamientos_stick.md")


@lru_cache(maxsize=1)
def load_protocolos_quejas() -> str:
    """Carga los protocolos de manejo de quejas."""
    return _load_file("protocolos_quejas.md")


@lru_cache(maxsize=1)
def build_full_system_prompt() -> str:
    """
    Construye el system prompt completo combinando:
    1. System prompt principal
    2. Base de tratamientos
    3. Protocolos de quejas

    Este es el prompt FIJO que se envía a Claude en cada conversación.
    """
    parts = [
        load_system_prompt(),
        "\n\n---\n\n# BASE DE CONOCIMIENTO: TRATAMIENTOS\n\n",
        load_tratamientos(),
        "\n\n---\n\n# PROTOCOLO: MANEJO DE QUEJAS\n\n",
        load_protocolos_quejas(),
    ]
    full_prompt = "".join(parts)
    logger.info("system_prompt_built", total_chars=len(full_prompt))
    return full_prompt


def _load_file(filename: str) -> str:
    """Carga un archivo de texto desde data/."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        logger.error("data_file_not_found", filename=filename, path=str(filepath))
        raise FileNotFoundError(f"Archivo de datos no encontrado: {filepath}")
    content = filepath.read_text(encoding="utf-8")
    logger.info("data_file_loaded", filename=filename, chars=len(content))
    return content
