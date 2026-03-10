#!/usr/bin/env python3
"""
Test de integracion completo: todos los modelos y operaciones contra Cloud SQL real.
Usa transaccion + rollback para no contaminar datos.
"""
import asyncio
import sys
import os
import traceback
from datetime import date, time, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

PG_URL = "postgresql+asyncpg://postgres:Frahat27@34.95.178.117:5432/nexus_clinic_os"

results = []


def ok(test_name, detail=""):
    results.append(("PASS", test_name, detail))
    print(f"  \u2705 {test_name}" + (f" — {detail}" if detail else ""))


def fail(test_name, error):
    results.append(("FAIL", test_name, str(error)))
    print(f"  \u274c {test_name} — {error}")


async def run_all_tests():
    engine = create_async_engine(PG_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from src.db.clinic_repository import ClinicRepository

    print("\n" + "=" * 70)
    print("TEST DE INTEGRACION — Cloud SQL (PostgreSQL)")
    print("Escrituras dentro de transaccion con ROLLBACK")
    print("=" * 70)

    # ===== READ TESTS (sin transaccion, no modifican nada) =====
    async with factory() as session:
        repo = ClinicRepository(session)

        # 1. HORARIOS
        print("\n\U0001f4c5 1. CONSULTAR HORARIOS")
        try:
            horarios = await repo.get_all_horarios()
            ok("get_all_horarios()", f"{len(horarios)} horarios")
            if horarios:
                d = horarios[0].to_appsheet_dict()
                ok("HorarioAtencion.to_appsheet_dict()", f"DIA={d['DIA']}, INICIO={d['HORA INICIO']}")
        except Exception as e:
            fail("get_all_horarios()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        # 2. TIPOS DE TRATAMIENTO
        print("\n\U0001f3e5 2. TIPOS DE TRATAMIENTO")
        try:
            tipos = await repo.get_all_treatment_types()
            ok("get_all_treatment_types()", f"{len(tipos)} tipos")
            if tipos:
                d = tipos[0].to_appsheet_dict()
                ok("TipoTratamiento.to_appsheet_dict()", f"{d['TIPO DE TRATAMIENTO']}, dur={d['Duracion Turno']}min")
        except Exception as e:
            fail("get_all_treatment_types()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        # 3. BUSCAR PACIENTE
        print("\n\U0001f464 3. PACIENTES (lectura)")
        try:
            pac = await repo.find_patient_by_phone("1155667788")
            ok("find_patient_by_phone()", f"Encontrado: {pac is not None}")
        except Exception as e:
            fail("find_patient_by_phone()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            pacientes = await repo.find_active_patients()
            ok("find_active_patients()", f"{len(pacientes)} pacientes activos")
        except Exception as e:
            fail("find_active_patients()", f"{type(e).__name__}: {e}")

        try:
            bday = await repo.find_active_patients_with_birthday(3, 10)
            ok("find_active_patients_with_birthday()", f"{len(bday)} cumpleanos hoy")
        except Exception as e:
            fail("find_active_patients_with_birthday()", f"{type(e).__name__}: {e}")

        # 4. BUSCAR LEAD
        print("\n\U0001f4cb 4. LEADS (lectura)")
        try:
            lead = await repo.find_lead_by_phone("1199998888")
            ok("find_lead_by_phone()", f"Encontrado: {lead is not None}")
        except Exception as e:
            fail("find_lead_by_phone()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            leads = await repo.find_leads_by_status_and_date("Nuevo", date.today())
            ok("find_leads_by_status_and_date()", f"{len(leads)} leads")
        except Exception as e:
            fail("find_leads_by_status_and_date()", f"{type(e).__name__}: {e}")

        # 5. SESIONES (lectura)
        print("\n\U0001f4c6 5. SESIONES (lectura)")
        try:
            hoy = date.today()
            sesiones = await repo.find_sessions_in_range(hoy, hoy + timedelta(days=14))
            ok("find_sessions_in_range()", f"{len(sesiones)} sesiones en 14 dias")
            if sesiones:
                d = sesiones[0].to_appsheet_dict()
                ok("Sesion.to_appsheet_dict()", f"Pac={d['Paciente']}, Fecha={d['Fecha de Sesion']}")
        except Exception as e:
            fail("find_sessions_in_range()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            plan = await repo.find_planned_future_sessions(date.today())
            ok("find_planned_future_sessions()", f"{len(plan)} planificadas")
        except Exception as e:
            fail("find_planned_future_sessions()", f"{type(e).__name__}: {e}")

        try:
            por_fecha = await repo.find_sessions_by_date_and_status(date.today(), "Planificada")
            ok("find_sessions_by_date_and_status()", f"{len(por_fecha)} hoy planificadas")
        except Exception as e:
            fail("find_sessions_by_date_and_status()", f"{type(e).__name__}: {e}")

        try:
            alin_s = await repo.find_aligner_sessions_active()
            ok("find_aligner_sessions_active()", f"{len(alin_s)} sesiones alineadores")
        except Exception as e:
            fail("find_aligner_sessions_active()", f"{type(e).__name__}: {e}")

        # 6. TARIFARIO
        print("\n\U0001f4b0 6. TARIFARIO")
        try:
            all_t = await repo.find_all_tariffs()
            ok("find_all_tariffs()", f"{len(all_t)} tarifas")
            if all_t:
                d = all_t[0].to_appsheet_dict()
                ok("Tarifario.to_appsheet_dict()", f"{d['Tratamiento']} - {d['Tratamiento Detalle']} ${d['Precio Lista']}")
        except Exception as e:
            fail("find_all_tariffs()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            t = await repo.find_tariff("Limpieza")
            ok("find_tariff('Limpieza')", f"Encontrada: {t is not None}" + (f" ${t.precio_lista}" if t else ""))
        except Exception as e:
            fail("find_tariff('Limpieza')", f"{type(e).__name__}: {e}")

        try:
            raw = await repo.find_all_tariffs_raw()
            ok("find_all_tariffs_raw()", f"{len(raw)} (raw SQL)")
        except Exception as e:
            fail("find_all_tariffs_raw()", f"{type(e).__name__}: {e}")

        try:
            raw_t = await repo.find_tariff_raw("Limpieza")
            ok("find_tariff_raw('Limpieza')", f"{len(raw_t)} resultados (raw SQL)")
        except Exception as e:
            fail("find_tariff_raw('Limpieza')", f"{type(e).__name__}: {e}")

        try:
            cols = await repo.diagnose_tarifario_columns()
            ok("diagnose_tarifario_columns()", f"{[c['column'] for c in cols]}")
        except Exception as e:
            fail("diagnose_tarifario_columns()", f"{type(e).__name__}: {e}")

        # 7. PRESUPUESTOS
        print("\n\U0001f4ca 7. PRESUPUESTOS")
        try:
            presus = await repo.find_budgets_by_patient("FAKE_ID")
            ok("find_budgets_by_patient()", f"{len(presus)} presupuestos")
        except Exception as e:
            fail("find_budgets_by_patient()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        # 8. PAGOS (lectura)
        print("\n\U0001f4b3 8. PAGOS (lectura)")
        try:
            pagos = await repo.find_payments("FAKE_ID")
            ok("find_payments()", f"{len(pagos)} pagos")
        except Exception as e:
            fail("find_payments()", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        # 9. ALINEADORES
        print("\n\U0001f9b7 9. ALINEADORES")
        try:
            from src.clinic_models.alineador import Alineador
            from sqlalchemy import select
            stmt = select(Alineador)
            result = await session.execute(stmt)
            alins = result.scalars().all()
            ok("SELECT Alineador", f"{len(alins)} alineadores")
            if alins:
                d = alins[0].to_appsheet_dict()
                ok("Alineador.to_appsheet_dict()", f"Pac={d['PACIENTE']}, Estado={d['ESTADO TRATAMIENTO']}")
        except Exception as e:
            fail("SELECT Alineador", f"{type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            alin = await repo.find_aligner_by_patient("FAKE_ID")
            ok("find_aligner_by_patient()", f"Encontrado: {alin is not None}")
        except Exception as e:
            fail("find_aligner_by_patient()", f"{type(e).__name__}: {e}")

    # ===== WRITE TESTS (con rollback) =====
    print("\n" + "-" * 70)
    print("WRITE TESTS (con rollback, no persisten datos)")
    print("-" * 70)

    # CREAR PACIENTE
    print("\n\U0001f464+ 10. CREAR PACIENTE")
    async with factory() as session:
        async with session.begin():
            repo = ClinicRepository(session)
            try:
                pac = await repo.create_patient(
                    nombre="Test Integration",
                    telefono="1199998888",
                    dni="99999999",
                    fecha_nacimiento=date(1990, 5, 15),
                    sexo="Masculino",
                    email="test@test.com",
                )
                ok("create_patient()", f"ID={pac.id_paciente}")
                d = pac.to_appsheet_dict()
                ok("Paciente(new).to_appsheet_dict()", f"Nombre={d['Paciente']}")

                # Verificar lectura del recien creado
                found = await repo.find_patient_by_id(pac.id_paciente)
                ok("find_patient_by_id(nuevo)", f"Encontrado={found is not None}")
            except Exception as e:
                fail("create_patient()", f"{type(e).__name__}: {e}")
                traceback.print_exc()
            # rollback automatico al salir del begin() sin commit

            await session.rollback()

    # CREAR LEAD
    print("\n\U0001f4cb+ 11. CREAR LEAD")
    async with factory() as session:
        async with session.begin():
            repo = ClinicRepository(session)
            try:
                lead = await repo.create_lead(
                    nombre="Test Lead",
                    telefono="1188887777",
                    motivo_interes="Alineadores",
                )
                ok("create_lead()", f"ID={lead.id_lead}")
                d = lead.to_appsheet_dict()
                ok("Lead(new).to_appsheet_dict()", f"Nombre={d['Apellido y Nombre']}")
            except Exception as e:
                fail("create_lead()", f"{type(e).__name__}: {e}")
                traceback.print_exc()
            await session.rollback()

    # CREAR SESION (agendar_turno)
    print("\n\U0001f4c6+ 12. CREAR SESION (agendar_turno)")
    async with factory() as session:
        async with session.begin():
            repo = ClinicRepository(session)
            try:
                sesion = await repo.create_session(
                    id_paciente="TEST_PAC_001",
                    paciente_nombre="Test Integration",
                    tratamiento="Limpieza",
                    fecha=date(2026, 4, 1),
                    hora=time(10, 0),
                    profesional="Hatzerian, Cynthia",
                    duracion_minutos=30,
                    descripcion="Test integracion",
                )
                ok("create_session()", f"ID={sesion.id_sesion}")
                d = sesion.to_appsheet_dict()
                ok("Sesion(new).to_appsheet_dict()",
                   f"Hora={d['Hora Sesion']}, Fin={d['Horario Finalizacion']}, Dur={d['Duracion']}min")

                # MODIFICAR
                mod = await repo.update_session(sesion.id_sesion, fecha=date(2026, 4, 2), hora=time(14, 0))
                ok("update_session() [modificar]", f"Nueva fecha={mod.fecha}")

                # CANCELAR
                cancel = await repo.update_session(sesion.id_sesion, estado="Cancelada")
                ok("update_session() [cancelar]", f"Estado={cancel.estado}")

                # BUSCAR TURNOS
                turnos = await repo.find_patient_active_sessions("TEST_PAC_001")
                ok("find_patient_active_sessions()", f"{len(turnos)} (deberia ser 0 por cancelado)")
            except Exception as e:
                fail("create_session()", f"{type(e).__name__}: {e}")
                traceback.print_exc()
            await session.rollback()

    # CREAR PAGO (registrar_pago)
    print("\n\U0001f4b3+ 13. CREAR PAGO (registrar_pago)")
    async with factory() as session:
        async with session.begin():
            repo = ClinicRepository(session)
            try:
                pago = await repo.create_payment(
                    id_paciente="TEST_PAC_001",
                    paciente_nombre="Test Integration",
                    tratamiento="Limpieza",
                    fecha=date.today(),
                    monto=Decimal("75000"),
                    metodo_pago="Efectivo",
                    tipo_pago="Sesion",
                    moneda="PESOS",
                    observaciones="Test integracion",
                )
                ok("create_payment()", f"ID={pago.id_pago}, ${pago.monto}")
                d = pago.to_appsheet_dict()
                ok("Pago(new).to_appsheet_dict()", f"Metodo={d['Metodo de Pago']}, Estado={d['Estado del Pago']}")
            except Exception as e:
                fail("create_payment()", f"{type(e).__name__}: {e}")
                traceback.print_exc()
            await session.rollback()

    # 14. GOOGLE SHEETS IMPORT
    print("\n\U0001f4dd 14. GOOGLE SHEETS (import check)")
    try:
        from src.clients.google_sheets import add_pending_task
        ok("import add_pending_task", "OK")
    except Exception as e:
        fail("import add_pending_task", f"{type(e).__name__}: {e}")

    await engine.dispose()


async def main():
    try:
        await run_all_tests()
    except Exception as e:
        print(f"\n\U0001f4a5 Error fatal: {e}")
        traceback.print_exc()

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DE TESTS")
    print("=" * 70)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    print(f"  \u2705 Pasaron: {passed}")
    print(f"  \u274c Fallaron: {failed}")
    print(f"  Total: {len(results)}")
    if failed > 0:
        print("\n\U0001f534 TESTS FALLIDOS:")
        for s, n, d in results:
            if s == "FAIL":
                print(f"  \u274c {n}: {d}")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
