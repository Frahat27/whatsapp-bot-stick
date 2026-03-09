"""
Calculadora de disponibilidad — cálculo determinístico de slots libres.

Reemplaza el envío de ~200 turnos crudos a Claude por 3 opciones
pre-calculadas. Reduce de ~40K tokens a ~500 tokens.

Lógica:
1. Parsear horarios por día de la semana
2. Para cada día en el rango:
   - Obtener horario del día
   - Filtrar turnos ocupados
   - Calcular gaps libres (respetando duración del tratamiento)
   - Asignar profesional (miércoles 14:30-20:00 = Ana Miño, resto = Cynthia)
3. Filtrar por preferencias del paciente
4. Retornar top opciones formateadas
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Intervalo mínimo entre inicio de turnos (minutos)
SLOT_INTERVAL = 30

# Default si no se puede determinar la duración real
# (cubre ~80% de los turnos que son de 30 minutos)
DEFAULT_DURATION = 30

# Mapeo weekday (0=Monday) → nombre español (para horarios de AppSheet)
DIAS_SEMANA: dict[int, str] = {
    0: "LUNES",
    1: "MARTES",
    2: "MIERCOLES",
    3: "JUEVES",
    4: "VIERNES",
    5: "SABADO",
    6: "DOMINGO",
}

DIAS_DISPLAY: dict[int, str] = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

MESES: dict[int, str] = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def calculate_available_slots(
    horarios: list[dict],
    turnos_ocupados: list[dict],
    tratamiento: str,
    fecha_desde: date,
    fecha_hasta: date,
    preferencia_dia: str = "cualquier dia",
    preferencia_horario: str = "cualquier horario",
    max_options: int = 3,
    duracion_minutos: Optional[int] = None,
) -> list[dict]:
    """
    Calcula los slots disponibles para agendar un turno.

    Args:
        horarios: Lista de dicts de LISTA O | HORARIOS DE ATENCION.
                  Cada dict tiene: DIA, HORA INICIO, HORA CIERRE.
        turnos_ocupados: Lista de dicts de BBDD SESIONES (ya filtrados por rango).
                         Cada dict tiene: Fecha de Sesion, Hora de Sesion, Duracion.
        tratamiento: Tipo de tratamiento (informativo para logs).
        fecha_desde: Fecha inicio de búsqueda.
        fecha_hasta: Fecha fin de búsqueda.
        preferencia_dia: "lunes", "martes y jueves", "cualquier dia", etc.
        preferencia_horario: "mañana", "tarde", "después de las 17", etc.
        max_options: Número máximo de opciones a retornar.
        duracion_minutos: Duración del tratamiento en minutos (leída de AppSheet).
                          Si None, se usa DEFAULT_DURATION (30 min).

    Returns:
        Lista de dicts con slots disponibles, cada uno con:
        - fecha: "YYYY-MM-DD"
        - fecha_display: "miércoles 12 de marzo"
        - hora: "10:00"
        - profesional: "Cynthia Hatzerian" o "Ana Miño"
        - duracion_minutos: 30
    """
    duration = duracion_minutos if duracion_minutos is not None else DEFAULT_DURATION

    # Parse horarios → day_name → (start_time, end_time)
    schedule = _parse_horarios(horarios)

    # Parse occupied sessions → date → [(start_time, end_time)]
    occupied = _parse_occupied_sessions(turnos_ocupados)

    # Hora actual para filtrar slots ya pasados hoy
    from src.utils.dates import today_argentina
    now = datetime.now()
    try:
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires"))
    except Exception:
        pass
    hora_actual = now.time()
    hoy = today_argentina()

    # Generate available slots day by day
    all_slots: list[dict] = []
    current_date = fecha_desde

    while current_date <= fecha_hasta:
        weekday = current_date.weekday()
        day_name = DIAS_SEMANA.get(weekday)

        if day_name not in schedule:
            current_date += timedelta(days=1)
            continue

        # Apply day preference filter
        if not _matches_day_preference(weekday, preferencia_dia):
            current_date += timedelta(days=1)
            continue

        open_time, close_time = schedule[day_name]
        day_occupied = occupied.get(current_date, [])

        # Find free slots in the day
        day_slots = _find_free_slots(
            current_date, open_time, close_time, day_occupied, duration,
        )

        # Filtrar slots ya pasados si es hoy
        if current_date == hoy:
            day_slots = [s for s in day_slots if s["_hora_time"] > hora_actual]

        # Apply time preference filter
        day_slots = [
            s for s in day_slots
            if _matches_time_preference(s["_hora_time"], preferencia_horario)
        ]

        all_slots.extend(day_slots)
        current_date += timedelta(days=1)

    # Select best options (diversified across days)
    result = _select_best_options(all_slots, max_options)

    logger.info(
        "availability_calculated",
        tratamiento=tratamiento,
        duration=duration,
        total_slots_found=len(all_slots),
        returned=len(result),
    )

    return result


# =============================================================================
# PARSING
# =============================================================================

def _parse_horarios(horarios: list[dict]) -> dict[str, tuple[time, time]]:
    """Parsea horarios de AppSheet → dict de DIA → (apertura, cierre)."""
    schedule: dict[str, tuple[time, time]] = {}
    for h in horarios:
        dia = str(h.get("DIA", "")).upper().strip()
        # Normalizar acentos: MIÉRCOLES → MIERCOLES
        dia = (
            dia.replace("É", "E").replace("Á", "A").replace("Í", "I")
            .replace("Ó", "O").replace("Ú", "U")
        )

        hora_inicio = _parse_time(h.get("HORA INICIO", ""))
        hora_cierre = _parse_time(h.get("HORA CIERRE", ""))

        if hora_inicio and hora_cierre and dia:
            schedule[dia] = (hora_inicio, hora_cierre)

    return schedule


def _parse_time(time_str) -> Optional[time]:
    """Parsea formatos de hora de AppSheet a time object."""
    if not time_str:
        return None

    time_str = str(time_str).strip()

    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue

    return None


def _parse_date(date_str) -> Optional[date]:
    """Parsea formatos de fecha de AppSheet (MM/DD/YYYY o YYYY-MM-DD)."""
    if not date_str:
        return None

    date_str = str(date_str).strip()

    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def _parse_duration(duration_val) -> int:
    """Parsea duración de AppSheet (int, "30", "00:30:00", etc)."""
    if isinstance(duration_val, (int, float)):
        return int(duration_val)

    dur_str = str(duration_val).strip()

    # Entero directo
    try:
        return int(dur_str)
    except ValueError:
        pass

    # HH:MM:SS o HH:MM
    try:
        parts = dur_str.split(":")
        if len(parts) >= 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
    except (ValueError, IndexError):
        pass

    return DEFAULT_DURATION


def _parse_occupied_sessions(
    turnos: list[dict],
) -> dict[date, list[tuple[time, time]]]:
    """
    Parsea sesiones ocupadas → dict de fecha → [(inicio, fin)].

    Prioridad para determinar el horario de fin:
    1. Hora inicio + Duracion (si hay duración explícita)
    2. Horario Finalizacion (hora de fin real de la DB)
    3. Hora inicio + DEFAULT_DURATION (fallback 30 min)
    """
    occupied: dict[date, list[tuple[time, time]]] = {}

    for t in turnos:
        fecha_str = t.get("Fecha de Sesion", "")
        hora_str = t.get("Hora de Sesion", "") or t.get("Hora Sesion", "")

        fecha = _parse_date(fecha_str)
        hora = _parse_time(hora_str)

        if not (fecha and hora):
            continue

        # Estrategia 1: calcular desde duración explícita
        dur_raw = t.get("Duracion")
        if dur_raw is not None:
            duracion = _parse_duration(dur_raw)
            end_dt = datetime.combine(fecha, hora) + timedelta(minutes=duracion)
            end_time = end_dt.time()
        else:
            # Estrategia 2: usar Horario Finalizacion directamente
            hora_fin_str = t.get("Horario Finalizacion", "")
            hora_fin = _parse_time(hora_fin_str) if hora_fin_str else None

            if hora_fin and hora_fin > hora:
                end_time = hora_fin
            else:
                # Estrategia 3: fallback a default 30 min
                end_dt = datetime.combine(fecha, hora) + timedelta(minutes=DEFAULT_DURATION)
                end_time = end_dt.time()

        if fecha not in occupied:
            occupied[fecha] = []
        occupied[fecha].append((hora, end_time))

    logger.info(
        "occupied_sessions_parsed",
        total_sessions=sum(len(v) for v in occupied.values()),
        days_with_sessions=len(occupied),
    )

    return occupied


# =============================================================================
# CÁLCULO DE SLOTS LIBRES
# =============================================================================

def _merge_intervals(
    intervals: list[tuple[time, time]],
    ref_date: date,
) -> list[tuple[time, time]]:
    """Merge overlapping time intervals."""
    if not intervals:
        return []

    # Convertir a datetime para comparar correctamente
    dt_intervals = sorted(
        [(datetime.combine(ref_date, s), datetime.combine(ref_date, e))
         for s, e in intervals],
        key=lambda x: x[0],
    )

    merged = [dt_intervals[0]]
    for start, end in dt_intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return [(m[0].time(), m[1].time()) for m in merged]


def _find_free_slots(
    fecha: date,
    open_time: time,
    close_time: time,
    occupied: list[tuple[time, time]],
    duration: int,
) -> list[dict]:
    """
    Encuentra slots libres en un día dado.

    Genera slots al intervalo SLOT_INTERVAL dentro de los gaps
    entre sesiones ocupadas, verificando que la duración completa
    del tratamiento cabe en el gap.
    """
    # Merge overlapping sessions
    merged = _merge_intervals(occupied, fecha)

    slots = []
    current = datetime.combine(fecha, open_time)
    close_dt = datetime.combine(fecha, close_time)

    for occ_start_t, occ_end_t in merged:
        occ_start = datetime.combine(fecha, occ_start_t)
        occ_end = datetime.combine(fecha, occ_end_t)

        # Generar slots en el gap antes de esta sesión ocupada
        while current + timedelta(minutes=duration) <= occ_start:
            slot = _build_slot(fecha, current.time(), duration)
            slots.append(slot)
            current += timedelta(minutes=SLOT_INTERVAL)

        # Avanzar después de la sesión ocupada
        if occ_end > current:
            current = occ_end

    # Generar slots después de la última sesión ocupada
    while current + timedelta(minutes=duration) <= close_dt:
        slot = _build_slot(fecha, current.time(), duration)
        slots.append(slot)
        current += timedelta(minutes=SLOT_INTERVAL)

    return slots


def _build_slot(fecha: date, hora: time, duration: int) -> dict:
    """Construye un dict de slot."""
    profesional = _get_professional(fecha.weekday(), hora)

    return {
        "fecha": fecha.isoformat(),
        "fecha_display": _format_date_display(fecha),
        "hora": hora.strftime("%H:%M"),
        "profesional": profesional,
        "duracion_minutos": duration,
        "_hora_time": hora,  # interno para filtros, se remueve antes de retornar
    }


def _get_professional(weekday: int, hora: time) -> str:
    """
    Determina qué profesional atiende en este slot.

    Regla: Miércoles de 14:30 a 20:00 → Ana Miño.
    Resto → Cynthia Hatzerian.
    """
    if weekday == 2 and time(14, 30) <= hora < time(20, 0):
        return "Ana Miño"
    return "Cynthia Hatzerian"


# =============================================================================
# FILTROS DE PREFERENCIA
# =============================================================================

def _matches_day_preference(weekday: int, preference: str) -> bool:
    """Verifica si un día de la semana coincide con la preferencia del paciente."""
    pref = preference.lower().strip()
    # Normalizar acentos
    pref = (
        pref.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u")
    )

    if pref in ("cualquier dia", "cualquiera", "todos", ""):
        return True

    # Mapeo de nombre → weekday index
    day_keywords: dict[str, int] = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "domingo": 6,
    }

    # Buscar si algún nombre de día aparece en la preferencia
    for name, idx in day_keywords.items():
        if name in pref and weekday == idx:
            return True

    # Si no matcheó ningún día mencionado, no incluir
    # (a menos que no se mencionó ningún día, lo cual ya se cubrió arriba)
    has_any_day = any(name in pref for name in day_keywords)
    if not has_any_day:
        # Preferencia no contiene nombres de días → asumir "cualquier dia"
        return True

    return False


def _matches_time_preference(hora: time, preference: str) -> bool:
    """Verifica si un horario coincide con la preferencia del paciente."""
    pref = preference.lower().strip()
    pref = (
        pref.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )

    if pref in ("cualquier horario", "cualquiera", "todos", ""):
        return True

    if "manana" in pref:
        return hora < time(13, 0)

    if "tarde" in pref:
        return hora >= time(13, 0)

    # Detectar hora específica: "después de las 17", "a partir de las 15"
    match = re.search(r"(\d{1,2})", pref)
    if match:
        target_hour = int(match.group(1))
        if target_hour < 24:
            if "despues" in pref or "partir" in pref:
                return hora >= time(target_hour, 0)
            if "antes" in pref:
                return hora < time(target_hour, 0)

    return True


# =============================================================================
# SELECCIÓN DE MEJORES OPCIONES
# =============================================================================

def _select_best_options(slots: list[dict], max_options: int) -> list[dict]:
    """
    Selecciona las mejores opciones, priorizando diversidad de días.

    Hace round-robin por fecha para que las opciones cubran
    distintos días (no 3 slots del mismo lunes).
    """
    if len(slots) <= max_options:
        result = slots[:]
    else:
        # Agrupar por fecha
        by_date: dict[str, list[dict]] = {}
        for s in slots:
            d = s["fecha"]
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(s)

        # Round-robin por fecha
        result = []
        date_keys = list(by_date.keys())
        idx = 0

        while len(result) < max_options and date_keys:
            date_key = date_keys[idx % len(date_keys)]
            day_slots = by_date[date_key]

            if day_slots:
                result.append(day_slots.pop(0))
                if not day_slots:
                    date_keys.remove(date_key)
                    if date_keys:
                        idx = idx % len(date_keys)
                    continue
            idx += 1

    # Limpiar campo interno
    for s in result:
        s.pop("_hora_time", None)

    return result


# =============================================================================
# UTILIDADES PÚBLICAS
# =============================================================================

def get_treatment_duration(
    tratamiento: str,
    tipos_tratamiento: Optional[list[dict]] = None,
) -> int:
    """
    Obtiene la duración de un tratamiento en minutos.

    Busca en la tabla LISTA A I tipo tratamientos (si se provee).
    Campos esperados: TIPO DE TRATAMIENTO, Duracion Turno.

    Si no encuentra match, retorna DEFAULT_DURATION (30 min).

    Args:
        tratamiento: Nombre del tratamiento a buscar.
        tipos_tratamiento: Lista de dicts de LISTA A I tipo tratamientos.
    """
    if not tipos_tratamiento:
        return DEFAULT_DURATION

    trat_lower = tratamiento.lower().strip()

    # Normalizar acentos para comparación
    def _normalize(s: str) -> str:
        return (
            s.lower().strip()
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )

    trat_norm = _normalize(tratamiento)

    # Paso 1: Match exacto (case-insensitive)
    for t in tipos_tratamiento:
        tipo = str(t.get("TIPO DE TRATAMIENTO", ""))
        if _normalize(tipo) == trat_norm:
            return _parse_duration(t.get("Duracion Turno", DEFAULT_DURATION))

    # Paso 2: Match parcial (el nombre contiene o está contenido)
    for t in tipos_tratamiento:
        tipo = str(t.get("TIPO DE TRATAMIENTO", ""))
        tipo_norm = _normalize(tipo)
        if tipo_norm in trat_norm or trat_norm in tipo_norm:
            return _parse_duration(t.get("Duracion Turno", DEFAULT_DURATION))

    return DEFAULT_DURATION


def _format_date_display(fecha: date) -> str:
    """Formatea fecha para display: 'miércoles 12 de marzo'."""
    weekday = DIAS_DISPLAY.get(fecha.weekday(), "")
    mes = MESES.get(fecha.month, "")
    return f"{weekday} {fecha.day} de {mes}"


def format_slots_for_claude(slots: list[dict]) -> str:
    """
    Formatea slots como texto conciso para el contexto de Claude.

    Esto es lo que Claude recibe en vez de los 200 turnos crudos.
    """
    if not slots:
        return "No se encontraron turnos disponibles en el rango solicitado."

    lines = []
    for i, s in enumerate(slots, 1):
        lines.append(
            f"{i}. {s['fecha_display']} a las {s['hora']} "
            f"con {s['profesional']} ({s['duracion_minutos']} min)"
        )

    return "\n".join(lines)
