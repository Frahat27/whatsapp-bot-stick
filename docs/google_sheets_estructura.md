# Estructura de Google Sheets — Bot Sofía

---

## 1. TAREAS PENDIENTES WHATSAPP

**URL:** https://docs.google.com/spreadsheets/d/1Ql5Li8PdpZGg7obxmEjoyH1h-rmjQw0F_WOnwn34GRU
**Propósito:** Bandeja de tareas que Sofía no puede resolver sola. El equipo (Franco/Cynthia) las revisa y resuelve.

### Tipos de tarea

| Tipo | Cuándo se genera | Prioridad default |
|---|---|---|
| Coordinación Endodoncia | Paciente necesita turno con Nacho Fernández | 🟡 Normal |
| Coordinación Implantes | Paciente necesita turno con Diego Figueiras | 🟡 Normal |
| Coordinación Cirugía | Paciente necesita turno con Dai Pérez | 🟡 Normal |
| Urgencia | No hay turnos de urgencia disponibles esta semana | 🔴 Alta |
| Reprogramación | No se encontró nueva fecha al reprogramar turno | 🟡 Normal |
| Sin disponibilidad | No hay turnos en las próximas 3 semanas | 🟡 Normal |
| Consulta sin respuesta | Sofía no puede responder (consulta clínica técnica o fuera de su conocimiento) | 🟡 Normal |
| Factura pendiente | Paciente solicita factura — Sofía recopiló los datos | 🟡 Normal |

### Columnas

| # | Columna | Tipo | Quién la llena | Descripción | Ejemplo |
|---|---|---|---|---|---|
| A | Fecha Creación | Datetime | Sofía (auto) | Timestamp del momento en que se genera la tarea | 2026-03-03 14:30 |
| B | Tipo | Texto (dropdown) | Sofía (auto) | Categoría de la tarea (ver tabla de tipos arriba) | Coordinación Endodoncia |
| C | Prioridad | Texto (dropdown) | Sofía (auto) | 🔴 Alta / 🟡 Normal | 🟡 Normal |
| D | Paciente | Texto | Sofía (auto) | Nombre del paciente | García, Juan |
| E | Teléfono | Texto | Sofía (auto) | Número de WhatsApp del paciente | +54 9 11 1234-5678 |
| F | ID Paciente | Texto | Sofía (auto) | ID de AppSheet (si existe en BBDD PACIENTES) | ANT-15 |
| G | Profesional | Texto | Sofía (auto) | Especialista relacionado (si aplica) | Nacho Fernández |
| H | Contexto | Texto largo | Sofía (auto) | Descripción de la situación / qué necesita el paciente | "Dolor en muela 46, necesita conducto. Paciente prefiere lunes o martes" |
| I | Estado | Texto (dropdown) | Manual → equipo | Estado de la tarea | Pendiente / En proceso / Resuelto |
| J | Resuelta por | Texto | Manual → equipo | Quién resolvió la tarea | Franco / Cynthia |
| K | Fecha Resolución | Date | Manual → equipo | Cuándo se cerró la tarea | 2026-03-04 |
| L | Notas Resolución | Texto largo | Manual → equipo | Qué se hizo para resolver | "Turno con Nacho para lunes 10/3 18hs" |

### Reglas de llenado por tipo

**Coordinación Endodoncia / Implantes / Cirugía:**
- Profesional: Nombre del especialista correspondiente
- Contexto: Qué necesita el paciente + disponibilidad que mencionó
- Ejemplo: Tipo="Coordinación Endodoncia", Profesional="Nacho Fernández", Contexto="Dolor intenso en muela 46, probable conducto. Disponible lunes y jueves por la tarde"

**Urgencia:**
- Prioridad: 🔴 Alta (siempre)
- Contexto: Qué le pasa al paciente + por qué no se pudo agendar
- Ejemplo: Tipo="Urgencia", Prioridad="🔴 Alta", Contexto="Dolor agudo en premolar superior, no hay turnos esta semana. Paciente necesita atención urgente"

**Reprogramación:**
- Contexto: Turno original (fecha y hora) + por qué no se pudo reprogramar
- Ejemplo: Tipo="Reprogramación", Contexto="Turno original: 05/03 15:00. No encontró opciones en 2 semanas. Prefiere martes/jueves por la tarde"

**Sin disponibilidad:**
- Contexto: Qué tipo de turno buscaba + preferencias del paciente
- Ejemplo: Tipo="Sin disponibilidad", Contexto="Control general, prefiere viernes por la mañana. Sin opciones en 3 semanas"

**Consulta sin respuesta:**
- Contexto: La pregunta exacta del paciente + por qué Sofía no puede responder
- Ejemplo: Tipo="Consulta sin respuesta", Contexto="Paciente pregunta si puede hacer alineadores teniendo un implante en muela 36 y un puente de 3 piezas. Consulta técnica que requiere evaluación profesional"

**Factura pendiente:**
- Contexto: Datos recopilados por Sofía para la factura
- Formato del contexto para facturas:
  ```
  DATOS FACTURA:
  - Nombre para factura: [lo que pidió el paciente]
  - CUIT/DNI: [número]
  - Tipo doc: [CUIT/DNI]
  - Descripción solicitada: [lo que el paciente quiere que figure]
  - Monto: $[monto]
  - Tratamiento real: [tratamiento que se realizó]
  ```
- Ejemplo: Tipo="Factura pendiente", Contexto="DATOS FACTURA: Nombre: García Juan Carlos, CUIT: 20-12345678-9, Tipo doc: CUIT, Descripción solicitada: 'Prestación odontológica - consulta', Monto: $45.000, Tratamiento real: Odontología primera vez"

---

## 2. F2-FACTURAS (referencia — Google Sheet existente)

**URL:** https://docs.google.com/spreadsheets/d/1J6NgE-CM4gsXn5Alr0KTc-PsepPpZaSByCfPtsDsahU
**Ubicación:** Dentro del spreadsheet "BASES PARA WHATSAPP", hoja "F2-Facturas"
**Propósito:** Base para el pipeline de facturación AFIP. AppSheet replica aquí automáticamente los datos de BBDD FACTURAS.

### Columnas (extraídas de los scripts de facturación)

| Columna | Quién la llena | Descripción |
|---|---|---|
| Estado | Script 2 / Manual | PENDIENTE → FACTURADA → ERROR |
| Fecha Emision | Script 2 (auto, fecha del día) | Fecha de emisión |
| Concepto | AppSheet (replicado de BBDD FACTURAS) | 1=Productos, 2=Servicios, 3=Ambos |
| Tipo Doc | AppSheet | 80=CUIT, 96=DNI, 99=DNI |
| CUIT Cliente | AppSheet | Número de documento del cliente |
| Nombre Cliente | AppSheet | Nombre para la factura |
| Condicion IVA Cliente | AppSheet | Código de condición IVA |
| Total Factura | AppSheet | Monto total |
| Importe Neto | AppSheet | Importe neto |
| Importe IVA | AppSheet | Importe IVA |
| Importe Tributos | AppSheet | Importe tributos |
| Item 1-4 | AppSheet | Descripción de cada ítem facturado |
| Cantidad 1-4 | AppSheet | Cantidad por ítem |
| Precio unitario 1-4 | AppSheet | Precio unitario por ítem |
| Subtotal 1-4 | AppSheet | Subtotal por ítem |
| FchServDesde | AppSheet | Fecha inicio servicio (para concepto 2/3) |
| FchServHasta | AppSheet | Fecha fin servicio (para concepto 2/3) |
| FchVtoPago | AppSheet | Fecha vencimiento pago (para concepto 2/3) |
| CAE | Script 2 (auto) | Código de Autorización Electrónica (AFIP) |
| Vto CAE | Script 2 (auto) | Vencimiento del CAE |
| Nro Factura | Script 2 (auto) | Número de comprobante correlativo |
| Factura PDF | Script 3 → "REALIZADA" / Manual → "PENDIENTE" | Estado de generación del PDF |
| Envio Factura PDF | Sofía → "ENVIADO" | Estado de envío por WhatsApp |
| Columna | Script 3 (auto) | Nombre del archivo PDF generado |
| Observaciones | Script 2 (errores) | Mensajes de error o notas |

### Pipeline de facturación completo

```
1. Secretaria/Cynthia crea registro en BBDD FACTURAS (AppSheet)
       ↓ (automatización AppSheet)
2. Se replica automáticamente en F2-Facturas (Google Sheet) con Estado = PENDIENTE
       ↓ (Script 1 - Facturas-auto2.py)
3. Login en AFIP/ARCA → obtiene Token + Sign
       ↓ (Script 2 - factura_gs.py)
4. Genera factura en AFIP → recibe CAE, Vto CAE, Nro Factura → Estado = FACTURADA
       ↓ (Script 3 - Emitir_pdf.py)
5. Genera PDF con QR de AFIP → Factura PDF = REALIZADA
       ↓ (Sofía / Bot - NUEVO)
6. Admin solicita envío → Sofía lee F2-Facturas → envía PDF por WhatsApp → Envio Factura PDF = ENVIADO
```

### Flujo de Sofía para enviar facturas PDF (acción por orden admin)

**Trigger:** Franco (54 9 1123266671) o Cynthia (54 9 1171342438) le dicen a Sofía que envíe las facturas pendientes.

**Proceso:**
1. Sofía lee F2-Facturas
2. Filtra filas donde:
   - Columna "Factura PDF" = **REALIZADA**
   - Columna "Envio Factura PDF" = **PENDIENTE**
3. Para cada fila que cumple:
   a. Obtiene el nombre del archivo PDF de la columna "Columna" (ej: `C_0002_00000123.pdf`)
   b. Busca el teléfono del paciente (por Nombre Cliente → cruzar con BBDD PACIENTES)
   c. Envía el PDF por WhatsApp al paciente con mensaje:
      > "Hola [Nombre] 😊 Te envío tu factura. Cualquier consulta me avisás."
   d. Actualiza "Envio Factura PDF" de PENDIENTE a **ENVIADO**
4. Responde al admin con resumen: "Listo, se enviaron [N] facturas ✅"

**⚠️ NOTA TÉCNICA (para implementación):**
- Los PDFs se generan actualmente en una carpeta local (`C:\STICK\0- SCRIPTS\1-FACTURACION-AUTOMATICA\ARCA_CYNT\FACTURAS PDF`).
- Para que el bot pueda enviarlos, necesitan estar accesibles en la nube (opciones: Google Drive compartido, o subirlos como media a WhatsApp Business API).
- Solución recomendada: Script 3 sube el PDF a Google Drive además de guardarlo local → Sofía lo descarga de Drive → lo envía por WhatsApp.
- Alternativa: n8n lee el archivo de una carpeta compartida o Drive y lo sube a la API de WhatsApp.

---

## NOTAS DE IMPLEMENTACIÓN

### Acceso de n8n a Google Sheets
- Service account: Franco.json (ya existe, usado por los scripts de facturación)
- Spreadsheet "BASES PARA WHATSAPP" ya está compartido con el service account
- Para TAREAS PENDIENTES: compartir la nueva Google Sheet con el mismo service account

### Convención de teléfonos
- Formato: siempre con código país, sin espacios → `5491112345678`
- Debe coincidir con el formato en BBDD PACIENTES para poder cruzar

### Validación de datos
- Sofía valida que los campos obligatorios estén completos antes de crear la fila
- Si falta información, la pide al paciente antes de registrar
- El campo Contexto debe ser siempre descriptivo (no solo "turno" sino "turno de control, paciente prefiere viernes mañana")
