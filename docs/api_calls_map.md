# Mapa de Llamadas API — Recetario para n8n
# v3.0 — Validación completa con Franco (sesión 03/03/2026)

Cada operación que Sofía necesita hacer, con tabla, acción, payload y campos exactos.
Validado ✅ = revisado con Franco contra screenshots reales de AppSheet.

---

## CONFIGURACIÓN BASE

```
App ID: cfc7574f-e4ec-4cf4-8a63-f04d84d347d4
Endpoint: https://api.appsheet.com/api/v2/apps/cfc7574f-e4ec-4cf4-8a63-f04d84d347d4/tables/{TABLA}/Action
Headers:
  ApplicationAccessKey: [API_KEY]
  Content-Type: application/json
```

**Reglas críticas:**
- NO usar `"Locale"` → causa respuestas vacías
- `"Properties": {}` → funciona perfecto (sin Locale)
- Rate limit: ~45 segundos entre requests
- `200 con body vacío` = rate limited o tabla no encontrada
- **Formato de fechas en API: `MM/DD/YYYY`** (ej: `06/30/2026`, `03/03/2026`). ⚠️ En el front de AppSheet se muestra DD/M/YY pero la API requiere MM/DD/YYYY.
- **Teléfonos:** Siempre con código país, sin espacios (ej: +5491112345678)

**Acciones disponibles:** Find, Add, Edit, Delete

**✅ TEST API v2 REALIZADO (03/03/2026):**
Fórmulas e initial values SÍ funcionan vía API v2. Resultados:
- ✅ `ID Sesion` → se auto-genera
- ✅ `Motivo Sesion` → fórmula = [Tratamiento] funciona
- ✅ `Estado de Sesion` → initial value = `"Planificada"` (con P mayúscula, resto minúscula — VERIFICAR si filtros deben matchear este formato)
- ✅ `Duracion` → se auto-calcula según tratamiento
- ✅ `Fecha Creacion` → se auto-genera con fecha actual
- ✅ `Telefono`, `Email` → se auto-poblan desde relación BBDD PACIENTES
- ❌ `Paciente` (campo Name) → NO se auto-pobla, es required. Sofía DEBE enviarlo siempre.
- ⚠️ Fecha de Sesion debe ser `MM/DD/YYYY` (DD/M/YY da error 400)

---

## ÍNDICE POR FLUJO DEL SYSTEM PROMPT

| Flujo | Operaciones API | Tablas involucradas |
|---|---|---|
| 3A Identificar contacto | #1, #1B, #2, #3 | PACIENTES, LEADS |
| 3A.1 Lead → Paciente | #4, #5, #6, #7, #8, #9, #10 | TARIFARIO, PACIENTES, SESIONES, PAGOS, LEADS |
| 3B Gestionar turnos | #11, #12, #13, #14, #15, #16 | HORARIOS, SESIONES |
| 3C Precios | #4, #17 | TARIFARIO, PRESUPUESTOS |
| 3D Pagos | #7, #8, #9, #17, #18 | PAGOS, PRESUPUESTOS, PACIENTES |
| 3D.1 Facturación | GS-1 | Google Sheets (Tareas Pendientes) |
| 3D.2 Envío facturas | GS-2, GS-3, #1 | Google Sheets (F2-Facturas), PACIENTES |
| 3E Recordatorios | #13, #14, #16, #20 | SESIONES, PACIENTES |
| 3F Alineadores | #21, #22, #25 | ALINEADORES, SESIONES |
| 3H Seguimiento leads | #24 | LEADS |
| 3I Escalar | GS-1, Chatwoot | Google Sheets + Chatwoot |

---

## OPERACIONES DETALLADAS

---

### #1 — Buscar paciente por teléfono ✅
**Flujo:** 3A (Identificar contacto)
**Cuándo:** Mensaje nuevo SIN historial en Chatwoot (primer contacto)
**Tabla:** `BBDD PACIENTES`
**Prioridad real:** Chatwoot resuelve ~70% de identificaciones con historial de chat. Esta operación solo se ejecuta cuando Chatwoot no tiene historial previo.

**Normalización de teléfono:** Usar los últimos 10 dígitos del número entrante. Los pacientes pueden tener guardado el teléfono como +54..., 549..., 011..., etc.

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PACIENTES, CONTAINS([Telefono (Whatsapp)], \"1112345678\"))"
  },
  "Rows": []
}
```

**⚠️ NOTA:** `CONTAINS` con los últimos 10 dígitos es más robusto que igualdad exacta.

**Respuesta esperada (1 resultado):**
```json
[
  {
    "ID Paciente": "ANT-15",
    "Paciente": "García, Juan",
    "Telefono (Whatsapp)": "+5491112345678",
    "Estado del Paciente": "ACTIVO",
    "SALDO PEND": 45000,
    "Proximo Turno": "2026-03-10"
  }
]
```

**Si devuelve múltiples resultados (mismo teléfono):**
Caso real: una madre con múltiples hijos como pacientes. Sofía NO lista los nombres. Saluda normalmente ("Hola 😊, cómo estás?") y espera a que el contexto del mensaje revele de qué paciente se trata. Después filtra por nombre:

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PACIENTES, AND(CONTAINS([Telefono (Whatsapp)], \"1112345678\"), CONTAINS([Paciente], \"García\")))"
  },
  "Rows": []
}
```

**Si no existe:** Respuesta vacía `[]` → ir a #2

---

### #1B — Actualizar teléfono de paciente ✅
**Flujo:** 3A (Identificar contacto — caso especial)
**Cuándo:** Paciente escribe desde un número nuevo y se identifica
**Tabla:** `BBDD PACIENTES`

**Paso 1 — Buscar por apellido Y nombre:**
```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PACIENTES, AND(CONTAINS([Paciente], \"García\"), CONTAINS([Paciente], \"Juan\")))"
  },
  "Rows": []
}
```

**Si encuentra 1 resultado:** Actualizar teléfono:
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Paciente": "ANT-15",
      "Telefono (Whatsapp)": "+5491198765432"
    }
  ]
}
```

**Si encuentra 2+ resultados Y tienen DNI = "COMPLETAR":**
- NO actualizar nada
- Registrar en Google Sheet tareas pendientes (GS-1) con Tipo: "Consulta sin respuesta"
- Contexto: "Paciente se comunicó desde nuevo número, múltiples coincidencias por nombre, no se pudo identificar unívocamente"

---

### #2 — Buscar lead por teléfono ✅
**Flujo:** 3A (Identificar contacto)
**Cuándo:** Cuando #1 no encuentra paciente
**Tabla:** `BBDD LEADS`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD LEADS, CONTAINS([Telefono (Whatsapp)], \"1112345678\"))"
  },
  "Rows": []
}
```

**Si no existe:** Respuesta vacía `[]` → ir a #3

---

### #3 — Crear lead nuevo ✅
**Flujo:** 3A (Identificar contacto)
**Cuándo:** Cuando #1 y #2 no encuentran al contacto
**Tabla:** `BBDD LEADS`

```json
{
  "Action": "Add",
  "Properties": {},
  "Rows": [
    {
      "Apellido y Nombre": "García, Juan",
      "Telefono (Whatsapp)": "+5491112345678",
      "Fecha Creacion": "03/03/2026",
      "Estado del Lead (Temp)": "Nuevo",
      "Motivo Interes": "Consulta por alineadores",
      "Notas y Seguimientos": "Primer contacto vía WhatsApp bot"
    }
  ]
}
```

**⚠️ NOTA:** NO se incluye `Fuente Captacion` automáticamente. "WhatsApp" no es un valor válido de LISTA B.
Sofía debe preguntar al paciente cómo conoció la clínica. Valores válidos de LISTA B:
- Instagram
- Google Maps
- Organico
- Referido (Boca en Boca)
- 3P Alineadores

Si el paciente no lo aclara, se puede dejar vacío y completar después, o usar "Organico" como default.

**Nota:** El ID Lead se genera automáticamente por AppSheet.

---

### #4 — Consultar precio en tarifario ✅
**Flujo:** 3A.1 (Lead → Paciente), 3C (Precios)
**Cuándo:** Cuando necesita informar valor de consulta, seña, o cualquier tratamiento
**Tabla:** `BBDD TARIFARIO`

**⚠️ El campo de búsqueda es `Tratamiento Detalle` (NO `Tratamiento`, que es el grupo/categoría).**

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD TARIFARIO, [Tratamiento Detalle] = \"Odontologia primera vez\")"
  },
  "Rows": []
}
```

**Respuesta esperada:**
```json
[
  {
    "Tratamiento Detalle": "Odontologia primera vez",
    "Tratamiento": "Alineadores",
    "Precio Lista": 45000,
    "Precio Efectivo": 40500,
    "Moneda": "PESOS"
  }
]
```

**Campos clave:**
- `Tratamiento Detalle` = nombre específico del tratamiento (lo que buscamos)
- `Tratamiento` = grupo/categoría (Alineadores, Blanqueamiento, Ortodoncia, Operatoria, Operatoria Compleja)
- `Precio Lista` = precio normal
- `Precio Efectivo` = precio con 10% dto. efectivo
- `Moneda` = PESOS o USD
- `Seña` = registro aparte en la misma tabla

**Para obtener todo el tarifario:**
```json
{
  "Action": "Find",
  "Properties": {},
  "Rows": []
}
```

---

### #5 — Crear paciente nuevo ✅
**Flujo:** 3A.1 (Lead → Paciente)
**Cuándo:** Después de recopilar datos del lead que quiere agendar
**Tabla:** `BBDD PACIENTES`
**CRÍTICO:** Debe ejecutarse ANTES de crear el turno (#7). BBDD SESIONES requiere que el paciente exista.

```json
{
  "Action": "Add",
  "Properties": {},
  "Rows": [
    {
      "Paciente": "García, Juan",
      "Fecha Nacimiento": "06/15/1990",
      "Sexo": "Masculino",
      "DNI / Pasaporte": "35123456",
      "Telefono (Whatsapp)": "+5491112345678",
      "email": "juan@email.com",
      "Fuente de Captacion": "Instagram"
    }
  ]
}
```

**Campos y reglas:**
| Campo | Formato | Regla |
|---|---|---|
| Paciente | "Apellido, Nombre" | Obligatorio |
| Fecha Nacimiento | MM/DD/YYYY (ej: 06/15/1990) | Obligatorio. ⚠️ Formato API, no front-end |
| Sexo | Masculino / Femenino / Otro | Inferir del nombre, default "Otro" si no hay certeza |
| DNI / Pasaporte | Solo número | Si el paciente no lo da ahora, poner "COMPLETAR" |
| Telefono (Whatsapp) | +549XXXXXXXXXX | Obligatorio |
| email | email@ejemplo.com | Opcional pero recomendado |
| Fuente de Captacion | Valor exacto de LISTA B | Preguntar al paciente |
| Referido | ID del paciente que refirió (ej: "ANT-5") | Solo si Fuente = "Referido (Boca en Boca)" |

**✅ Verificado por test API (03/03/2026):**
| Campo | Auto-poblado | Valor |
|---|---|---|
| Estado del Paciente | ✅ SÍ | "Activo" |
| Fecha de Alta | ✅ SÍ | Fecha actual |
| email | ✅ SÍ (default) | "1@1.com" — Sofía debería enviar el real si lo tiene |
| Sexo | ✅ SÍ (default) | "Otro" |
| DNI / Pasaporte | ✅ SÍ (default) | "COMPLETAR" |
| CONSGEN FIRMADO | ✅ Auto | "" (vacío, no "NO") |

**Nota:** El ID Paciente se genera automáticamente en formato UUID (ej: `cu44H5ro304PQ5G0KfnG-3`). La respuesta devuelve el registro creado con su ID → **guardar para usar en #7**.

**⚠️ LIMITACIÓN API: Edit de pacientes existentes (keys "ANT" legacy) NO funciona vía API.**
Cuando un paciente quiere actualizar DNI/email/fecha nacimiento → Sofía registra **GS-1** tipo "Datos para actualizar" con la info y un humano lo aplica. Pacientes NUEVOS (keys UUID) sí se pueden editar.

---

### #6 — Crear turno / sesión ✅
**Flujo:** 3A.1 (Lead → Paciente), 3B (Gestionar turnos)
**Cuándo:** Al agendar un turno nuevo
**Tabla:** `BBDD SESIONES`
**CRÍTICO:** El paciente DEBE existir en BBDD PACIENTES antes de ejecutar esto.

**Payload completo — testeado y verificado ✅:**
```json
{
  "Action": "Add",
  "Properties": {},
  "Rows": [
    {
      "ID PACIENTE": "ANT-15",
      "Paciente": "García, Juan",
      "Tratamiento": "Odontologia primera vez",
      "Fecha de Sesion": "03/10/2026",
      "Hora Sesion": "15:00",
      "Profesional Asignado": "Hatzerian, Cynthia",
      "Descripcion de la sesion": "Interesado en alineadores. Falta seña"
    }
  ]
}
```

**⚠️ `Paciente` es OBLIGATORIO** — El test API confirmó que NO se auto-pobla (error 400 sin él).
**⚠️ Fecha formato `MM/DD/YYYY`** — DD/M/YY da error 400.

**Campos que se auto-generan (confirmado por test ✅ — NO enviar):**
| Campo | Valor auto-generado |
|---|---|
| ID Sesion | Auto-key única |
| Motivo Sesion | Fórmula = [Tratamiento] |
| Estado de Sesion | Initial value = `"Planificada"` |
| Duracion | Auto-calcula según tratamiento (30min para "Odontologia primera vez" ✅ confirmado) |
| Horario Finalizacion | Auto = Hora + Duracion |
| Fecha Creacion | Auto = fecha actual |
| Telefono (Whatsapp) | Auto desde relación BBDD PACIENTES |
| Email | Auto desde relación BBDD PACIENTES |
| Solapamiento turnos | Auto-calculado |

**Valores de Tratamiento (de LISTA A):**
| Tratamiento | Duración |
|---|---|
| Odontologia primera vez | 30 min |
| Control | 30 min |
| Limpieza | 45 min |
| Urgencia | 30 min |
| Alineadores | 30 min |
| Brackets metalicos | 60 min |
| Brackets zafiro | 60 min |
| Blanqueamiento | 90 min |
| Endodoncia | 60 min |
| Implantes | 60 min |
| Cirugia - Extraccion simple | 30 min |
| Cirugia - Extraccion compleja | 60 min |
| Operatoria Simple | 30 min |
| Operatoria Compleja | 60 min |
| Odontopediatria | 30 min |
| Protesis | 60 min |

**Profesional Asignado (formato: "Apellido, Nombre"):**
| Profesional | Cuándo asignar |
|---|---|
| Hatzerian, Cynthia | Default — L a S (excepto Mi tarde) |
| Miño, Ana | Mi 14:30-20:00 — Odontopediatria, Controles, Limpiezas, Caries |

**⚠️ NO ASIGNAR directamente (escalar a Google Sheet):**
- Fernández, Ignacio (Endodoncia)
- Figueiras, Diego (Implantes)
- Pérez, Daiana (Cirugía)

**Variantes de Descripcion de la sesion:**
- Lead sin seña: `"Interesado en [motivo]. Falta seña"`
- Lead con seña: `"Interesado en [motivo]"`
- Urgencia: `"URGENCIA: [descripción del problema]"`
- Control: `"Control general"` o `"Control por [motivo]"`

---

### #7 — Verificar pago duplicado (ANTI-DUPLICADO) ✅
**Flujo:** 3D (Pagos)
**Cuándo:** SIEMPRE antes de registrar un pago nuevo (#8)
**Tabla:** `BBDD PAGOS`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PAGOS, AND([ID PACIENTE] = \"ANT-15\", [Fecha del Pago] = \"03/03/2026\", [Monto Pagado] = 20000, [Metodo de Pago] = \"Transferencia\"))"
  },
  "Rows": []
}
```

**Si devuelve resultados:** El pago YA existe → NO crear otro. Confirmar al paciente "Ya lo tenemos registrado 😊"
**Si devuelve vacío:** El pago NO existe → Proceder con #8

---

### #8 — Registrar pago (seña o pago regular) ✅
**Flujo:** 3A.1 (Lead → Paciente), 3D (Pagos)
**Cuándo:** Cuando el paciente envía comprobante de pago
**Tabla:** `BBDD PAGOS`
**CRÍTICO:** Antes de crear, ejecutar SIEMPRE #7 (verificación anti-duplicado)

```json
{
  "Action": "Add",
  "Properties": {},
  "Rows": [
    {
      "ID PACIENTE": "ANT-15",
      "Tratamiento": "Odontologia primera vez",
      "Fecha del Pago": "03/03/2026",
      "Monto Pagado": 20000,
      "Moneda": "PESOS",
      "Metodo de Pago": "Transferencia",
      "Estado del Pago": "Confirmado",
      "Tipo de Pago": "Seña",
      "CUENTA": "CYNTHIA"
    }
  ]
}
```

**Campos y valores exactos:**

| Campo | Valores válidos | Notas |
|---|---|---|
| Moneda | `PESOS`, `USD` | Default: PESOS |
| CUENTA | `CYNTHIA` | Siempre CYNTHIA (confirmado por Franco) |
| Metodo de Pago | `Efectivo`, `Transferencia`, `Mercado Pago`, `Tarjeta de Credito`, `Tarjeta de Debito` | De LISTA G (**sin tilde**, verificado) |
| Estado del Pago | `Confirmado`, `Pendiente`, `Rechazado`, `Reembolso` | De LISTA G1 (verificado) |
| Tipo de Pago | `Seña`, `Arancel`, `Cuota`, `Implante`, `Endodoncia`, `Cirugia`, `Tratamiento Protesis`, `Blanqueamiento`, `Tratamiento ortodoncia`, `Tratamiento alineadores` | De LISTA M (CATEGORIA DE PAGOS) |

**✅ Verificado por test API (03/03/2026):**
- `Quiere Factura?` → Acepta "N" pero almacena como "False" (es Boolean). Para "Sí" enviar "True"
- `Observaciones` → vacío por default, enviar string libre
- `Paciente` → **REQUIRED**, NO se auto-pobla desde ID PACIENTE. Enviar "Apellido, Nombre"
- `Tratamiento` → **REQUIRED**, NO se auto-pobla
- `CUENTA` → Auto-poblado "CYNTHIA"
- `Tipo de Paciente` → Auto-lookup desde BBDD PACIENTES

---

### #9 — Quitar "Falta seña" del turno ✅
**Flujo:** 3A.1 (cuando llega la seña)
**Cuándo:** Cuando el paciente confirma el pago de la seña
**Tabla:** `BBDD SESIONES`

```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Sesion": "SES-123",
      "Descripcion de la sesion": "Interesado en alineadores"
    }
  ]
}
```

**⚠️ NOTA:** El campo es `Descripcion de la sesion` (NO "Observaciones"). BBDD PAGOS sí usa "Observaciones", pero BBDD SESIONES usa "Descripcion de la sesion".

---

### #10 — Actualizar estado del lead a "Cerrada Ganada" ✅
**Flujo:** 3A.1 (Lead → Paciente)
**Cuándo:** Cuando un lead se convierte en paciente (después de crear paciente y turno)
**Tabla:** `BBDD LEADS`

```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Lead": "LEAD-42",
      "Estado del Lead (Temp)": "Cerrada Ganada",
      "Notas y Seguimientos": "Convirtió a paciente el 03/03. Turno agendado."
    }
  ]
}
```

**Valores posibles de Estado del Lead (LISTA C):**
Nuevo, Contactado, Cerrada Ganada, Cerrada Perdida, Recontactado, Contactado Frio, Contactado Caliente

---

### #11 — Consultar horarios de atención ✅ TESTEADO
**Flujo:** 3B (Gestionar turnos)
**Cuándo:** Antes de buscar turnos disponibles
**Tabla:** `LISTA O | HORARIOS DE ATENCION`

⚠️ El nombre contiene un pipe `|`. En URL se encodea como `%7C`: `LISTA%20O%20%7C%20HORARIOS%20DE%20ATENCION`

```json
{
  "Action": "Find",
  "Properties": {},
  "Rows": []
}
```

**Respuesta real (testeada 03/03/2026):**
```json
[
  {"DIA": "LUNES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
  {"DIA": "MARTES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
  {"DIA": "MIERCOLES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
  {"DIA": "JUEVES", "HORA INICIO": "08:30:00", "HORA CIERRE": "18:00:00"},
  {"DIA": "VIERNES", "HORA INICIO": "10:00:00", "HORA CIERRE": "18:00:00"},
  {"DIA": "SABADO", "HORA INICIO": "08:30:00", "HORA CIERRE": "13:00:00"},
  {"DIA": "DOMINGO", "HORA INICIO": "", "HORA CIERRE": ""}
]
```

**Campos:** `DIA` (Text), `HORA INICIO` (Time, formato HH:MM:SS), `HORA CIERRE` (Time, formato HH:MM:SS)

**Regla especial miércoles tarde (NO está en la tabla, hardcodear en n8n):**
- 14:30-20:00 → Profesional = `"Miño, Ana"` (Anita)
- Anita atiende: Odontopediatría, Controles, Limpiezas, Caries
- Si turno cae en este horario → informar al paciente: "Tu turno va a ser con la Dra. Ana Miño 😊"

**Cynthia — formas de mencionarla al paciente:** "Dra. Cynthia", "Cyn", "Dra. Cyn"

---

### #12 — Buscar turnos existentes (para ver disponibilidad) ✅
**Flujo:** 3B (Gestionar turnos)
**Cuándo:** Para encontrar slots libres en un rango de fechas
**Tabla:** `BBDD SESIONES`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([Fecha de Sesion] >= \"03/03/2026\", [Fecha de Sesion] <= \"03/24/2026\", [Estado de Sesion] <> \"Cancelada\"))"
  },
  "Rows": []
}
```

**Lógica de cálculo de slots (en n8n):**
1. Trae todos los turnos NO cancelados en las próximas 3 semanas
2. Para cada día, armar timeline con turnos existentes (Hora Sesion + Duracion)
3. **Los slots son DINÁMICOS** — dependen de la duración del turno anterior (NO son fijos cada 30 min)
4. Calcular huecos libres entre turnos existentes, respetando horarios de #11
5. Sofía ofrece 2-3 opciones que se adapten al paciente

**⚠️ SOBRETURNOS:** Solo se cargan manualmente por humanos. Sofía NUNCA crea sobreturnos. Si el campo `Solapamiento turnos` devuelve algo distinto a "✅ Horario disponible", Sofía debe buscar otro slot.

**Formato de fechas en filtros:** `MM/DD/YYYY` (confirmado en test API)

---

### #13 — Buscar turno de un paciente específico ✅
**Flujo:** 3B (Reprogramar/Cancelar), 3E (Recordatorios)
**Cuándo:** Paciente quiere reprogramar, cancelar, o pregunta "¿cuándo es mi turno?"
**Tabla:** `BBDD SESIONES`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([ID PACIENTE] = \"ANT-15\", OR([Estado de Sesion] = \"Planificada\", [Estado de Sesion] = \"Confirmada\")))"
  },
  "Rows": []
}
```

**Respuesta:** Si tiene múltiples turnos futuros, Sofía siempre responde con el **turno más próximo a hoy**.

---

### #14 — Actualizar estado de turno ✅
**Flujo:** 3B, 3E, 3E.1
**Cuándo:** Confirmar, reprogramar o cancelar un turno
**Tabla:** `BBDD SESIONES`

**Confirmar turno:**
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Sesion": "CRTEjtG4-xxx",
      "Estado de Sesion": "Confirmada"
    }
  ]
}
```

**Reprogramar (editar mismo turno — NO crear nuevo):**
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Sesion": "CRTEjtG4-xxx",
      "Fecha de Sesion": "03/15/2026",
      "Hora Sesion": "10:00",
      "Profesional Asignado": "Hatzerian, Cynthia"
    }
  ]
}
```
→ Se **modifica el mismo registro** cambiando Fecha, Hora y Profesional. **El Estado se mantiene en "Planificada"** (no se cambia a Reprogramada).
→ Profesional puede cambiar si la nueva fecha/hora cae miércoles 14:30-20:00 (pasa a "Miño, Ana")

**⚠️ Si el nuevo turno queda con Ana Miño, Sofía debe informar al paciente al ofrecerlo:** "Ese turno sería con la Dra. Ana Miño 😊"

**Cancelar:**
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Sesion": "CRTEjtG4-xxx",
      "Estado de Sesion": "Cancelada"
    }
  ]
}
```
→ Después Sofía pregunta: "¿Querés que busquemos otro día?" o "¿Querés que reprogramemos para otro día?"

**Valores de Estado de Sesion (verificado en base real):**
`Planificada`, `Confirmada`, `Reprogramada`, `Realizada`, `Cancelada`, `No Asistio`
⚠️ LISTA J tiene MAYÚSCULAS pero la base almacena Title Case. Filtros son case-insensitive pero usar Title Case por consistencia.

---

### #15 — Buscar turnos de urgencia (misma semana) ✅
**Flujo:** 3B (Urgencias)
**Cuándo:** Paciente reporta urgencia
**Tabla:** `BBDD SESIONES`
**Diferencia con turno normal:** NO se pregunta disponibilidad al paciente. Se buscan huecos directamente.

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([Fecha de Sesion] >= \"03/03/2026\", [Fecha de Sesion] <= \"03/07/2026\", [Estado de Sesion] <> \"Cancelada\"))"
  },
  "Rows": []
}
```

**Nota:** Fechas = lunes a sábado de la semana actual. Buscar los huecos libres.

**Si hay huecos:** Ofrecer directamente → #6 (Tratamiento = "Urgencia", Descripcion = "URGENCIA: [descripción]")
**Si NO hay huecos:** Escalar → GS-1 (Tipo: "Urgencia", Prioridad: 🔴 Alta)

---

### #15B — Escalar turno de especialista ✅
**Flujo:** 3B (Endodoncia/Implantes/Cirugía)
**Cuándo:** Paciente necesita turno con Nacho, Diego o Dai
**Operación:** Solo GS-1 (Google Sheet) — Sofía NO agenda estos turnos directamente

| Especialidad | Tipo tarea | Profesional |
|---|---|---|
| Endodoncia | Coordinación Endodoncia | Nacho Fernández |
| Implantes | Coordinación Implantes | Diego Figueiras |
| Cirugía | Coordinación Cirugía | Dai Pérez |

Sofía:
1. Informa al paciente sobre el tratamiento normalmente
2. Registra en Google Sheet (GS-1) con Tipo, Profesional y Contexto (qué necesita + disponibilidad del paciente)
3. Informa: "Voy a pasar tu solicitud al equipo para coordinar el turno con el especialista. Te contactamos a la brevedad 😊"

---

### #16 — Buscar turnos para recordatorios diarios ✅
**Flujo:** 3E (Recordatorios)
**Cuándo:** Ejecución diaria automática (cron job en n8n) — **solo el día anterior**
**Tabla:** `BBDD SESIONES` (NO M1 Turnos)

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([Fecha de Sesion] = \"03/04/2026\", [Estado de Sesion] = \"Planificada\"))"
  },
  "Rows": []
}
```

**⚠️ Fecha = mañana** (n8n calcula la fecha de mañana en formato MM/DD/YYYY)

**Mensaje de recordatorio (formato exacto):**
> "Hola [Nombre] 😊 Te escribo para recordarte que mañana **[fecha en formato: miércoles 04 de marzo]** tenés turno a las **[hora en formato: 9:00]** con **[Profesional]**. ¿Confirmás que venís?
>
> Responde con **SI** para confirmar o **NO** para cancelar el turno."

**Respuesta del paciente:**
- "SI" → Tarea #27 (confirmar + consentimiento)
- "NO" → Tarea #28 (cancelar/reprogramar)

---

### #17 — Consultar presupuesto/saldo del paciente ⏳ PENDIENTE VALIDAR
**Flujo:** 3C (Precios), 3D (Pagos/Cobros)
**Cuándo:** Paciente pregunta saldo, o admin solicita cobro
**Tabla:** `BBDD PRESUPUESTOS`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PRESUPUESTOS, [ID Paciente] = \"ANT-15\")"
  },
  "Rows": []
}
```

**Respuesta esperada:**
```json
[
  {
    "ID Presupuesto": "PRES-10",
    "ID Paciente": "ANT-15",
    "Tratamiento": "Alineadores",
    "Monto Total": 1100,
    "Moneda": "USD",
    "ESTADO": "En curso",
    "Monto Pagado": 500,
    "Saldo Pendiente": 600
  }
]
```

**Para informar saldo pendiente:** Usar el campo virtual `Saldo Pendiente` de esta tabla. NO usar BBDD PACIENTES → el campo `SALDO PEND` de PACIENTES es menos confiable. Tanto el monto como el tratamiento se sacan de BBDD PRESUPUESTOS.

---

### #18 — Consultar pagos de un paciente ⏳ PENDIENTE VALIDAR
**Flujo:** 3D (Pagos)
**Cuándo:** Para verificar historial de pagos
**Tabla:** `BBDD PAGOS`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PAGOS, [ID PACIENTE] = \"ANT-15\")"
  },
  "Rows": []
}
```

---

### ~~#19~~ — ELIMINADO ❌
**M1 Turnos es vista calculada (read-only).** No se usa para NINGUNA acción.
Todas las confirmaciones, cancelaciones y reprogramaciones se hacen directo en **BBDD SESIONES** via Op #14.

---

### #20 — Verificar consentimiento firmado ✅
**Flujo:** 3E (Recordatorios — cuando el paciente confirma)
**Cuándo:** Después de que el paciente confirma turno (responde SÍ al recordatorio)
**Tabla:** `BBDD PACIENTES`

**Campo:** `CONSGEN FIRMADO` — campo virtual, valores: `"OK"` (firmado) o `"NO"` (no firmado)

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD PACIENTES, [ID Paciente] = \"ANT-15\")"
  },
  "Rows": []
}
```

**Lógica:**
1. Buscar al paciente y leer el campo `CONSGEN FIRMADO`
2. Si = `"OK"` → No pedir nada más, consentimiento ya firmado
3. Si = `"NO"` → Enviar link de consentimiento (Tally):
   - Calcular edad desde `Fecha Nacimiento`
   - **≥ 18 años:** `https://tally.so/r/dW6dvN?codigo=[ID PACIENTE]`
   - **< 18 años:** `https://tally.so/r/EkXMVo?codigo=[ID PACIENTE]`

**Mensaje al enviar link:**
> "Te paso el link del consentimiento de atención para que lo completes antes del turno: [LINK]"

---

### #21 — Buscar tratamiento de alineadores del paciente ✅
**Flujo:** 3F (Recordatorios de cambio de alineadores)
**Cuándo:** Para verificar si el paciente tiene tratamiento activo
**Tabla:** `BBDD ALINEADORES`

```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD ALINEADORES, AND([ID PACIENTE] = \"ANT-15\", [ESTADO TRATAMIENTO] = \"EN CURSO\"))"
  },
  "Rows": []
}
```

**Campo de relación:** `ID PACIENTE` ✅ confirmado
**Campo de estado:** `ESTADO TRATAMIENTO`

**Valores de ESTADO TRATAMIENTO:**
| Valor | Significado |
|---|---|
| INTERESADO | Lead interesado en alineadores |
| ESCANEADO | Se realizó el escaneo |
| ESTUDIOS | En etapa de estudios/planificación |
| EN ESPERA (No urg) | En espera, no urgente |
| EN ESPERA (Urg) | En espera, urgente |
| **EN CURSO** | **Tratamiento activo** — solo estos reciben recordatorios |
| ABANDONADO | Paciente abandonó el tratamiento |
| FINALIZADO | Tratamiento completado |

**Nota:** Por ahora esta tabla se usa SOLO para verificar estado del tratamiento. Los campos detallados (etapa, nro alineador, etc.) no se consumen aún — se podrían usar más adelante.

---

### #22 — Buscar turnos de alineadores (para calcular recordatorio de cambio) ✅
**Flujo:** 3F (Recordatorios de cambio de alineadores)
**Cuándo:** Cron diario en n8n — para cada paciente con ESTADO TRATAMIENTO = "EN CURSO" (#21)
**Tabla:** `BBDD SESIONES`

**Paso 1 — Buscar último turno REALIZADA:**
```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([ID PACIENTE] = \"ANT-15\", [Tratamiento] = \"Alineadores\", [Estado de Sesion] = \"Realizada\"))"
  },
  "Rows": []
}
```
→ De los resultados, tomar el de `Fecha de Sesion` más reciente

**Paso 2 — Buscar próximo turno PLANIFICADA:**
```json
{
  "Action": "Find",
  "Properties": {
    "Selector": "Filter(BBDD SESIONES, AND([ID PACIENTE] = \"ANT-15\", [Tratamiento] = \"Alineadores\", OR([Estado de Sesion] = \"Planificada\", [Estado de Sesion] = \"Confirmada\")))"
  },
  "Rows": []
}
```

**⚠️ Si NO tiene próximo turno planificado/confirmado:**
- **NO enviar recordatorio de cambio**
- Enviar alerta al admin (WhatsApp a Franco + GS-1):
  - Tipo: "Aviso alineadores sin turno"
  - Contexto: "Paciente [Nombre] (ID: [ID]) tiene tratamiento EN CURSO pero no tiene próximo turno planificado"
- El admin puede responder: "Ese paciente ya finalizó" → Sofía ejecuta Op #25 (cambiar ESTADO TRATAMIENTO a "FINALIZADO")

**Lógica de cálculo del timing del recordatorio (en n8n):**

| Días entre último REALIZADA y próximo PLANIFICADA | Cuándo enviar recordatorio |
|---|---|
| 22 a 26 días (ciclo corto) | A los **12 días** del último turno realizado |
| 27 a 34 días (ciclo estándar ~30 días) | A los **15 días** del último turno realizado |
| Más de 34 días (ciclo largo ~45 días) | Cada **15 días** desde el último turno realizado |

**Mensaje de recordatorio (SIN número de alineador, UN solo mensaje aunque tenga superior+inferior):**
> "Hola [Nombre] 😊 Te recuerdo que ya es momento de cambiar al siguiente juego de alineadores. Recordá usarlos entre 20 y 22 horas por día para que el tratamiento avance bien. ¿Todo bien con las placas?"

**No se registra en ningún lado que se envió el recordatorio.** Es fire-and-forget.

---

### ~~#23~~ — ELIMINADO ❌
**M2 y M3 ya no se usan.** No se consulta número de alineador actual — el recordatorio de cambio se envía sin número específico.

---

### #24 — Actualizar seguimiento de lead ✅
**Flujo:** 3H (Seguimiento de leads)
**Cuándo:** Actualizar notas y estado después de cada intento de seguimiento
**Tabla:** `BBDD LEADS`

**Después del 1er intento sin respuesta (3 días):**
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Lead": "LEAD-42",
      "Estado del Lead (Temp)": "Contactado Frio",
      "Notas y Seguimientos": "1er seguimiento [fecha]: sin respuesta"
    }
  ]
}
```

**Después del 2do intento sin respuesta (7 días) — ÚLTIMO:**
```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID Lead": "LEAD-42",
      "Estado del Lead (Temp)": "Cerrada Perdida",
      "Notas y Seguimientos": "2do seguimiento [fecha]: sin respuesta. Seguimiento cerrado."
    }
  ]
}
```

**⚠️ MÁXIMO 2 intentos de seguimiento.** Después del 2do, cerrar como "Cerrada Perdida".

**Si el lead responde en cualquier momento:**
- Cancelar seguimiento automático
- Pasar a conversación normal con Sofía
- Actualizar estado según corresponda (ej: "Contactado Caliente" si muestra interés)

---

### #25 — Actualizar estado de tratamiento de alineadores ✅
**Flujo:** 3F (Alineadores — por orden del admin)
**Cuándo:** El admin indica que un paciente finalizó o abandonó su tratamiento
**Tabla:** `BBDD ALINEADORES`

```json
{
  "Action": "Edit",
  "Properties": {},
  "Rows": [
    {
      "ID PACIENTE": "ANT-15",
      "ESTADO TRATAMIENTO": "FINALIZADO"
    }
  ]
}
```

**Valores posibles:** `INTERESADO`, `ESCANEADO`, `ESTUDIOS`, `EN ESPERA (No urg)`, `EN ESPERA (Urg)`, `EN CURSO`, `ABANDONADO`, `FINALIZADO`

**⚠️ Sofía solo ejecuta esta operación por instrucción del admin.** Nunca cambia el estado por cuenta propia.

---

## OPERACIONES CON GOOGLE SHEETS (no AppSheet)

Estas operaciones usan la API de Google Sheets, no AppSheet. Se configuran en n8n con el nodo "Google Sheets".
Service account: Franco.json (ya existe).

### GS-1 — Escribir tarea pendiente ✅
**Sheet:** TAREAS PENDIENTES WHATSAPP
**URL:** https://docs.google.com/spreadsheets/d/1Ql5Li8PdpZGg7obxmEjoyH1h-rmjQw0F_WOnwn34GRU
**Operación:** Append Row

| Columna | Valor |
|---|---|
| Fecha Creación | `{{$now}}` (formato: YYYY-MM-DD HH:mm) |
| Tipo | Variable (ver tipos abajo) |
| Prioridad | 🟡 Normal / 🔴 Alta |
| Paciente | Nombre del paciente |
| Teléfono | Teléfono del paciente |
| ID Paciente | ID de AppSheet (si existe) |
| Profesional | Especialista (si aplica) |
| Contexto | Descripción detallada |
| Estado | "Pendiente" |

**Tipos válidos:**
- Coordinación Endodoncia (Profesional: Nacho Fernández)
- Coordinación Implantes (Profesional: Diego Figueiras)
- Coordinación Cirugía (Profesional: Dai Pérez)
- Urgencia (Prioridad: 🔴 Alta siempre)
- Reprogramación
- Sin disponibilidad
- Consulta sin respuesta
- Factura pendiente
- Problema alineadores (Prioridad: 🔴 Alta) — attache/tope suelto o alineador roto
- Aviso alineadores sin turno — paciente EN CURSO sin próximo turno planificado
- Cobro sin respuesta — paciente no respondió al 2do intento de cobro
- Datos para actualizar — paciente informó DNI/email/fecha nac pero Sofía no puede editar BBDD PACIENTES (keys legacy). Contexto: "DNI: 35123456, email: juan@email.com"
- Archivo/estudio recibido — paciente envió archivo/estudio que Sofía no puede procesar
- Archivo/estudio recibido — paciente envió foto o archivo de estudio

### GS-2 — Leer facturas pendientes de envío ✅
**Sheet:** BASES PARA WHATSAPP → F2-Facturas
**URL:** https://docs.google.com/spreadsheets/d/1J6NgE-CM4gsXn5Alr0KTc-PsepPpZaSByCfPtsDsahU
**Operación:** Get All Rows + Filter
**Filtro:** Factura PDF = "REALIZADA" AND Envio Factura PDF = "PENDIENTE"

### GS-3 — Actualizar estado de envío de factura ✅
**Sheet:** BASES PARA WHATSAPP → F2-Facturas
**Operación:** Update Row
**Campo:** Envio Factura PDF → "ENVIADO"

---

## CADENAS DE OPERACIONES (secuencias comunes)

### Cadena A: Contacto nuevo → Identificar → Registrar lead
```
Chatwoot: ¿tiene historial? → SÍ → Identificado (no API)
                             → NO →
  #1 (buscar paciente por tel) → encontrado → Identificado
                                → vacío →
    #2 (buscar lead por tel) → encontrado → Lead conocido
                              → vacío →
      Sofía saluda, pide nombre → #3 (crear lead nuevo)
```

### Cadena B: Lead agenda primer turno (conversión completa)
```
#4 (consultar precio consulta + seña en TARIFARIO)
  → Sofía envía bloque informativo (precio + seña + datos)
    → Lead envía datos personales
      → #5 (crear paciente) → obtener ID Paciente
        → #6 (crear turno con ID Paciente, "Falta seña" en Descripcion)
          → #10 (actualizar lead → Cerrada Ganada)
```

Cuando llega la seña:
```
  → #7 (verificar duplicado) → no existe
    → #8 (registrar pago: Tipo = Seña)
      → #9 (quitar "Falta seña" de Descripcion de la sesion)
```

### Cadena C: Paciente existente pide turno
```
#1 (buscar paciente) → encontrado
  → #11 (consultar horarios de atención)
    → #12 (buscar turnos existentes en rango 3 semanas)
      → n8n calcula slots libres
        → Sofía ofrece 2-3 opciones
          → #6 (crear turno)
```

### Cadena D: Recordatorio diario (cron job n8n)
```
#16 (buscar turnos de mañana en BBDD SESIONES, Estado=Planificada)
  → Para cada turno: enviar WhatsApp recordatorio (formato con fecha larga + profesional)
    → Paciente responde SÍ:
      → #14 (actualizar a Confirmada)
        → #20 (verificar CONSGEN FIRMADO en BBDD PACIENTES):
          → Si = "OK": no pedir nada más
          → Si = "NO": calcular edad desde Fecha Nacimiento
            → ≥18: enviar link https://tally.so/r/dW6dvN?codigo=[ID PACIENTE]
            → <18: enviar link https://tally.so/r/EkXMVo?codigo=[ID PACIENTE]
        → "Perfecto, te esperamos mañana a las [hora] en Virrey del Pino 4191 3C 😊"
    → Paciente responde NO:
      → "Gracias por avisar 😊 ¿Querés que reprogramemos para otro día?"
        → SÍ: #12 (buscar opciones próximas 2 semanas) → #14 (EDIT: cambiar Fecha, Hora, Profesional del mismo turno. Estado queda Planificada)
        → NO: #14 (→ Cancelada) → "Sin problema, cuando quieras retomar me avisás 😊"
```

### Cadena E: Recordatorio alineadores (cron job n8n)
```
#21 (buscar todos los pacientes con ESTADO TRATAMIENTO = "EN CURSO")
  → Para cada paciente EN CURSO:
    → #22 (buscar último REALIZADA + próximo PLANIFICADA)
      → Si NO tiene próximo turno:
        → Alertar admin (WhatsApp a Franco + GS-1 tipo "Aviso alineadores sin turno")
        → Admin puede responder "ya finalizó" → #25 (cambiar a FINALIZADO)
      → Si tiene próximo turno:
        → n8n calcula días entre REALIZADA y PLANIFICADA
          → Si corresponde enviar hoy: WhatsApp recordatorio de cambio (sin nro de alineador)
```

### Cadena F: Cobro por orden admin
```
Admin envía mensaje con paciente + monto
  → #1 (buscar paciente)
    → #17 (consultar presupuesto/saldo)
      → Sofía envía mensaje de cobro al paciente
        → Paciente envía comprobante:
          → #7 (verificar duplicado) → #8 (registrar pago)
```

### Cadena G: Paciente pide factura
```
Paciente pide factura
  → Sofía pregunta: "¿A nombre de quién va la factura?"
    → Verificar si ya tiene DNI en BBDD PACIENTES (#1)
      → Si tiene DNI → no pedir
      → Si no tiene → pedir CUIT o DNI
    → Verificar monto del último pago (#18)
    → (NO preguntar descripción — la escribe un humano)
    → GS-1 (escribir en Tareas Pendientes como "Factura pendiente")
      → Sofía confirma: "Le paso los datos al equipo 😊"
```

### Cadena H: Admin pide enviar facturas
```
Admin envía orden "enviar facturas"
  → GS-2 (leer F2-Facturas: REALIZADA + PENDIENTE)
    → Para cada fila:
      → #1 (buscar teléfono del paciente por nombre)
        → Enviar PDF por WhatsApp
          → GS-3 (actualizar Envio Factura PDF → ENVIADO)
    → Sofía responde al admin: "Listo, se enviaron [N] facturas ✅"
```

### Cadena I: Reprogramación por iniciativa del paciente
```
Paciente pide reprogramar
  → #13 (buscar su turno Planificada/Confirmada)
    → #12 (buscar slots libres próximas 2 semanas)
      → Si hay opciones: Sofía ofrece 2-3 → paciente elige
        → #14 (EDIT mismo turno: cambiar Fecha, Hora, Profesional. Mantener Estado Planificada)
      → Si NO hay opciones:
        → GS-1 (tarea pendiente, Tipo: "Reprogramación")
```

### Cadena J: Paciente envía comprobante de pago
```
Paciente envía imagen de comprobante
  → Claude Vision lee la imagen → extrae: monto, fecha, tipo de operación
    → Sofía confirma al paciente: "Recibí tu comprobante. Veo una transferencia de $[monto] del [fecha]. ¿Es correcto?"
    → SIN ESPERAR confirmación, registrar pago:
      → #7 (verificar duplicado: mismo paciente + fecha + monto + Transferencia)
        → Si ya existe → "Perfecto, ya lo tenemos registrado 😊"
        → Si NO existe:
          → #8 (registrar pago en BBDD PAGOS)
            - Observaciones: incluir número de operación extraído del comprobante
            → Confirmar: "Listo, tu pago quedó registrado 😊"
```

### Cadena K: Escalamiento a humano (Chatwoot)
```
Trigger detectado (queja, clínico, pide hablar con persona, 2+ sin avanzar)
  → Sofía avisa al paciente: "Te comunico con el equipo ahora mismo"
    → En Chatwoot:
      1. Asignar conversación al agente humano (Cynthia/Franco)
      2. Agregar label "Escalado"
      3. Enviar nota interna (private note) con:
         - Motivo de escalada
         - Resumen de la conversación
         - Datos del paciente (nombre, ID, teléfono)
    → GS-1 (tarea pendiente según tipo)
    → Sofía deja de responder en esa conversación

Re-engagement (paciente escribe después):
  → Si conversación tiene label "Escalado" + estado "Resuelta" → quitar label → Sofía retoma
  → Si conversación tiene label "Escalado" + estado "Abierta" → Sofía NO responde (humano sigue a cargo)
```

### Cadena L: Seguimiento leads automático (cron n8n — 2 intentos máximo)
```
Cron diario en n8n:
  → Buscar en BBDD LEADS: Estado = "Nuevo", Fecha Creacion ≥ 3 días
    → Verificar en Chatwoot si respondió (historial de conversación)
      → Si respondió → cancelar seguimiento, conversación normal
      → Si NO respondió:
        → 1er intento (3 días): mensaje suave
          "Hola 😊 ¿Pudiste pensar lo que charlamos? Si tenés alguna duda más, acá estoy"
          → #24 (Estado → "Contactado Frio", Notas → "1er seguimiento [fecha]: sin respuesta")
        → 2do intento (7 días) — ÚLTIMO:
          "Hola, soy Sofía de Stick. Tenemos turnos disponibles esta semana. ¿Te interesa que te reserve uno?"
          → #24 (Estado → "Cerrada Perdida", Notas → "2do seguimiento [fecha]: sin respuesta. Cerrado.")

⚠️ MÁXIMO 2 intentos. NO hay 3er intento.
Si el lead no muestra interés o dice que no → cerrar inmediatamente como "Cerrada Perdida"
```

### Cadena M: Problema con alineadores (paciente reporta)
```
Paciente reporta problema con alineadores:

Caso 1 — Attache o tope se salió:
  → Sofía: "¿Podrías enviarme una foto marcando cuál es el que se salió?"
    → Paciente envía foto
      → Claude Vision recibe la imagen
      → GS-1 (Tipo: "Problema alineadores", Prioridad: 🔴 Alta,
              Contexto: "Attache/tope suelto. Foto recibida. Revisar con Cyn.")
      → Sofía: "Perfecto, lo vamos a revisar con Cyn y te avisamos 😊"

Caso 2 — Alineador roto:
  → Sofía: "¿Podrías enviarme una foto del alineador roto?"
    → Paciente envía foto
      → Claude Vision recibe la imagen
      → GS-1 (Tipo: "Problema alineadores", Prioridad: 🔴 Alta,
              Contexto: "Alineador roto. Foto recibida. Revisar con Cyn.")
      → Sofía: "Perfecto, lo vamos a revisar con Cyn y te avisamos 😊"

Caso 3 — Otro problema (dolor, molestia, etc.):
  → Escalar a humano → Cadena K
```

### Cadena N: Cobro por orden del admin
```
Admin envía: "Cobrarle $X a [paciente] por [concepto]"
  → #1 (buscar paciente)
    → #17 (consultar presupuesto/saldo)
      → Sofía envía al paciente:
        "Hola [Nombre] 😊 Te quería comentar que tenés un saldo pendiente de $[monto]
         por [concepto]. Te paso el alias para transferir: ODONTO.CYNTHIA.
         Cualquier duda me avisás."
      → Si paciente responde con comprobante → Cadena J
      → Si no responde en 48hs:
        → 2do mensaje: "Hola [Nombre] 😊 Solo te recuerdo lo de la transferencia. Cualquier duda me avisás"
      → Si no responde al 2do:
        → Avisar a Franco por WhatsApp
        → GS-1 (Tipo: "Cobro sin respuesta", Contexto: paciente + monto + concepto)
        → NUNCA 3er intento automático
```

---

## PENDIENTES DE VERIFICAR

| # | Qué verificar | Prioridad | Estado |
|---|---|---|---|
| ~~🔬~~ | ~~Test API v2 initial values/formulas~~ | ~~ALTA~~ | ✅ RESUELTO |
| ~~1~~ | ~~Tabla horarios en API~~ | ~~ALTA~~ | ✅ RESUELTO — `LISTA O \| HORARIOS DE ATENCION` |
| ~~2~~ | ~~Formato de fechas en filtros API~~ | ~~ALTA~~ | ✅ RESUELTO — MM/DD/YYYY |
| ~~3~~ | ~~Campo relación paciente en BBDD ALINEADORES~~ | ~~MEDIA~~ | ✅ RESUELTO — `ID PACIENTE` confirmado |
| ~~4~~ | ~~Consentimiento~~ | ~~MEDIA~~ | ✅ RESUELTO — Campo `CONSGEN FIRMADO` en BBDD PACIENTES ("OK"/"NO") + Links Tally |
| ~~5~~ | ~~Lectura de comprobante con Claude Vision~~ | ~~MEDIA~~ | ✅ RESUELTO — Extraer monto, fecha, tipo. Nro operación → Observaciones |
| ~~6~~ | ~~M1 Turnos editable?~~ | ~~MEDIA~~ | ✅ RESUELTO — NO, es read-only. Usar BBDD SESIONES |
| ~~7~~ | ~~M2/M3 seguimiento alineadores~~ | ~~MEDIA~~ | ✅ RESUELTO — Ya no se usan |
| 8 | Límite de filas en respuesta Find | BAJA | ⏳ Pendiente |
| ~~9~~ | ~~Test crear paciente via API~~ | ~~MEDIA~~ | ✅ RESUELTO — Add OK, key UUID auto-gen, initial values OK (Estado, Fecha Alta, email default) |
| ~~10~~ | ~~Test BBDD PRESUPUESTOS via API~~ | ~~MEDIA~~ | ✅ RESUELTO — Add OK, KEY COMPUESTO (Row ID + ID Presupuesto), ESTADO: ACTIVO/FINALIZADO/CANCELADO |
| ~~11~~ | ~~Test BBDD ALINEADORES via API~~ | ~~MEDIA~~ | ✅ RESUELTO — Find OK, KEY es `ID ALINEADORES` (no ID PACIENTE), ESTADO TRATAMIENTO funciona como filtro |
| ~~12~~ | ~~Test Edit BBDD SESIONES~~ | ~~ALTA~~ | ✅ RESUELTO — Edit OK con ID Sesion |
| ~~13~~ | ~~Test Add/Delete BBDD PAGOS~~ | ~~ALTA~~ | ✅ RESUELTO — Requiere: Paciente + Tratamiento + campos pago. Delete por ID Pago |
| ~~14~~ | ~~Test Add/Delete BBDD GASTOS~~ | ~~MEDIA~~ | ✅ RESUELTO — 11 campos required! Delete por ID Gasto |
| ~~15~~ | ~~Test BBDD TARIFARIO~~ | ~~MEDIA~~ | ✅ RESUELTO — 38 registros, precios en USD |
| ~~16~~ | ~~Test Edit BBDD PACIENTES~~ | ~~ALTA~~ | ⚠️ NO FUNCIONA — Keys legacy "ANT" dan 404. UUID keys SÍ funcionan. Workaround: GS-1 |

---

## ESTADO DE MAPEO

**✅ COMPLETADO — Todas las operaciones mapeadas y validadas con Franco:**
- Ops #1-#18: Validadas ✅
- Ops #19, #23: Eliminadas (M1 y M2/M3 no se usan)
- Ops #20-#22, #24-#25: Validadas ✅
- Cadenas A-N: Completas ✅
- Google Sheets GS-1, GS-2, GS-3: Completas ✅

**Operaciones que NO requieren API (lógica conversacional en system prompt):**
- Objeciones ("es muy caro", "no tengo tiempo", etc.) → Sección 7 del system prompt
- Manejo de ghosting → Sección 8 del system prompt
- Protocolos de presentación → Sección 6 del system prompt
- Información de tratamientos → Archivo `tratamientos_stick.md`
- Adaptación por señales del paciente → Sección 11 del system prompt

**Tablas que NO se usan via API:**
- `M1 Turnos` — vista read-only, NO usar para ninguna acción
- `M2 Seg Cambio C Seg` — descontinuada
- `M3 Seg Cambio S Seg` — descontinuada
