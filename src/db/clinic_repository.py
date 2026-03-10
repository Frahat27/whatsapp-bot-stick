"""
Clinic Repository — reemplazo directo de AppSheetClient.

Cada metodo mapea 1:1 con las operaciones que los tool handlers
y el reminder service necesitan. Usa Cloud SQL via SQLAlchemy async.

Velocidad: ~5ms por query (vs ~45s con AppSheet API).
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import and_, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clinic_models.alineador import Alineador
from src.clinic_models.horario_atencion import HorarioAtencion
from src.clinic_models.lead import Lead
from src.clinic_models.paciente import Paciente
from src.clinic_models.pago import Pago
from src.clinic_models.presupuesto import Presupuesto
from src.clinic_models.sesion import Sesion
from src.clinic_models.tarifario import Tarifario
from src.clinic_models.tipo_tratamiento import TipoTratamiento


def _new_id() -> str:
    """Generar UUID compatible con formato AppSheet."""
    return uuid.uuid4().hex[:22]  # ~22 chars como los IDs de AppSheet


class ClinicRepository:
    """
    Repositorio tipado para datos clinicos en Cloud SQL.
    Reemplaza todas las llamadas a AppSheetClient.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # PACIENTES
    # =========================================================================

    async def find_patient_by_phone(self, phone_10: str) -> Optional[Paciente]:
        """
        Buscar paciente por telefono con matching flexible.

        Debido a formatos legacy de AppSheet (+54, 549, 15, 11, etc.),
        probamos multiples variantes:
          1. Ultimos 10 digitos tal cual
          2. 11 + ultimos 8 digitos (formato celular AMBA)
          3. 15 + ultimos 8 digitos (formato viejo celular)
        """
        # Variante 1: los 10 digitos originales
        stmt = select(Paciente).where(Paciente.telefono.contains(phone_10))
        result = await self.session.execute(stmt)
        patient = result.scalar_one_or_none()
        if patient:
            return patient

        # Variantes alternativas con los ultimos 8 digitos
        last_8 = phone_10[-8:]
        for prefix in ("11", "15"):
            variant = f"{prefix}{last_8}"
            if variant == phone_10:
                continue  # ya se probo arriba
            stmt = select(Paciente).where(Paciente.telefono.contains(variant))
            result = await self.session.execute(stmt)
            patient = result.scalar_one_or_none()
            if patient:
                return patient

        return None

    async def find_patient_by_id(self, patient_id: str) -> Optional[Paciente]:
        """Buscar paciente por ID primario."""
        return await self.session.get(Paciente, patient_id)

    async def create_patient(
        self,
        nombre: str,
        telefono: str,
        dni: str = "COMPLETAR",
        fecha_nacimiento: Optional[date] = None,
        sexo: str = "Otro",
        email: str = "1@1.com",
        referido: Optional[str] = None,
    ) -> Paciente:
        """
        Crear paciente nuevo.
        Equivale a: appsheet.add("BBDD PACIENTES", [row])
        """
        paciente = Paciente(
            id_paciente=_new_id(),
            paciente=nombre,
            telefono=telefono,
            dni=dni,
            fecha_nacimiento=fecha_nacimiento,
            sexo=sexo,
            email=email,
            referido=referido,
            estado="Activo",
            fecha_alta=date.today(),
        )
        self.session.add(paciente)
        await self.session.flush()
        return paciente

    async def find_active_patients(self) -> Sequence[Paciente]:
        """Pacientes con estado Activo (para reminders)."""
        stmt = select(Paciente).where(Paciente.estado == "Activo")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_active_patients_with_birthday(
        self, month: int, day: int
    ) -> Sequence[Paciente]:
        """Pacientes activos cuyo cumpleaños es hoy (para birthday greetings)."""
        stmt = select(Paciente).where(
            and_(
                Paciente.estado == "Activo",
                extract("month", Paciente.fecha_nacimiento) == month,
                extract("day", Paciente.fecha_nacimiento) == day,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # LEADS
    # =========================================================================

    async def find_lead_by_phone(self, phone_10: str) -> Optional[Lead]:
        """
        Buscar lead por telefono con matching flexible.

        Misma logica que find_patient_by_phone: prueba variantes
        con ultimos 10, 11+ultimos 8, y 15+ultimos 8.
        """
        # Variante 1: los 10 digitos originales
        stmt = select(Lead).where(Lead.telefono.contains(phone_10))
        result = await self.session.execute(stmt)
        lead = result.scalar_one_or_none()
        if lead:
            return lead

        # Variantes alternativas con los ultimos 8 digitos
        last_8 = phone_10[-8:]
        for prefix in ("11", "15"):
            variant = f"{prefix}{last_8}"
            if variant == phone_10:
                continue
            stmt = select(Lead).where(Lead.telefono.contains(variant))
            result = await self.session.execute(stmt)
            lead = result.scalar_one_or_none()
            if lead:
                return lead

        return None

    async def create_lead(
        self,
        nombre: str,
        telefono: str,
        motivo_interes: str = "",
        notas: str = "Primer contacto via WhatsApp bot",
    ) -> Lead:
        """
        Crear lead nuevo.
        Equivale a: appsheet.add("BBDD LEADS", [row])
        """
        lead = Lead(
            id_lead=_new_id(),
            nombre=nombre,
            telefono=telefono,
            fecha_creacion=date.today(),
            estado="Nuevo",
            motivo_interes=motivo_interes,
            notas=notas,
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def update_lead_status(self, lead_id: str, new_status: str) -> Optional[Lead]:
        """Actualizar estado de un lead (para reminders)."""
        lead = await self.session.get(Lead, lead_id)
        if lead:
            lead.estado = new_status
            await self.session.flush()
        return lead

    async def find_leads_by_status_and_date(
        self, status: str, creation_date: date
    ) -> Sequence[Lead]:
        """Leads con estado X creados en fecha Y (para reminders)."""
        stmt = select(Lead).where(
            and_(Lead.estado == status, Lead.fecha_creacion == creation_date)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # SESIONES / TURNOS
    # =========================================================================

    async def find_sessions_in_range(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        exclude_cancelled: bool = True,
    ) -> Sequence[Sesion]:
        """
        Sesiones en un rango de fechas (para buscar_disponibilidad).
        Equivale a: appsheet.find("BBDD SESIONES", Filter(AND(...)))
        """
        conditions = [
            Sesion.fecha >= fecha_desde,
            Sesion.fecha <= fecha_hasta,
        ]
        if exclude_cancelled:
            conditions.append(Sesion.estado != "Cancelada")
        stmt = select(Sesion).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_patient_active_sessions(
        self, patient_id: str
    ) -> Sequence[Sesion]:
        """
        Turnos activos de un paciente (Planificada o Confirmada).
        Equivale a: buscar_turno_paciente tool
        """
        stmt = select(Sesion).where(
            and_(
                Sesion.id_paciente == patient_id,
                or_(
                    Sesion.estado == "Planificada",
                    Sesion.estado == "Confirmada",
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_sessions_by_date_and_status(
        self, fecha: date, estado: str
    ) -> Sequence[Sesion]:
        """Sesiones en una fecha con un estado (para reminders)."""
        stmt = select(Sesion).where(
            and_(Sesion.fecha == fecha, Sesion.estado == estado)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_planned_future_sessions(
        self, from_date: date
    ) -> Sequence[Sesion]:
        """Sesiones planificadas a futuro (para confirmaciones)."""
        stmt = select(Sesion).where(
            and_(Sesion.fecha >= from_date, Sesion.estado == "Planificada")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_aligner_sessions_active(self) -> Sequence[Sesion]:
        """Sesiones de alineadores activas (para reminders)."""
        stmt = select(Sesion).where(
            and_(
                Sesion.tratamiento == "Alineadores",
                or_(
                    Sesion.estado == "Planificada",
                    Sesion.estado == "Confirmada",
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_aligner_sessions_realized(
        self, patient_id: str
    ) -> Sequence[Sesion]:
        """Sesiones de alineadores realizadas de un paciente."""
        stmt = select(Sesion).where(
            and_(
                Sesion.id_paciente == patient_id,
                Sesion.tratamiento == "Alineadores",
                Sesion.estado == "Realizada",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_session(
        self,
        id_paciente: str,
        paciente_nombre: str,
        tratamiento: str,
        fecha: date,
        hora: time,
        profesional: str,
        duracion_minutos: int = 30,
        descripcion: str = "",
    ) -> Sesion:
        """
        Crear un turno/sesion nuevo.
        Equivale a: appsheet.add("BBDD SESIONES", [row])
        """
        from datetime import datetime, timedelta
        dur = timedelta(minutes=duracion_minutos)
        hora_fin = (datetime.combine(fecha, hora) + dur).time()

        sesion = Sesion(
            id_sesion=_new_id(),
            id_paciente=id_paciente,
            paciente=paciente_nombre,
            tratamiento=tratamiento,
            fecha=fecha,
            hora=hora,
            hora_fin=hora_fin,
            duracion=duracion_minutos,
            profesional=profesional,
            estado="Planificada",
            descripcion=descripcion,
            fecha_creacion=date.today(),
            consultorio="SALA 1",
            sede="Virrey del Pino",
        )
        self.session.add(sesion)
        await self.session.flush()
        return sesion

    async def update_session(
        self, session_id: str, **data
    ) -> Optional[Sesion]:
        """
        Actualizar una sesion (modificar_turno, cancelar_turno).
        Equivale a: appsheet.edit("BBDD SESIONES", [row])
        """
        sesion = await self.session.get(Sesion, session_id)
        if sesion:
            for key, value in data.items():
                if hasattr(sesion, key):
                    setattr(sesion, key, value)
            await self.session.flush()
        return sesion

    # =========================================================================
    # PAGOS
    # =========================================================================

    async def find_payments(
        self,
        patient_id: str,
        fecha: Optional[date] = None,
        monto: Optional[Decimal] = None,
        metodo: Optional[str] = None,
    ) -> Sequence[Pago]:
        """
        Buscar pagos de un paciente con filtros opcionales.
        Equivale a: buscar_pago tool (anti-duplicado)
        """
        conditions = [Pago.id_paciente == patient_id]
        if fecha:
            conditions.append(Pago.fecha == fecha)
        if monto is not None:
            conditions.append(Pago.monto == monto)
        if metodo:
            conditions.append(Pago.metodo == metodo)
        stmt = select(Pago).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_payment(
        self,
        id_paciente: str,
        paciente_nombre: str,
        tratamiento: str,
        fecha: date,
        monto: Decimal,
        metodo_pago: str,
        tipo_pago: str,
        moneda: str = "PESOS",
        observaciones: str = "",
    ) -> Pago:
        """
        Registrar un pago nuevo.
        Equivale a: appsheet.add("BBDD PAGOS", [row])
        """
        pago = Pago(
            id_pago=_new_id(),
            id_paciente=id_paciente,
            paciente=paciente_nombre,
            tratamiento=tratamiento,
            fecha=fecha,
            monto=monto,
            moneda=moneda,
            metodo=metodo_pago,
            tipo=tipo_pago,
            estado="Confirmado",
            cuenta="CYNTHIA",
            observaciones=observaciones,
            consultorio="SALA 1",
            sede="Virrey del Pino",
        )
        self.session.add(pago)
        await self.session.flush()
        return pago

    # =========================================================================
    # PRESUPUESTOS
    # =========================================================================

    async def find_budgets_by_patient(
        self, patient_id: str
    ) -> Sequence[Presupuesto]:
        """
        Presupuestos de un paciente.
        Equivale a: consultar_presupuesto tool
        """
        stmt = select(Presupuesto).where(
            Presupuesto.id_paciente == patient_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # TARIFARIO
    # =========================================================================

    async def find_tariff(self, tratamiento: str) -> Optional[Tarifario]:
        """
        Buscar tarifa por nombre de tratamiento detalle.
        Equivale a: consultar_tarifario tool
        """
        stmt = select(Tarifario).where(
            Tarifario.tratamiento_detalle == tratamiento
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all_tariffs(self) -> Sequence[Tarifario]:
        """Todos los registros del tarifario."""
        stmt = select(Tarifario)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # HORARIOS DE ATENCION
    # =========================================================================

    async def get_all_horarios(self) -> Sequence[HorarioAtencion]:
        """
        Todos los horarios de atencion.
        Equivale a: consultar_horarios tool
        """
        stmt = select(HorarioAtencion)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # TIPOS DE TRATAMIENTO
    # =========================================================================

    async def get_all_treatment_types(self) -> Sequence[TipoTratamiento]:
        """
        Todos los tipos de tratamiento (para duracion en disponibilidad).
        Equivale a: appsheet.find("LISTA A I tipo tratamientos")
        """
        stmt = select(TipoTratamiento)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # =========================================================================
    # ALINEADORES
    # =========================================================================

    async def find_aligner_by_patient(
        self, patient_id: str
    ) -> Optional[Alineador]:
        """Buscar tratamiento de alineadores de un paciente."""
        stmt = select(Alineador).where(
            Alineador.id_paciente == patient_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
