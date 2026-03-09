"""
Tests de la calculadora de disponibilidad.
Verifica cálculo de slots, filtros, profesional, y edge cases.
"""
from __future__ import annotations

from datetime import date, time

import pytest

from src.services.availability import (
    SLOT_INTERVAL,
    _find_free_slots,
    _format_date_display,
    _get_professional,
    _matches_day_preference,
    _matches_time_preference,
    _merge_intervals,
    _parse_duration,
    _parse_horarios,
    _parse_occupied_sessions,
    _parse_time,
    _select_best_options,
    calculate_available_slots,
    format_slots_for_claude,
    get_treatment_duration,
)


# =============================================================================
# FIXTURES — datos de ejemplo de AppSheet
# =============================================================================

@pytest.fixture
def horarios_standard():
    """Horarios estándar de la clínica (lunes a viernes + sábado)."""
    return [
        {"DIA": "LUNES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
        {"DIA": "MARTES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
        {"DIA": "MIERCOLES", "HORA INICIO": "08:30:00", "HORA CIERRE": "20:00:00"},
        {"DIA": "JUEVES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
        {"DIA": "VIERNES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
        {"DIA": "SABADO", "HORA INICIO": "09:00:00", "HORA CIERRE": "13:00:00"},
    ]


@pytest.fixture
def dia_sin_turnos():
    """Día sin turnos ocupados → muchos slots disponibles."""
    return []


@pytest.fixture
def turnos_parciales():
    """Algunos turnos ocupados en un lunes."""
    return [
        {
            "Fecha de Sesion": "03/09/2026",
            "Hora de Sesion": "09:00:00",
            "Duracion": 30,
            "Estado de Sesion": "Planificada",
        },
        {
            "Fecha de Sesion": "03/09/2026",
            "Hora de Sesion": "10:30:00",
            "Duracion": 45,
            "Estado de Sesion": "Confirmada",
        },
        {
            "Fecha de Sesion": "03/09/2026",
            "Hora de Sesion": "14:00:00",
            "Duracion": 90,
            "Estado de Sesion": "Planificada",
        },
    ]


@pytest.fixture
def dia_lleno():
    """Día completamente ocupado — sin gaps."""
    turnos = []
    hora = time(8, 30)
    from datetime import datetime, timedelta
    current = datetime(2026, 3, 9, 8, 30)
    close = datetime(2026, 3, 9, 18, 0)
    while current < close:
        turnos.append({
            "Fecha de Sesion": "03/09/2026",
            "Hora de Sesion": current.strftime("%H:%M:%S"),
            "Duracion": 30,
            "Estado de Sesion": "Planificada",
        })
        current += timedelta(minutes=30)
    return turnos


# =============================================================================
# PARSE FUNCTIONS
# =============================================================================

class TestParseTime:
    def test_hhmmss(self):
        assert _parse_time("08:30:00") == time(8, 30)

    def test_hhmm(self):
        assert _parse_time("14:00") == time(14, 0)

    def test_ampm(self):
        assert _parse_time("2:30 PM") == time(14, 30)

    def test_empty(self):
        assert _parse_time("") is None

    def test_none(self):
        assert _parse_time(None) is None

    def test_invalid(self):
        assert _parse_time("not a time") is None


class TestParseDuration:
    def test_integer(self):
        assert _parse_duration(30) == 30

    def test_float(self):
        assert _parse_duration(45.0) == 45

    def test_string_int(self):
        assert _parse_duration("30") == 30

    def test_hhmmss(self):
        assert _parse_duration("00:30:00") == 30

    def test_hhmm(self):
        assert _parse_duration("01:30") == 90

    def test_invalid_returns_default(self):
        assert _parse_duration("invalid") == 30


class TestParseHorarios:
    def test_standard(self, horarios_standard):
        schedule = _parse_horarios(horarios_standard)
        assert "LUNES" in schedule
        assert schedule["LUNES"] == (time(8, 30), time(18, 0))
        assert "MIERCOLES" in schedule
        assert schedule["MIERCOLES"] == (time(8, 30), time(20, 0))

    def test_handles_accented_dias(self):
        horarios = [
            {"DIA": "MIÉRCOLES", "HORA INICIO": "08:30:00", "HORA CIERRE": "20:00:00"},
            {"DIA": "SÁBADO", "HORA INICIO": "09:00:00", "HORA CIERRE": "13:00:00"},
        ]
        schedule = _parse_horarios(horarios)
        assert "MIERCOLES" in schedule
        assert "SABADO" in schedule

    def test_empty_list(self):
        assert _parse_horarios([]) == {}

    def test_skips_invalid(self):
        horarios = [
            {"DIA": "LUNES", "HORA INICIO": "", "HORA CIERRE": "18:00:00"},
            {"DIA": "", "HORA INICIO": "09:00:00", "HORA CIERRE": "18:00:00"},
        ]
        assert _parse_horarios(horarios) == {}


class TestParseOccupiedSessions:
    def test_standard(self):
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora de Sesion": "10:00:00",
                "Duracion": 30,
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        assert date(2026, 3, 9) in occupied
        sessions = occupied[date(2026, 3, 9)]
        assert len(sessions) == 1
        assert sessions[0] == (time(10, 0), time(10, 30))

    def test_multiple_days(self):
        turnos = [
            {"Fecha de Sesion": "03/09/2026", "Hora de Sesion": "10:00:00", "Duracion": 30},
            {"Fecha de Sesion": "03/10/2026", "Hora de Sesion": "11:00:00", "Duracion": 45},
        ]
        occupied = _parse_occupied_sessions(turnos)
        assert len(occupied) == 2

    def test_iso_date_format(self):
        """También parsea formato YYYY-MM-DD."""
        turnos = [
            {"Fecha de Sesion": "2026-03-09", "Hora de Sesion": "10:00:00", "Duracion": 30},
        ]
        occupied = _parse_occupied_sessions(turnos)
        assert date(2026, 3, 9) in occupied

    def test_alternative_field_name(self):
        """Campo 'Hora Sesion' como alternativa a 'Hora de Sesion'."""
        turnos = [
            {"Fecha de Sesion": "03/09/2026", "Hora Sesion": "10:00:00", "Duracion": 30},
        ]
        occupied = _parse_occupied_sessions(turnos)
        assert date(2026, 3, 9) in occupied

    def test_skips_invalid(self):
        turnos = [
            {"Fecha de Sesion": "", "Hora de Sesion": "10:00:00", "Duracion": 30},
            {"Fecha de Sesion": "03/09/2026", "Hora de Sesion": "", "Duracion": 30},
        ]
        occupied = _parse_occupied_sessions(turnos)
        assert len(occupied) == 0

    def test_duracion_takes_priority_over_finalizacion(self):
        """Duracion overrides Horario Finalizacion when both present."""
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora de Sesion": "10:00:00",
                "Duracion": 30,
                "Horario Finalizacion": "11:00",
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        assert len(sessions) == 1
        # Should use Duracion (10:30), NOT Horario Finalizacion (11:00)
        assert sessions[0] == (time(10, 0), time(10, 30))

    def test_horario_finalizacion_null_duracion(self):
        """When Duracion is None, Horario Finalizacion is the only source."""
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora Sesion": "12:30",
                "Duracion": None,
                "Horario Finalizacion": "13:30",
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        assert sessions[0] == (time(12, 30), time(13, 30))

    def test_long_session_via_horario_finalizacion(self):
        """Multi-hour session (e.g. Implantes 60min, Ocupado 4.5hr)."""
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora Sesion": "16:00",
                "Duracion": None,
                "Horario Finalizacion": "20:30",
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        # Session blocks from 16:00 to 20:30 (4.5 hours)
        assert sessions[0] == (time(16, 0), time(20, 30))

    def test_falls_back_to_duracion_when_no_finalizacion(self):
        """When Horario Finalizacion is missing, use Duracion as before."""
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora de Sesion": "09:00:00",
                "Duracion": 45,
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        assert sessions[0] == (time(9, 0), time(9, 45))

    def test_falls_back_to_default_when_both_missing(self):
        """When both are missing, falls back to DEFAULT_DURATION (30)."""
        turnos = [
            {
                "Fecha de Sesion": "03/09/2026",
                "Hora Sesion": "09:00",
                "Duracion": None,
                "Horario Finalizacion": None,
            },
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        assert sessions[0] == (time(9, 0), time(9, 30))

    def test_real_world_data_no_duracion(self):
        """Simulates actual Cloud SQL data where all Duracion=NULL."""
        turnos = [
            {"Fecha de Sesion": "03/09/2026", "Hora Sesion": "08:30", "Duracion": None, "Horario Finalizacion": "09:15"},
            {"Fecha de Sesion": "03/09/2026", "Hora Sesion": "09:00", "Duracion": None, "Horario Finalizacion": "09:30"},
            {"Fecha de Sesion": "03/09/2026", "Hora Sesion": "12:30", "Duracion": None, "Horario Finalizacion": "13:30"},
            {"Fecha de Sesion": "03/09/2026", "Hora Sesion": "16:00", "Duracion": None, "Horario Finalizacion": "20:30"},
        ]
        occupied = _parse_occupied_sessions(turnos)
        sessions = occupied[date(2026, 3, 9)]
        assert len(sessions) == 4
        # Protesis: 45 min
        assert sessions[0] == (time(8, 30), time(9, 15))
        # Alineadores: 30 min
        assert sessions[1] == (time(9, 0), time(9, 30))
        # Implantes: 60 min (NOT 30!)
        assert sessions[2] == (time(12, 30), time(13, 30))
        # Ocupado: 4.5 hours (NOT 30 min!)
        assert sessions[3] == (time(16, 0), time(20, 30))


# =============================================================================
# MERGE INTERVALS
# =============================================================================

class TestMergeIntervals:
    def test_no_overlap(self):
        intervals = [(time(9, 0), time(9, 30)), (time(10, 0), time(10, 30))]
        merged = _merge_intervals(intervals, date(2026, 3, 9))
        assert len(merged) == 2

    def test_overlapping(self):
        intervals = [(time(9, 0), time(10, 0)), (time(9, 30), time(10, 30))]
        merged = _merge_intervals(intervals, date(2026, 3, 9))
        assert len(merged) == 1
        assert merged[0] == (time(9, 0), time(10, 30))

    def test_adjacent(self):
        intervals = [(time(9, 0), time(9, 30)), (time(9, 30), time(10, 0))]
        merged = _merge_intervals(intervals, date(2026, 3, 9))
        assert len(merged) == 1
        assert merged[0] == (time(9, 0), time(10, 0))

    def test_empty(self):
        assert _merge_intervals([], date(2026, 3, 9)) == []

    def test_unsorted_input(self):
        intervals = [(time(10, 0), time(10, 30)), (time(9, 0), time(9, 30))]
        merged = _merge_intervals(intervals, date(2026, 3, 9))
        assert len(merged) == 2
        assert merged[0][0] == time(9, 0)  # Sorted


# =============================================================================
# FIND FREE SLOTS
# =============================================================================

class TestFindFreeSlots:
    def test_empty_day_30min(self):
        """Día sin turnos → slots cada 30 min (08:30-18:00 = 19 slots)."""
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(8, 30), time(18, 0),
            [], 30,
        )
        assert len(slots) == 19
        assert slots[0]["hora"] == "08:30"
        assert slots[-1]["hora"] == "17:30"

    def test_empty_day_45min(self):
        """Día sin turnos, tratamiento 45 min → menos slots."""
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(8, 30), time(18, 0),
            [], 45,
        )
        # Slots a los 30 min que caben 45 min: 8:30, 9:00, 9:30, ..., 17:00
        # 8:30+45=9:15 OK, 9:00+45=9:45 OK, ..., 17:00+45=17:45 OK, 17:30+45=18:15 NO
        assert slots[0]["hora"] == "08:30"
        assert slots[-1]["hora"] == "17:00"
        # Verificar que todos caben en el horario
        from datetime import datetime, timedelta
        for s in slots:
            start = datetime.strptime(s["hora"], "%H:%M")
            end = start + timedelta(minutes=45)
            assert end.time() <= time(18, 0)

    def test_empty_day_90min(self):
        """Día sin turnos, blanqueamiento 90 min."""
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(8, 30), time(18, 0),
            [], 90,
        )
        assert slots[0]["hora"] == "08:30"
        assert slots[-1]["hora"] == "16:30"

    def test_with_occupied_sessions(self):
        """Turnos ocupados reducen slots disponibles."""
        occupied = [
            (time(9, 0), time(9, 30)),   # 30 min
            (time(10, 0), time(10, 45)),  # 45 min
        ]
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(8, 30), time(18, 0),
            occupied, 30,
        )
        # Slot a las 8:30 (libre), no 9:00 (ocupado)
        slot_times = [s["hora"] for s in slots]
        assert "08:30" in slot_times
        assert "09:00" not in slot_times
        assert "09:30" in slot_times  # Free gap between sessions
        assert "10:00" not in slot_times
        assert "10:30" not in slot_times  # 10:00-10:45 occupied
        assert "10:45" in slot_times  # Free after session ends

    def test_fully_booked(self):
        """Día completamente ocupado → sin slots."""
        from datetime import datetime, timedelta
        # Fill 8:30 to 18:00 with 30-min sessions
        occupied = []
        current = datetime(2026, 3, 9, 8, 30)
        while current < datetime(2026, 3, 9, 18, 0):
            end = current + timedelta(minutes=30)
            occupied.append((current.time(), end.time()))
            current = end

        slots = _find_free_slots(
            date(2026, 3, 9),
            time(8, 30), time(18, 0),
            occupied, 30,
        )
        assert len(slots) == 0

    def test_gap_too_small(self):
        """Gap de 15 min entre sesiones — no cabe 30 min."""
        occupied = [
            (time(9, 0), time(9, 45)),
            (time(10, 0), time(10, 30)),
        ]
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(9, 0), time(10, 30),
            occupied, 30,
        )
        # Only gap is 9:45-10:00 (15 min) — too small for 30 min
        assert len(slots) == 0

    def test_overlapping_sessions(self):
        """Sesiones que se solapan se mergen correctamente."""
        occupied = [
            (time(10, 0), time(11, 0)),
            (time(10, 30), time(11, 30)),  # Overlaps with previous
        ]
        slots = _find_free_slots(
            date(2026, 3, 9),
            time(10, 0), time(12, 0),
            occupied, 30,
        )
        # Merged: 10:00-11:30 occupied, 11:30-12:00 free → 1 slot at 11:30
        assert len(slots) == 1
        assert slots[0]["hora"] == "11:30"


# =============================================================================
# PROFESSIONAL ASSIGNMENT
# =============================================================================

class TestGetProfessional:
    def test_monday_morning(self):
        assert _get_professional(0, time(10, 0)) == "Cynthia Hatzerian"

    def test_wednesday_morning(self):
        """Miércoles antes de 14:30 → Cynthia."""
        assert _get_professional(2, time(10, 0)) == "Cynthia Hatzerian"

    def test_wednesday_afternoon(self):
        """Miércoles 14:30-20:00 → Ana Miño."""
        assert _get_professional(2, time(14, 30)) == "Ana Miño"
        assert _get_professional(2, time(16, 0)) == "Ana Miño"
        assert _get_professional(2, time(19, 30)) == "Ana Miño"

    def test_wednesday_before_ana(self):
        """Miércoles 14:00 → Cynthia (antes de 14:30)."""
        assert _get_professional(2, time(14, 0)) == "Cynthia Hatzerian"

    def test_wednesday_limit(self):
        """Miércoles 20:00 → Cynthia (ya no es rango de Ana)."""
        assert _get_professional(2, time(20, 0)) == "Cynthia Hatzerian"

    def test_saturday(self):
        assert _get_professional(5, time(10, 0)) == "Cynthia Hatzerian"


# =============================================================================
# PREFERENCE MATCHING
# =============================================================================

class TestMatchesDayPreference:
    def test_cualquier_dia(self):
        assert _matches_day_preference(0, "cualquier dia") is True
        assert _matches_day_preference(3, "cualquier dia") is True

    def test_empty(self):
        assert _matches_day_preference(0, "") is True

    def test_single_day(self):
        assert _matches_day_preference(0, "lunes") is True
        assert _matches_day_preference(1, "lunes") is False

    def test_multiple_days(self):
        assert _matches_day_preference(0, "lunes y jueves") is True
        assert _matches_day_preference(3, "lunes y jueves") is True
        assert _matches_day_preference(2, "lunes y jueves") is False

    def test_with_accents(self):
        assert _matches_day_preference(2, "miércoles") is True

    def test_phrase(self):
        assert _matches_day_preference(4, "los viernes me quedan bien") is True
        assert _matches_day_preference(0, "los viernes me quedan bien") is False


class TestMatchesTimePreference:
    def test_cualquier_horario(self):
        assert _matches_time_preference(time(10, 0), "cualquier horario") is True

    def test_empty(self):
        assert _matches_time_preference(time(10, 0), "") is True

    def test_manana(self):
        assert _matches_time_preference(time(10, 0), "por la mañana") is True
        assert _matches_time_preference(time(15, 0), "por la mañana") is False

    def test_tarde(self):
        assert _matches_time_preference(time(15, 0), "por la tarde") is True
        assert _matches_time_preference(time(10, 0), "por la tarde") is False

    def test_despues_de_hora(self):
        assert _matches_time_preference(time(17, 0), "después de las 17") is True
        assert _matches_time_preference(time(15, 0), "después de las 17") is False

    def test_antes_de_hora(self):
        assert _matches_time_preference(time(9, 0), "antes de las 12") is True
        assert _matches_time_preference(time(14, 0), "antes de las 12") is False

    def test_a_partir_de(self):
        assert _matches_time_preference(time(15, 0), "a partir de las 15") is True
        assert _matches_time_preference(time(14, 0), "a partir de las 15") is False


# =============================================================================
# TREATMENT DURATION
# =============================================================================

class TestGetTreatmentDuration:
    """Tests usando datos reales de LISTA A I tipo tratamientos."""

    TIPOS = [
        {"TIPO DE TRATAMIENTO": "Alineadores", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Blanqueamiento", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Ortodoncia (Brackets)", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Implantes", "Duracion Turno": "00:45:00"},
        {"TIPO DE TRATAMIENTO": "Cirugia", "Duracion Turno": "01:00:00"},
        {"TIPO DE TRATAMIENTO": "Protesis", "Duracion Turno": "00:45:00"},
        {"TIPO DE TRATAMIENTO": "Urgencia odontologica", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Control", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Odontologia primera vez", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Limpieza", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Caries", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Endodoncia (Tratamiento de Conducto)", "Duracion Turno": "02:00:00"},
        {"TIPO DE TRATAMIENTO": "Otro", "Duracion Turno": "00:30:00"},
        {"TIPO DE TRATAMIENTO": "Odontopediatría", "Duracion Turno": "00:30:00"},
    ]

    def test_exact_match(self):
        assert get_treatment_duration("Control", self.TIPOS) == 30
        assert get_treatment_duration("Implantes", self.TIPOS) == 45
        assert get_treatment_duration("Cirugia", self.TIPOS) == 60

    def test_case_insensitive(self):
        assert get_treatment_duration("control", self.TIPOS) == 30
        assert get_treatment_duration("LIMPIEZA", self.TIPOS) == 30

    def test_partial_match(self):
        """'Brackets' matchea parcial con 'Ortodoncia (Brackets)'."""
        assert get_treatment_duration("Brackets", self.TIPOS) == 30

    def test_odontologia_primera_vez(self):
        assert get_treatment_duration("Odontología primera vez", self.TIPOS) == 30
        assert get_treatment_duration("Odontologia primera vez", self.TIPOS) == 30

    def test_unknown_returns_default(self):
        assert get_treatment_duration("Tratamiento desconocido", self.TIPOS) == 30

    def test_urgencia(self):
        """'Urgencia' matchea parcial con 'Urgencia odontologica'."""
        assert get_treatment_duration("Urgencia", self.TIPOS) == 30

    def test_endodoncia(self):
        """Endodoncia dura 2 horas (120 min)."""
        assert get_treatment_duration("Endodoncia (Tratamiento de Conducto)", self.TIPOS) == 120
        assert get_treatment_duration("Endodoncia", self.TIPOS) == 120

    def test_without_tipos_returns_default(self):
        """Sin tabla de tipos → default 30."""
        assert get_treatment_duration("Control", None) == 30
        assert get_treatment_duration("Cirugia", []) == 30


# =============================================================================
# SELECT BEST OPTIONS
# =============================================================================

class TestSelectBestOptions:
    def test_fewer_than_max(self):
        """Si hay menos opciones que max, retorna todas."""
        slots = [
            {"fecha": "2026-03-09", "hora": "10:00", "_hora_time": time(10, 0)},
            {"fecha": "2026-03-10", "hora": "11:00", "_hora_time": time(11, 0)},
        ]
        result = _select_best_options(slots, 3)
        assert len(result) == 2
        # Campo interno removido
        assert "_hora_time" not in result[0]

    def test_diverse_days(self):
        """Selecciona de distintos días (round-robin)."""
        slots = [
            {"fecha": "2026-03-09", "hora": "09:00", "_hora_time": time(9, 0)},
            {"fecha": "2026-03-09", "hora": "10:00", "_hora_time": time(10, 0)},
            {"fecha": "2026-03-09", "hora": "11:00", "_hora_time": time(11, 0)},
            {"fecha": "2026-03-10", "hora": "09:00", "_hora_time": time(9, 0)},
            {"fecha": "2026-03-10", "hora": "10:00", "_hora_time": time(10, 0)},
            {"fecha": "2026-03-11", "hora": "09:00", "_hora_time": time(9, 0)},
        ]
        result = _select_best_options(slots, 3)
        assert len(result) == 3
        # Debería tener una opción de cada día
        dates = {s["fecha"] for s in result}
        assert len(dates) == 3

    def test_cleans_internal_field(self):
        """Remueve _hora_time del resultado."""
        slots = [
            {"fecha": "2026-03-09", "hora": "10:00", "_hora_time": time(10, 0)},
        ]
        result = _select_best_options(slots, 3)
        assert "_hora_time" not in result[0]


# =============================================================================
# FORMAT
# =============================================================================

class TestFormatDateDisplay:
    def test_standard(self):
        result = _format_date_display(date(2026, 3, 12))
        assert result == "jueves 12 de marzo"

    def test_miercoles(self):
        result = _format_date_display(date(2026, 3, 11))
        assert "miércoles" in result

    def test_sabado(self):
        result = _format_date_display(date(2026, 3, 14))
        assert "sábado" in result


class TestFormatSlotsForClaude:
    def test_with_slots(self):
        slots = [
            {
                "fecha": "2026-03-09",
                "fecha_display": "lunes 9 de marzo",
                "hora": "10:00",
                "profesional": "Cynthia Hatzerian",
                "duracion_minutos": 30,
            },
            {
                "fecha": "2026-03-10",
                "fecha_display": "martes 10 de marzo",
                "hora": "14:00",
                "profesional": "Cynthia Hatzerian",
                "duracion_minutos": 30,
            },
        ]
        result = format_slots_for_claude(slots)
        assert "1. lunes 9 de marzo a las 10:00" in result
        assert "2. martes 10 de marzo a las 14:00" in result
        assert "Cynthia Hatzerian" in result

    def test_empty(self):
        result = format_slots_for_claude([])
        assert "No se encontraron" in result


# =============================================================================
# INTEGRATION: calculate_available_slots
# =============================================================================

class TestCalculateAvailableSlots:
    def test_basic_no_occupied(self, horarios_standard):
        """Sin turnos ocupados → retorna max opciones."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),   # Lunes
            fecha_hasta=date(2026, 3, 14),  # Sábado
            max_options=3,
        )
        assert len(slots) == 3
        # Opciones de distintos días (diversificadas)
        dates = {s["fecha"] for s in slots}
        assert len(dates) == 3

    def test_with_occupied_sessions(self, horarios_standard, turnos_parciales):
        """Con turnos ocupados → los slots no colisionan."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=turnos_parciales,
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),   # Lunes (día de los turnos)
            fecha_hasta=date(2026, 3, 9),   # Solo este día
            max_options=5,
        )
        # No debería haber slots que colisionen con 9:00, 10:30, 14:00
        for s in slots:
            assert s["hora"] != "09:00"
            assert s["hora"] != "10:30"
            assert s["hora"] != "14:00"

    def test_fully_booked_day(self, horarios_standard, dia_lleno):
        """Día completamente lleno → sin opciones para ese día."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=dia_lleno,
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),   # Lunes lleno
            fecha_hasta=date(2026, 3, 9),
        )
        assert len(slots) == 0

    def test_day_preference(self, horarios_standard):
        """Filtro por día de la semana."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),   # Lunes
            fecha_hasta=date(2026, 3, 14),  # Sábado
            preferencia_dia="miércoles",
            max_options=3,
        )
        for s in slots:
            assert s["fecha"] == "2026-03-11"  # Miércoles

    def test_time_preference_manana(self, horarios_standard):
        """Filtro por horario mañana."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            preferencia_horario="por la mañana",
            max_options=20,
        )
        for s in slots:
            h, m = map(int, s["hora"].split(":"))
            assert h < 13

    def test_time_preference_tarde(self, horarios_standard):
        """Filtro por horario tarde."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            preferencia_horario="por la tarde",
            max_options=20,
        )
        for s in slots:
            h, m = map(int, s["hora"].split(":"))
            assert h >= 13

    def test_wednesday_ana_mino(self, horarios_standard):
        """Miércoles tarde → profesional Ana Miño."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 11),  # Miércoles
            fecha_hasta=date(2026, 3, 11),
            preferencia_horario="por la tarde",
            max_options=20,
        )
        # Slots antes de 14:30 deberían ser Cynthia, después Ana Miño
        for s in slots:
            h, m = map(int, s["hora"].split(":"))
            if h > 14 or (h == 14 and m >= 30):
                assert s["profesional"] == "Ana Miño"
            else:
                assert s["profesional"] == "Cynthia Hatzerian"

    def test_urgencia_1_week(self, horarios_standard):
        """Urgencia busca en 1 semana."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Urgencia",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 15),  # ~1 semana
            max_options=3,
        )
        assert len(slots) == 3
        # Todas dentro de la semana
        for s in slots:
            assert s["fecha"] <= "2026-03-15"

    def test_endodoncia_120min(self, horarios_standard):
        """Endodoncia 120 min → slots más limitados (usa duracion_minutos param)."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Endodoncia",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            max_options=20,
            duracion_minutos=120,
        )
        assert len(slots) > 0
        for s in slots:
            assert s["duracion_minutos"] == 120
        # Menos slots que un turno de 30 min
        slots_30 = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            max_options=50,
            duracion_minutos=30,
        )
        assert len(slots) < len(slots_30)

    def test_no_sunday(self, horarios_standard):
        """Domingo no tiene horarios → no genera slots."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 15),  # Domingo
            fecha_hasta=date(2026, 3, 15),
        )
        assert len(slots) == 0

    def test_returns_structured_data(self, horarios_standard):
        """Verificar estructura de los slots retornados."""
        slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            max_options=1,
        )
        assert len(slots) == 1
        slot = slots[0]
        assert "fecha" in slot
        assert "fecha_display" in slot
        assert "hora" in slot
        assert "profesional" in slot
        assert "duracion_minutos" in slot
        # Campo interno no presente
        assert "_hora_time" not in slot

    def test_saturday_shorter_hours(self, horarios_standard):
        """Sábado 9:00-13:00 → menos slots que un lunes."""
        lunes_slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 9),
            fecha_hasta=date(2026, 3, 9),
            max_options=50,
        )
        sabado_slots = calculate_available_slots(
            horarios=horarios_standard,
            turnos_ocupados=[],
            tratamiento="Control",
            fecha_desde=date(2026, 3, 14),
            fecha_hasta=date(2026, 3, 14),
            max_options=50,
        )
        assert len(sabado_slots) < len(lunes_slots)
