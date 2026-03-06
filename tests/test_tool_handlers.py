"""
Tests unitarios para los 15 tool handlers de ConversationManager.

Verifica que cada handler construye los dicts correctos para AppSheet,
con los nombres de campos que coinciden con api_calls_map.md.

Mocks: AppSheet client (no API real).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.services.conversation_manager import ConversationManager, _safe_patient_summary


# =============================================================================
# Fixture: ConversationManager con AppSheet mockeado
# =============================================================================

@pytest.fixture
def mock_appsheet():
    """AppSheet client completamente mockeado."""
    client = MagicMock()
    client.find = AsyncMock(return_value=[])
    client.add = AsyncMock(return_value=[{"ID": "MOCK-1"}])
    client.edit = AsyncMock(return_value=[{"ID": "MOCK-1"}])
    client.find_patient_by_phone = AsyncMock(return_value=None)
    client.find_lead_by_phone = AsyncMock(return_value=None)
    return client


@pytest.fixture
def manager(mock_appsheet):
    """ConversationManager con DB=None y AppSheet mockeado."""
    with patch("src.services.conversation_manager.get_appsheet_client", return_value=mock_appsheet):
        mgr = ConversationManager(db=MagicMock())
        mgr.appsheet = mock_appsheet
        return mgr


# =============================================================================
# 1. IDENTIFICACIÓN
# =============================================================================

class TestBuscarPaciente:
    async def test_calls_find_patient_by_phone(self, manager, mock_appsheet):
        mock_appsheet.find_patient_by_phone.return_value = {"Paciente": "Test"}
        result = await manager._tool_buscar_paciente({"telefono": "1112345678"})
        mock_appsheet.find_patient_by_phone.assert_called_once_with("1112345678")
        assert result["status"] == "found"

    async def test_not_found(self, manager, mock_appsheet):
        result = await manager._tool_buscar_paciente({"telefono": "0000000000"})
        assert result["status"] == "not_found"


class TestBuscarLead:
    async def test_calls_find_lead_by_phone(self, manager, mock_appsheet):
        mock_appsheet.find_lead_by_phone.return_value = {"Apellido y Nombre": "Test"}
        result = await manager._tool_buscar_lead({"telefono": "1112345678"})
        mock_appsheet.find_lead_by_phone.assert_called_once_with("1112345678")
        assert result["status"] == "found"

    async def test_not_found(self, manager, mock_appsheet):
        result = await manager._tool_buscar_lead({"telefono": "0000000000"})
        assert result["status"] == "not_found"


class TestCrearLead:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_crear_lead({
            "nombre": "García, Juan",
            "telefono": "1198765432",
            "motivo": "Consulta alineadores",
        })
        assert result["status"] == "created"

        # Verificar row enviada a AppSheet
        call_args = mock_appsheet.add.call_args
        table = call_args[0][0]
        rows = call_args[0][1]
        row = rows[0]

        assert table == "BBDD LEADS"
        assert row["Apellido y Nombre"] == "García, Juan"
        assert row["Telefono (Whatsapp)"] == "1198765432"
        assert row["Estado del Lead (Temp)"] == "Nuevo"
        assert row["Motivo Interes"] == "Consulta alineadores"
        assert "Fecha Creacion" in row
        # NO debe tener "Canal" (campo que no existe en AppSheet)
        assert "Canal" not in row

    async def test_motivo_default_empty(self, manager, mock_appsheet):
        await manager._tool_crear_lead({
            "nombre": "Test",
            "telefono": "1100000000",
        })
        row = mock_appsheet.add.call_args[0][1][0]
        assert row["Motivo Interes"] == ""


class TestCrearPaciente:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_crear_paciente({
            "nombre": "Pérez, María",
            "dni": "40123456",
            "fecha_nacimiento": "15/03/1990",
            "telefono": "1155667788",
            "mail": "maria@test.com",
            "sexo": "Femenino",
        })
        assert result["status"] == "created"

        row = mock_appsheet.add.call_args[0][1][0]
        table = mock_appsheet.add.call_args[0][0]

        assert table == "BBDD PACIENTES"
        # Nombre de campo es "Paciente", no "Nombre"
        assert row["Paciente"] == "Pérez, María"
        assert row["DNI / Pasaporte"] == "40123456"
        # Fecha convertida a MM/DD/YYYY
        assert row["Fecha Nacimiento"] == "03/15/1990"
        assert row["Sexo"] == "Femenino"
        assert row["Telefono (Whatsapp)"] == "1155667788"
        # email en minúscula
        assert row["email"] == "maria@test.com"
        # NO debe tener "Nombre" (campo incorrecto)
        assert "Nombre" not in row

    async def test_sexo_default_otro(self, manager, mock_appsheet):
        await manager._tool_crear_paciente({
            "nombre": "Test, User",
            "dni": "00000000",
            "fecha_nacimiento": "01/01/2000",
            "telefono": "1100000000",
            "mail": "test@test.com",
        })
        row = mock_appsheet.add.call_args[0][1][0]
        assert row["Sexo"] == "Otro"

    async def test_referido_optional(self, manager, mock_appsheet):
        await manager._tool_crear_paciente({
            "nombre": "Test, User",
            "dni": "00000000",
            "fecha_nacimiento": "01/01/2000",
            "telefono": "1100000000",
            "mail": "test@test.com",
            "referido_por": "Instagram",
        })
        row = mock_appsheet.add.call_args[0][1][0]
        assert row["Referido"] == "Instagram"


# =============================================================================
# 2. TURNOS
# =============================================================================

class TestConsultarHorarios:
    async def test_calls_find_horarios(self, manager, mock_appsheet):
        mock_appsheet.find.return_value = [{"Dia": "Lunes"}]
        result = await manager._tool_consultar_horarios({})
        mock_appsheet.find.assert_called_once_with("LISTA O | HORARIOS DE ATENCION")
        assert result["status"] == "ok"


class TestBuscarDisponibilidad:
    async def test_filter_uses_correct_field_names(self, manager, mock_appsheet):
        result = await manager._tool_buscar_disponibilidad({
            "preferencia_dia": "lunes",
            "semanas": 2,
        })
        assert result["status"] == "ok"

        # Verificar selector del Find
        call_args = mock_appsheet.find.call_args_list
        # Primer call = BBDD SESIONES, segundo = horarios
        sesiones_call = call_args[0]
        selector = sesiones_call[1].get("selector", sesiones_call[0][1] if len(sesiones_call[0]) > 1 else "")

        # Verificar que usa nombres correctos de campos
        assert "Fecha de Sesion" in selector  # NO "Fecha"
        assert "Estado de Sesion" in selector  # NO "Estado Sesion"
        assert "Cancelada" in selector
        # Verificar que NO tiene comillas alrededor del nombre de tabla
        assert 'Filter(BBDD SESIONES,' in selector


class TestAgendarTurno:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_agendar_turno({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Antúnez, Florencia",
            "fecha": "10/03/2026",
            "hora": "10:00",
            "tratamiento": "Odontologia primera vez",
            "profesional": "Cynthia Hatzerian",
            "observaciones": "Interesada en alineadores",
        })
        assert result["status"] == "created"

        row = mock_appsheet.add.call_args[0][1][0]
        table = mock_appsheet.add.call_args[0][0]

        assert table == "BBDD SESIONES"
        assert row["ID PACIENTE"] == "ANT-15"
        assert row["Paciente"] == "Antúnez, Florencia"
        assert row["Tratamiento"] == "Odontologia primera vez"
        assert row["Fecha de Sesion"] == "03/10/2026"  # DD/MM → MM/DD
        assert row["Hora Sesion"] == "10:00"
        assert row["Profesional Asignado"] == "Cynthia Hatzerian"
        assert row["Descripcion de la sesion"] == "Interesada en alineadores"
        # NO debe tener "Estado Sesion" (se auto-genera)
        assert "Estado Sesion" not in row
        assert "Estado de Sesion" not in row


class TestBuscarTurnoPaciente:
    async def test_filter_uses_correct_field_names(self, manager, mock_appsheet):
        await manager._tool_buscar_turno_paciente({"paciente_id": "ANT-15"})

        call_args = mock_appsheet.find.call_args
        selector = call_args[1].get("selector", call_args[0][1] if len(call_args[0]) > 1 else "")

        assert "ID PACIENTE" in selector  # NO "ID Paciente"
        assert "Estado de Sesion" in selector
        assert "Planificada" in selector
        assert "Confirmada" in selector
        assert 'Filter(BBDD SESIONES,' in selector


class TestModificarTurno:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_modificar_turno({
            "turno_id": "SES-001",
            "nueva_fecha": "15/03/2026",
            "nueva_hora": "14:00",
            "profesional": "Ana Miño",
        })
        assert result["status"] == "modified"

        row = mock_appsheet.edit.call_args[0][1][0]

        # Key field es "ID Sesion", NO "_RowNumber"
        assert row["ID Sesion"] == "SES-001"
        assert row["Fecha de Sesion"] == "03/15/2026"
        assert row["Hora Sesion"] == "14:00"
        assert row["Profesional Asignado"] == "Ana Miño"
        assert "_RowNumber" not in row


class TestCancelarTurno:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_cancelar_turno({"turno_id": "SES-002"})
        assert result["status"] == "cancelled"

        row = mock_appsheet.edit.call_args[0][1][0]

        assert row["ID Sesion"] == "SES-002"
        assert row["Estado de Sesion"] == "Cancelada"
        assert "_RowNumber" not in row


# =============================================================================
# 3. PRECIOS Y PRESUPUESTOS
# =============================================================================

class TestConsultarTarifario:
    async def test_filter_uses_tratamiento_detalle(self, manager, mock_appsheet):
        mock_appsheet.find.return_value = [{"Tratamiento Detalle": "Alineadores", "Precio": 100000}]
        result = await manager._tool_consultar_tarifario({"tratamiento": "Alineadores"})
        assert result["status"] == "ok"

        selector = mock_appsheet.find.call_args[1].get("selector", "")

        # Debe usar "Tratamiento Detalle", NO "Tratamiento"
        assert "Tratamiento Detalle" in selector
        assert 'Filter(BBDD TARIFARIO,' in selector

    async def test_not_found(self, manager, mock_appsheet):
        result = await manager._tool_consultar_tarifario({"tratamiento": "NoExiste"})
        assert result["status"] == "not_found"


class TestConsultarPresupuesto:
    async def test_filter_uses_id_paciente(self, manager, mock_appsheet):
        await manager._tool_consultar_presupuesto({"paciente_id": "ANT-15"})

        selector = mock_appsheet.find.call_args[1].get("selector", "")
        assert "ID Paciente" in selector
        assert 'Filter(BBDD PRESUPUESTOS,' in selector


# =============================================================================
# 4. PAGOS
# =============================================================================

class TestBuscarPago:
    async def test_filter_uses_correct_fields(self, manager, mock_appsheet):
        await manager._tool_buscar_pago({
            "paciente_id": "ANT-15",
            "fecha": "03/03/2026",
            "monto": "20000",
            "metodo_pago": "Transferencia",
        })

        selector = mock_appsheet.find.call_args[1].get("selector", "")

        assert "ID PACIENTE" in selector
        assert "Fecha del Pago" in selector
        assert "Monto Pagado" in selector
        assert "Metodo de Pago" in selector
        assert 'Filter(BBDD PAGOS,' in selector

    async def test_detects_duplicado(self, manager, mock_appsheet):
        mock_appsheet.find.return_value = [{"ID Pago": "PAG-1"}]
        result = await manager._tool_buscar_pago({
            "paciente_id": "ANT-15",
            "fecha": "03/03/2026",
            "monto": "20000",
        })
        assert result["duplicado"] is True

    async def test_minimal_filter_only_paciente(self, manager, mock_appsheet):
        await manager._tool_buscar_pago({"paciente_id": "ANT-15"})
        selector = mock_appsheet.find.call_args[1].get("selector", "")
        # Solo filtro por ID PACIENTE, sin AND()
        assert "AND(" not in selector
        assert 'ID PACIENTE' in selector


class TestRegistrarPago:
    async def test_correct_appsheet_fields(self, manager, mock_appsheet):
        result = await manager._tool_registrar_pago({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Antúnez, Florencia",
            "tratamiento": "Odontologia primera vez",
            "fecha": "03/03/2026",
            "monto": 20000,
            "metodo_pago": "Transferencia",
            "tipo_pago": "Seña",
            "moneda": "PESOS",
        })
        assert result["status"] == "created"

        row = mock_appsheet.add.call_args[0][1][0]
        table = mock_appsheet.add.call_args[0][0]

        assert table == "BBDD PAGOS"
        assert row["ID PACIENTE"] == "ANT-15"
        assert row["Paciente"] == "Antúnez, Florencia"
        assert row["Tratamiento"] == "Odontologia primera vez"
        assert row["Fecha del Pago"] == "03/03/2026"
        assert row["Monto Pagado"] == 20000
        assert row["Moneda"] == "PESOS"
        assert row["Metodo de Pago"] == "Transferencia"
        assert row["Tipo de Pago"] == "Seña"
        assert row["Estado del Pago"] == "Confirmado"
        assert row["CUENTA"] == "CYNTHIA"  # Siempre CYNTHIA
        # NO debe tener campos viejos
        assert "Fecha" not in row or row.get("Fecha") is None
        assert "ID Paciente" not in row  # Es "ID PACIENTE" (mayúsculas)
        assert "Monto" not in row or "Monto Pagado" in row

    async def test_moneda_default_pesos(self, manager, mock_appsheet):
        await manager._tool_registrar_pago({
            "paciente_id": "ANT-15",
            "paciente_nombre": "Test",
            "tratamiento": "Test",
            "fecha": "01/01/2026",
            "monto": 5000,
            "metodo_pago": "Efectivo",
            "tipo_pago": "Arancel",
        })
        row = mock_appsheet.add.call_args[0][1][0]
        assert row["Moneda"] == "PESOS"


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
            "Paciente": "García, Juan",
            "ID Paciente": "ANT-15",
            "DNI / Pasaporte": "40123456",
            "email": "juan@test.com",
            "Estado del Paciente": "Activo",
            "Tratamiento": "Alineadores",
            "CONSGEN FIRMADO": "SI",
            "SALDO PEND": "50000",
            "Proximo Turno": "10/03/2026",
        }
        result = _safe_patient_summary(paciente)
        assert "nombre: García, Juan" in result
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
            "Nombre": "Campo viejo",        # Viejo — debería ser "Paciente"
            "_RowNumber": 5,                  # Viejo — debería ser "ID Paciente"
        }
        result = _safe_patient_summary(paciente)
        # No debe extraer datos de los campos viejos
        assert "Campo viejo" not in result
