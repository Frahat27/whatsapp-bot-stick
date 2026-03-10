"""
Tests unitarios para los 15 tool handlers de ConversationManager.

Verifica que cada handler invoca los metodos correctos de ClinicRepository
y retorna los dicts de status esperados.

Mocks: ClinicRepository (no DB real), clinic_db session (no commits reales).
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.services.conversation_manager import ConversationManager, _safe_patient_summary


# =============================================================================
# Fixtures: ConversationManager con ClinicRepository mockeado
# =============================================================================

@pytest.fixture
def mock_clinic_db():
    """Mock de AsyncSession para clinic_db (commit, rollback)."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_clinic_repo():
    """ClinicRepository completamente mockeado."""
    repo = MagicMock()
    # Pacientes
    repo.find_patient_by_phone = AsyncMock(return_value=None)
    repo.create_patient = AsyncMock()
    # Leads
    repo.find_lead_by_phone = AsyncMock(return_value=None)
    repo.create_lead = AsyncMock()
    # Sesiones / Turnos
    repo.get_all_horarios = AsyncMock(return_value=[])
    repo.find_sessions_in_range = AsyncMock(return_value=[])
    repo.get_all_treatment_types = AsyncMock(return_value=[])
    repo.create_session = AsyncMock()
    repo.find_patient_active_sessions = AsyncMock(return_value=[])
    repo.update_session = AsyncMock()
    # Tarifario
    repo.find_tariff = AsyncMock(return_value=None)
    repo.find_all_tariffs = AsyncMock(return_value=[])
    # Presupuestos
    repo.find_budgets_by_patient = AsyncMock(return_value=[])
    # Pagos
    repo.find_payments = AsyncMock(return_value=[])
    repo.create_payment = AsyncMock()
    return repo


@pytest.fixture
def manager(mock_clinic_repo, mock_clinic_db):
    """ConversationManager con DB mock y ClinicRepository mockeado."""
    with patch("src.services.conversation_manager.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            conversation_history_limit=20,
            admin_phone_list=[],
        )
        mgr = ConversationManager(db=MagicMock(), clinic_db=mock_clinic_db)
        mgr.clinic_repo = mock_clinic_repo
        return mgr


# =============================================================================
# 1. IDENTIFICACION
# =============================================================================

class TestBuscarPaciente:
    async def test_calls_find_patient_by_phone(self, manager, mock_clinic_repo):
        mock_paciente = MagicMock()
        mock_paciente.to_appsheet_dict.return_value = {"Paciente": "Test", "ID Paciente": "PAC-1"}
        mock_clinic_repo.find_patient_by_phone = AsyncMock(return_value=mock_paciente)

        result = await manager._tool_buscar_paciente({"telefono": "1112345678"})

        mock_clinic_repo.find_patient_by_phone.assert_called_once_with("1112345678")
        assert result["status"] == "found"
        assert result["paciente"]["Paciente"] == "Test"

    async def test_not_found(self, manager, mock_clinic_repo):
        result = await manager._tool_buscar_paciente({"telefono": "0000000000"})
        assert result["status"] == "not_found"


class TestBuscarLead:
    async def test_calls_find_lead_by_phone(self, manager, mock_clinic_repo):
        mock_lead = MagicMock()
        mock_lead.to_appsheet_dict.return_value = {"Apellido y Nombre": "Test", "ID Lead": "LEAD-1"}
        mock_clinic_repo.find_lead_by_phone = AsyncMock(return_value=mock_lead)

        result = await manager._tool_buscar_lead({"telefono": "1112345678"})

        mock_clinic_repo.find_lead_by_phone.assert_called_once_with("1112345678")
        assert result["status"] == "found"
        assert "lead" in result

    async def test_not_found(self, manager, mock_clinic_repo):
        result = await manager._tool_buscar_lead({"telefono": "0000000000"})
        assert result["status"] == "not_found"


class TestCrearLead:
    async def test_calls_create_lead_with_correct_args(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_lead = MagicMock()
        mock_lead.to_appsheet_dict.return_value = {
            "Apellido y Nombre": "Garcia, Juan",
            "Telefono (Whatsapp)": "+5491198765432",
            "Estado del Lead (Temp)": "Nuevo",
            "Motivo Interes": "Consulta alineadores",
        }
        mock_clinic_repo.create_lead = AsyncMock(return_value=mock_lead)

        result = await manager._tool_crear_lead({
            "nombre": "Garcia, Juan",
            "telefono": "1198765432",
            "motivo": "Consulta alineadores",
        })

        assert result["status"] == "created"
        assert "lead" in result

        # Verificar argumentos pasados a create_lead
        call_kwargs = mock_clinic_repo.create_lead.call_args
        assert call_kwargs[1]["nombre"] == "Garcia, Juan"
        assert call_kwargs[1]["motivo_interes"] == "Consulta alineadores"
        # Verificar que se hizo commit en clinic_db
        mock_clinic_db.commit.assert_called_once()

    async def test_motivo_default_empty(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_lead = MagicMock()
        mock_lead.to_appsheet_dict.return_value = {"Apellido y Nombre": "Test"}
        mock_clinic_repo.create_lead = AsyncMock(return_value=mock_lead)

        await manager._tool_crear_lead({
            "nombre": "Test",
            "telefono": "1100000000",
        })

        call_kwargs = mock_clinic_repo.create_lead.call_args[1]
        assert call_kwargs["motivo_interes"] == ""


class TestCrearPaciente:
    async def test_calls_create_patient_with_correct_args(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_paciente = MagicMock()
        mock_paciente.to_appsheet_dict.return_value = {
            "Paciente": "Perez, Maria",
            "DNI / Pasaporte": "40123456",
        }
        mock_clinic_repo.create_patient = AsyncMock(return_value=mock_paciente)

        result = await manager._tool_crear_paciente({
            "nombre": "Perez, Maria",
            "dni": "40123456",
            "fecha_nacimiento": "15/03/1990",
            "telefono": "1155667788",
            "mail": "maria@test.com",
            "sexo": "Femenino",
        })

        assert result["status"] == "created"
        assert "paciente" in result

        # Verificar argumentos pasados a create_patient
        call_kwargs = mock_clinic_repo.create_patient.call_args[1]
        assert call_kwargs["nombre"] == "Perez, Maria"
        assert call_kwargs["dni"] == "40123456"
        assert call_kwargs["fecha_nacimiento"] == date(1990, 3, 15)
        assert call_kwargs["sexo"] == "Femenino"
        assert call_kwargs["email"] == "maria@test.com"
        # Verificar commit
        mock_clinic_db.commit.assert_called_once()

    async def test_sexo_default_otro(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_paciente = MagicMock()
        mock_paciente.to_appsheet_dict.return_value = {"Paciente": "Test"}
        mock_clinic_repo.create_patient = AsyncMock(return_value=mock_paciente)

        await manager._tool_crear_paciente({
            "nombre": "Test, User",
            "dni": "00000000",
            "fecha_nacimiento": "01/01/2000",
            "telefono": "1100000000",
            "mail": "test@test.com",
        })

        call_kwargs = mock_clinic_repo.create_patient.call_args[1]
        assert call_kwargs["sexo"] == "Otro"

    async def test_referido_optional(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_paciente = MagicMock()
        mock_paciente.to_appsheet_dict.return_value = {"Paciente": "Test"}
        mock_clinic_repo.create_patient = AsyncMock(return_value=mock_paciente)

        await manager._tool_crear_paciente({
            "nombre": "Test, User",
            "dni": "00000000",
            "fecha_nacimiento": "01/01/2000",
            "telefono": "1100000000",
            "mail": "test@test.com",
            "referido_por": "Instagram",
        })

        call_kwargs = mock_clinic_repo.create_patient.call_args[1]
        assert call_kwargs["referido"] == "Instagram"


# =============================================================================
# 2. TURNOS
# =============================================================================

class TestConsultarHorarios:
    async def test_calls_get_all_horarios(self, manager, mock_clinic_repo):
        mock_horario = MagicMock()
        mock_horario.to_appsheet_dict.return_value = {"DIA": "Lunes", "HORA INICIO": "08:30:00"}
        mock_clinic_repo.get_all_horarios = AsyncMock(return_value=[mock_horario])

        result = await manager._tool_consultar_horarios({})

        mock_clinic_repo.get_all_horarios.assert_called_once()
        assert result["status"] == "ok"
        assert len(result["horarios"]) == 1


class TestBuscarDisponibilidad:
    async def test_queries_sessions_horarios_and_tipos(self, manager, mock_clinic_repo):
        # Mock sesiones (empty = sin turnos ocupados)
        mock_clinic_repo.find_sessions_in_range = AsyncMock(return_value=[])

        # Mock horarios
        mock_horario_lunes = MagicMock()
        mock_horario_lunes.to_appsheet_dict.return_value = {
            "DIA": "LUNES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00",
        }
        mock_horario_martes = MagicMock()
        mock_horario_martes.to_appsheet_dict.return_value = {
            "DIA": "MARTES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00",
        }
        mock_clinic_repo.get_all_horarios = AsyncMock(
            return_value=[mock_horario_lunes, mock_horario_martes]
        )

        # Mock tipos de tratamiento
        mock_tipo = MagicMock()
        mock_tipo.to_appsheet_dict.return_value = {
            "TIPO DE TRATAMIENTO": "Odontologia primera vez",
            "Duracion Turno": "00:30:00",
        }
        mock_clinic_repo.get_all_treatment_types = AsyncMock(return_value=[mock_tipo])

        result = await manager._tool_buscar_disponibilidad({
            "preferencia_dia": "lunes",
            "semanas": 2,
        })

        # Verificar que se llamaron los 3 metodos del repo
        mock_clinic_repo.find_sessions_in_range.assert_called_once()
        mock_clinic_repo.get_all_horarios.assert_called_once()
        mock_clinic_repo.get_all_treatment_types.assert_called_once()

        assert result["status"] == "ok"
        assert "opciones_disponibles" in result
        assert len(result["opciones_disponibles"]) > 0
        assert "duracion_minutos" in result


class TestAgendarTurno:
    async def test_calls_create_session_with_correct_args(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_sesion = MagicMock()
        mock_sesion.to_appsheet_dict.return_value = {
            "ID Sesion": "SES-NEW",
            "ID PACIENTE": "ANT-15",
            "Paciente": "Antunez, Florencia",
            "Tratamiento": "Odontologia primera vez",
            "Fecha de Sesion": "03/10/2026",
            "Hora Sesion": "10:00",
            "Profesional Asignado": "Cynthia Hatzerian",
        }
        mock_clinic_repo.create_session = AsyncMock(return_value=mock_sesion)

        result = await manager._tool_agendar_turno({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Antunez, Florencia",
            "fecha": "10/03/2026",
            "hora": "10:00",
            "tratamiento": "Odontologia primera vez",
            "profesional": "Cynthia Hatzerian",
            "observaciones": "Interesada en alineadores",
        })

        assert result["status"] == "created"
        assert "turno" in result

        # Verificar argumentos pasados a create_session
        call_kwargs = mock_clinic_repo.create_session.call_args[1]
        assert call_kwargs["id_paciente"] == "ANT-15"
        assert call_kwargs["paciente_nombre"] == "Antunez, Florencia"
        assert call_kwargs["tratamiento"] == "Odontologia primera vez"
        assert call_kwargs["fecha"] == date(2026, 3, 10)
        assert call_kwargs["hora"] == time(10, 0)
        assert call_kwargs["profesional"] == "Cynthia Hatzerian"
        assert call_kwargs["descripcion"] == "Interesada en alineadores"
        # Verificar commit
        mock_clinic_db.commit.assert_called_once()


class TestBuscarTurnoPaciente:
    async def test_calls_find_patient_active_sessions(self, manager, mock_clinic_repo):
        mock_turno = MagicMock()
        mock_turno.fecha = date(2026, 3, 10)  # Martes
        mock_turno.to_appsheet_dict.return_value = {
            "ID Sesion": "SES-1",
            "ID PACIENTE": "ANT-15",
            "Estado de Sesion": "Planificada",
        }
        mock_clinic_repo.find_patient_active_sessions = AsyncMock(return_value=[mock_turno])

        result = await manager._tool_buscar_turno_paciente({"paciente_id": "ANT-15"})

        mock_clinic_repo.find_patient_active_sessions.assert_called_once_with("ANT-15")
        assert result["status"] == "ok"
        assert len(result["turnos"]) == 1
        # Verificar enriquecimiento con dia de semana
        assert result["turnos"][0]["Dia de Semana"] == "martes"


class TestModificarTurno:
    async def test_calls_update_session_with_correct_args(self, manager, mock_clinic_repo, mock_clinic_db):
        # Mock get_session para que devuelva la sesion actual con duracion
        mock_sesion_actual = MagicMock()
        mock_sesion_actual.duracion = 30
        mock_clinic_repo.get_session = AsyncMock(return_value=mock_sesion_actual)

        mock_sesion = MagicMock()
        mock_sesion.to_appsheet_dict.return_value = {
            "ID Sesion": "SES-001",
            "Fecha de Sesion": "03/15/2026",
            "Hora Sesion": "14:00",
            "Profesional Asignado": "Ana Mino",
        }
        mock_clinic_repo.update_session = AsyncMock(return_value=mock_sesion)

        result = await manager._tool_modificar_turno({
            "turno_id": "SES-001",
            "nueva_fecha": "15/03/2026",
            "nueva_hora": "14:00",
            "profesional": "Ana Mino",
        })

        assert result["status"] == "modified"
        assert "turno" in result

        # Verificar argumentos: turno_id como primer arg, kwargs con fecha/hora/profesional/hora_fin
        call_args = mock_clinic_repo.update_session.call_args
        assert call_args[0][0] == "SES-001"  # session_id positional
        assert call_args[1]["fecha"] == date(2026, 3, 15)
        assert call_args[1]["hora"] == time(14, 0)
        assert call_args[1]["hora_fin"] == time(14, 30)  # 14:00 + 30min
        assert call_args[1]["profesional"] == "Ana Mino"
        # Verificar commit
        mock_clinic_db.commit.assert_called_once()

    async def test_turno_not_found_returns_error(self, manager, mock_clinic_repo, mock_clinic_db):
        # Mock get_session (necesario para recalcular hora_fin)
        mock_clinic_repo.get_session = AsyncMock(return_value=None)
        mock_clinic_repo.update_session = AsyncMock(return_value=None)

        result = await manager._tool_modificar_turno({
            "turno_id": "SES-NONEXISTENT",
            "nueva_fecha": "15/03/2026",
            "nueva_hora": "14:00",
            "profesional": "Ana Mino",
        })

        assert result["status"] == "error"


class TestCancelarTurno:
    async def test_calls_update_session_with_estado_cancelada(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_sesion = MagicMock()
        mock_sesion.to_appsheet_dict.return_value = {
            "ID Sesion": "SES-002",
            "Estado de Sesion": "Cancelada",
        }
        mock_clinic_repo.update_session = AsyncMock(return_value=mock_sesion)

        result = await manager._tool_cancelar_turno({"turno_id": "SES-002"})

        assert result["status"] == "cancelled"
        assert "turno" in result

        # Verificar que se llamo con estado="Cancelada"
        call_args = mock_clinic_repo.update_session.call_args
        assert call_args[0][0] == "SES-002"
        assert call_args[1]["estado"] == "Cancelada"
        # Verificar commit
        mock_clinic_db.commit.assert_called_once()

    async def test_turno_not_found_returns_error(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_clinic_repo.update_session = AsyncMock(return_value=None)

        result = await manager._tool_cancelar_turno({"turno_id": "SES-NONEXISTENT"})

        assert result["status"] == "error"


# =============================================================================
# 3. PRECIOS Y PRESUPUESTOS
# =============================================================================

class TestConsultarTarifario:
    async def test_found_exact_match(self, manager, mock_clinic_repo):
        mock_tarifa = MagicMock()
        mock_tarifa.to_appsheet_dict.return_value = {
            "Tratamiento Detalle": "Alineadores",
            "Precio": 100000,
        }
        mock_clinic_repo.find_tariff = AsyncMock(return_value=mock_tarifa)

        result = await manager._tool_consultar_tarifario({"tratamiento": "Alineadores"})

        mock_clinic_repo.find_tariff.assert_called_once_with("Alineadores")
        assert result["status"] == "ok"
        assert len(result["tarifas"]) == 1

    async def test_not_found_falls_back_to_all(self, manager, mock_clinic_repo):
        mock_clinic_repo.find_tariff = AsyncMock(return_value=None)
        mock_clinic_repo.find_all_tariffs = AsyncMock(return_value=[])

        result = await manager._tool_consultar_tarifario({"tratamiento": "NoExiste"})

        mock_clinic_repo.find_tariff.assert_called_once_with("NoExiste")
        mock_clinic_repo.find_all_tariffs.assert_called_once()
        assert result["status"] == "not_found"

    async def test_not_found_returns_all_when_available(self, manager, mock_clinic_repo):
        mock_clinic_repo.find_tariff = AsyncMock(return_value=None)
        mock_tarifa = MagicMock()
        mock_tarifa.to_appsheet_dict.return_value = {"Tratamiento Detalle": "Otro", "Precio": 5000}
        mock_clinic_repo.find_all_tariffs = AsyncMock(return_value=[mock_tarifa])

        result = await manager._tool_consultar_tarifario({"tratamiento": "NoExiste"})

        assert result["status"] == "ok"
        assert len(result["tarifas"]) == 1


class TestConsultarPresupuesto:
    async def test_calls_find_budgets_by_patient(self, manager, mock_clinic_repo):
        mock_presupuesto = MagicMock()
        mock_presupuesto.to_appsheet_dict.return_value = {
            "ID Presupuesto": "PRES-1",
            "ID Paciente": "ANT-15",
        }
        mock_clinic_repo.find_budgets_by_patient = AsyncMock(return_value=[mock_presupuesto])

        result = await manager._tool_consultar_presupuesto({"paciente_id": "ANT-15"})

        mock_clinic_repo.find_budgets_by_patient.assert_called_once_with("ANT-15")
        assert result["status"] == "ok"
        assert len(result["presupuestos"]) == 1


# =============================================================================
# 4. PAGOS
# =============================================================================

class TestBuscarPago:
    async def test_calls_find_payments_with_all_filters(self, manager, mock_clinic_repo):
        mock_clinic_repo.find_payments = AsyncMock(return_value=[])

        await manager._tool_buscar_pago({
            "paciente_id": "ANT-15",
            "fecha": "03/03/2026",
            "monto": "20000",
            "metodo_pago": "Transferencia",
        })

        call_kwargs = mock_clinic_repo.find_payments.call_args[1]
        assert call_kwargs["patient_id"] == "ANT-15"
        assert call_kwargs["fecha"] == date(2026, 3, 3)
        assert call_kwargs["monto"] == Decimal("20000")
        assert call_kwargs["metodo"] == "Transferencia"

    async def test_detects_duplicado(self, manager, mock_clinic_repo):
        mock_pago = MagicMock()
        mock_pago.to_appsheet_dict.return_value = {"ID Pago": "PAG-1"}
        mock_clinic_repo.find_payments = AsyncMock(return_value=[mock_pago])

        result = await manager._tool_buscar_pago({
            "paciente_id": "ANT-15",
            "fecha": "03/03/2026",
            "monto": "20000",
        })

        assert result["duplicado"] is True

    async def test_minimal_filter_only_paciente(self, manager, mock_clinic_repo):
        mock_clinic_repo.find_payments = AsyncMock(return_value=[])

        await manager._tool_buscar_pago({"paciente_id": "ANT-15"})

        call_kwargs = mock_clinic_repo.find_payments.call_args[1]
        assert call_kwargs["patient_id"] == "ANT-15"
        assert call_kwargs["fecha"] is None
        assert call_kwargs["monto"] is None
        assert call_kwargs["metodo"] is None


class TestRegistrarPago:
    async def test_calls_create_payment_with_correct_args(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_pago = MagicMock()
        mock_pago.to_appsheet_dict.return_value = {
            "ID Pago": "PAG-NEW",
            "ID PACIENTE": "ANT-15",
            "Paciente": "Antunez, Florencia",
            "Tratamiento": "Odontologia primera vez",
            "Fecha del Pago": "03/03/2026",
            "Monto Pagado": 20000,
            "Moneda": "PESOS",
            "Metodo de Pago": "Transferencia",
            "Tipo de Pago": "Sena",
            "Estado del Pago": "Confirmado",
            "CUENTA": "CYNTHIA",
        }
        mock_clinic_repo.create_payment = AsyncMock(return_value=mock_pago)

        result = await manager._tool_registrar_pago({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Antunez, Florencia",
            "tratamiento": "Odontologia primera vez",
            "fecha": "03/03/2026",
            "monto": 20000,
            "metodo_pago": "Transferencia",
            "tipo_pago": "Sena",
            "moneda": "PESOS",
        })

        assert result["status"] == "created"
        assert "pago" in result

        # Verificar argumentos pasados a create_payment
        call_kwargs = mock_clinic_repo.create_payment.call_args[1]
        assert call_kwargs["id_paciente"] == "ANT-15"
        assert call_kwargs["paciente_nombre"] == "Antunez, Florencia"
        assert call_kwargs["tratamiento"] == "Odontologia primera vez"
        assert call_kwargs["fecha"] == date(2026, 3, 3)
        assert call_kwargs["monto"] == Decimal("20000")
        assert call_kwargs["metodo_pago"] == "Transferencia"
        assert call_kwargs["tipo_pago"] == "Sena"
        assert call_kwargs["moneda"] == "PESOS"
        # Verificar commit
        mock_clinic_db.commit.assert_called_once()

    async def test_moneda_default_pesos(self, manager, mock_clinic_repo, mock_clinic_db):
        mock_pago = MagicMock()
        mock_pago.to_appsheet_dict.return_value = {"ID Pago": "PAG-NEW"}
        mock_clinic_repo.create_payment = AsyncMock(return_value=mock_pago)

        await manager._tool_registrar_pago({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Test",
            "tratamiento": "Test",
            "fecha": "01/01/2026",
            "monto": 5000,
            "metodo_pago": "Efectivo",
            "tipo_pago": "Arancel",
        })

        call_kwargs = mock_clinic_repo.create_payment.call_args[1]
        assert call_kwargs["moneda"] == "PESOS"


# =============================================================================
# 5. TAREAS PENDIENTES
# =============================================================================

class TestCrearTareaPendiente:
    async def test_calls_add_pending_task(self, manager):
        with patch("src.services.conversation_manager.add_pending_task", new_callable=AsyncMock) as mock_task:
            mock_task.return_value = {"status": "ok"}
            result = await manager._tool_crear_tarea_pendiente({
                "tipo": "Urgencia",
                "contexto": "Paciente con dolor agudo",
                "paciente": "Test User",
                "telefono": "1100000000",
            })
            mock_task.assert_called_once()
            assert mock_task.call_args[1]["tipo"] == "Urgencia"


# =============================================================================
# 6. HELPER: _safe_patient_summary
# =============================================================================

class TestSafePatientSummary:
    def test_extracts_correct_fields(self):
        paciente = {
            "Paciente": "Garcia, Juan",
            "ID Paciente": "ANT-15",
            "DNI / Pasaporte": "40123456",
            "email": "juan@test.com",
            "Estado del Paciente": "Activo",
            "Tratamiento": "Alineadores",
            "SALDO PEND": "50000",
            "Proximo Turno": "10/03/2026",
        }
        result = _safe_patient_summary(paciente)
        assert "nombre: Garcia, Juan" in result
        assert "id: ANT-15" in result
        assert "dni: 40123456" in result
        assert "email: juan@test.com" in result
        assert "saldo_pendiente: 50000" in result

    def test_skips_empty_and_completar(self):
        paciente = {
            "Paciente": "Test",
            "email": "",
            "Tratamiento": "COMPLETAR",
        }
        result = _safe_patient_summary(paciente)
        assert "nombre: Test" in result
        assert "email" not in result
        assert "COMPLETAR" not in result

    def test_empty_returns_datos_limitados(self):
        result = _safe_patient_summary({})
        assert result == "Datos limitados"

    def test_old_field_names_not_used(self):
        """Verifica que NO usa nombres de campo viejos."""
        paciente = {
            "Nombre": "Campo viejo",        # Viejo -- deberia ser "Paciente"
            "_RowNumber": 5,                  # Viejo -- deberia ser "ID Paciente"
        }
        result = _safe_patient_summary(paciente)
        # No debe extraer datos de los campos viejos
        assert "Campo viejo" not in result
