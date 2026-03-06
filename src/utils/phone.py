"""
Utilidades para normalización de números de teléfono argentinos.

Reglas:
- AppSheet almacena teléfonos en formatos variados: +5491112345678, 1112345678, etc.
- Para buscar con CONTAINS en AppSheet, usamos los últimos 10 dígitos.
- Para WhatsApp API, el formato es 5491112345678 (sin +).
"""

import re


def normalize_phone(phone: str) -> str:
    """
    Normaliza un teléfono a los últimos 10 dígitos (formato argentino).
    Útil para búsquedas CONTAINS en AppSheet.

    Ejemplos:
        "+54 9 11 2326-6671" → "1123266671"
        "5491123266671"       → "1123266671"
        "1123266671"          → "1123266671"
        "011 2326-6671"       → "1123266671"
    """
    # Remover todo excepto dígitos
    digits = re.sub(r"\D", "", phone)

    # Si empieza con 54 y tiene 13 dígitos (549XXXXXXXXXX), sacar prefijo
    if len(digits) >= 12 and digits.startswith("549"):
        digits = digits[3:]  # Quitar "549"
    elif len(digits) >= 12 and digits.startswith("54"):
        digits = digits[2:]  # Quitar "54"

    # Si empieza con 0 (ej: 01123266671), quitar el 0
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Tomar últimos 10 dígitos
    return digits[-10:] if len(digits) >= 10 else digits


def to_whatsapp_format(phone: str) -> str:
    """
    Convierte un teléfono al formato WhatsApp API (549XXXXXXXXXX).

    Ejemplos:
        "1123266671" → "5491123266671"
        "+54 9 11 2326-6671" → "5491123266671"
    """
    normalized = normalize_phone(phone)
    return f"549{normalized}"


def is_admin_phone(phone: str, admin_phones: list[str]) -> bool:
    """
    Verifica si un teléfono pertenece a un admin.
    Compara los últimos 10 dígitos.
    """
    normalized = normalize_phone(phone)
    return normalized in [normalize_phone(p) for p in admin_phones]
