# AppSheet Tables — Referencia Rápida
# Generado: 2026-03-06
# Fuente: api_calls_map.md + test API real

## Configuración

- **App ID:** `cfc7574f-e4ec-4cf4-8a63-f04d84d347d4`
- **Endpoint:** `https://api.appsheet.com/api/v2/apps/{APP_ID}/tables/{TABLA}/Action`
- **Properties:** `{}` (NUNCA usar Locale)
- **Rate limit:** ~45s entre requests
- **Fechas en API:** `MM/DD/YYYY` (ej: `03/06/2026`)
- **200 con body vacío** = rate limited o tabla inexistente

---

## Tablas Verificadas (test 2026-03-06)

| Tabla (nombre exacto en API) | Registros | Key primaria | Columnas clave |
|---|---|---|---|
| `BBDD PACIENTES` | 1,899 | `ID Paciente` | Paciente, Telefono (Whatsapp), Estado del Paciente, Fecha Nacimiento, SALDO PEND, CONSGEN FIRMADO |
| `BBDD SESIONES` | 6,395 | `ID Sesion` | ID PACIENTE, Paciente, Tratamiento, Fecha de Sesion, Hora de Sesion, Estado de Sesion, Profesional, Duracion, Observaciones |
| `BBDD PAGOS` | 6,290 | `ID Pago` | ID PACIENTE, Paciente, Tratamiento, Monto, Fecha de Pago, Tipo de Pago, Metodo de Pago, Nro de Operacion |
| `BBDD PRESUPUESTOS` | 319 | `Row ID` + `ID Presupuesto` (compuesto) | ID Paciente, Paciente, Telefono, Tratamiento, Saldo Pendiente |
| `BBDD ALINEADORES` | 206 | `ID ALINEADORES` | ID PACIENTE, PACIENTE, ESTADO TRATAMIENTO, 1P/3P |
| `BBDD TARIFARIO` | 38 | `Tratamiento` | Tratamiento Detalle, Precio Lista, Precio efectivo |
| `BBDD LEADS` | 16 | `ID Lead` | Apellido y Nombre, Telefono (Whatsapp), email, Estado del Lead (Temp), Motivo Interes, Fuente Captacion |
| `LISTA O \| HORARIOS DE ATENCION` | 7 | `Row ID` | DIA, HORA INICIO, HORA CIERRE |

---

## Notas Importantes

1. **NO existe tabla "BBDD TURNOS"** — Los turnos se manejan en `BBDD SESIONES`
2. **BBDD PACIENTES Edit**: NO funciona con keys legacy "ANT-xxx", solo UUID
3. **BBDD PRESUPUESTOS**: Key compuesto = `Row ID` + `ID Presupuesto`
4. **Teléfonos**: CONTAINS con últimos 10 dígitos (robustez contra variantes +54, 549, 011)
5. **Estado de Sesion**: initial value = `"Planificada"` (P mayúscula, resto minúscula)
6. **Campo `Paciente`**: Es required en BBDD SESIONES, NO se auto-pobla — Sofía debe enviarlo
7. **Fuente Captacion** (BBDD LEADS): Valores válidos: Instagram, Google Maps, Organico, Referido (Boca en Boca), 3P Alineadores

---

## Tablas Referenciadas en System Prompt pero NO testeadas vía API

| Tabla | Uso | Notas |
|---|---|---|
| `BBDD FACTURAS` | Solo lectura para Sofía — NO crear registros directamente | Pipeline de facturación separado |
| `M1 Turnos` | Vista read-only — NUNCA usar para acciones | Solo para visualización |

---

## Mapeo Tool → Tabla

| Tool de Claude | Tabla AppSheet |
|---|---|
| `buscar_paciente` | `BBDD PACIENTES` (Find) |
| `buscar_lead` | `BBDD LEADS` (Find) |
| `crear_lead` | `BBDD LEADS` (Add) |
| `crear_paciente` | `BBDD PACIENTES` (Add) |
| `consultar_horarios` | `LISTA O \| HORARIOS DE ATENCION` (Find) |
| `buscar_disponibilidad` | `BBDD SESIONES` (Find) |
| `agendar_turno` | `BBDD SESIONES` (Add) |
| `buscar_turno_paciente` | `BBDD SESIONES` (Find) |
| `modificar_turno` | `BBDD SESIONES` (Edit) |
| `cancelar_turno` | `BBDD SESIONES` (Edit) |
| `consultar_tarifario` | `BBDD TARIFARIO` (Find) |
| `consultar_presupuesto` | `BBDD PRESUPUESTOS` (Find) |
| `buscar_pago` | `BBDD PAGOS` (Find) |
| `registrar_pago` | `BBDD PAGOS` (Add) |
| `crear_tarea_pendiente` | Google Sheets (no AppSheet) |
