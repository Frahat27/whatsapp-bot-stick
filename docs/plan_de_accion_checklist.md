# Plan de Accion — Bot Sofia STICK
# Checklist v2 — Python + React (sin n8n, sin Chatwoot)

**Stack:** Python (FastAPI) + React (Next.js) + PostgreSQL + Claude API + AppSheet API + Google Sheets

---

## FASE 0 — Infraestructura Base (Semana 1-2)

- [ ] **0.1** Configurar WhatsApp Business API
  - [ ] Registrar numero de telefono en Meta Business
  - [ ] Verificar negocio en Meta Business Manager
  - [ ] Obtener token permanente de acceso
  - [ ] Configurar webhook URL apuntando al backend

- [x] **0.2** Setup proyecto Python (FastAPI)
  - [x] Crear estructura del proyecto (src/, tests/, config/)
  - [x] Instalar dependencias: fastapi, uvicorn, anthropic, httpx, sqlalchemy, apscheduler
  - [x] Configurar variables de entorno (.env): API keys, DB URL, etc.
  - [ ] Setup Docker + docker-compose para desarrollo local
  - [x] Configurar logging estructurado

- [x] **0.3** Configurar PostgreSQL ✅
  - [x] Instalar/configurar PostgreSQL (Neon — sa-east-1 São Paulo)
  - [x] Disenar schema: conversaciones, mensajes, estados de flujo
  - [x] Crear migraciones con Alembic — migración inicial aplicada
  - [x] Testear conexion desde FastAPI — 5 tablas verificadas

- [ ] **0.4** Configurar credenciales externas
  - [ ] AppSheet API Key
  - [ ] Google Sheets service account (Franco.json)
  - [ ] Claude API Key (Anthropic)
  - [ ] WhatsApp Business API Token

- [x] **0.5** Crear Google Sheet "Tareas Pendientes WhatsApp" ✅
  - [x] Crear spreadsheet con columnas documentadas (A-L)
  - [x] Configurar dropdowns: Tipo, Prioridad, Estado
  - [x] Compartir con service account (Franco.json)
  - [x] Verificar acceso desde Python — client implementado + test OK

- [ ] **0.6** Test de conectividad end-to-end
  - [ ] Recibir webhook de WhatsApp en FastAPI
  - [ ] Llamar AppSheet API y recibir datos
  - [ ] Llamar Claude API y recibir respuesta
  - [ ] Enviar respuesta hardcodeada de vuelta por WhatsApp
  - [ ] Verificar ciclo completo: mensaje -> proceso -> respuesta

---

## FASE 1 — Backend Core: Identificacion + IA (Semana 3-5)

- [x] **1.1** Webhook handler de WhatsApp ✅
  - [x] Endpoint POST /webhook para recibir mensajes
  - [x] Endpoint GET /webhook para verificacion de Meta
  - [x] Validar firma del webhook (X-Hub-Signature)
  - [x] Parsear tipos de mensaje: texto, imagen, audio, documento, ubicacion
  - [x] Procesamiento asincrono (background tasks o queue)

- [x] **1.2** Modulo AppSheet API (cliente reutilizable) ✅
  - [x] Clase AppSheetClient con metodos Find, Add, Edit, Delete
  - [x] Parametrizable por tabla (Pacientes, Sesiones, Pagos, etc.)
  - [x] Manejo de rate limits (~45s entre requests)
  - [x] Formato de fechas MM/DD/YYYY automatico
  - [x] Manejo de errores: 200 con body vacio = rate limited
  - [x] Properties: {} (sin Locale, causa respuestas vacias)

- [x] **1.3** Identificar contacto ✅
  - [x] Extraer telefono del mensaje (formato +5491112345678) — phone.py completo
  - [x] Buscar en BBDD Pacientes via AppSheet → _identify_contact()
  - [x] Si no existe, buscar en BBDD Leads
  - [x] Si no existe en ninguna, marcar como contacto nuevo
  - [x] Armar objeto de contexto con datos del contacto → patient_context dict

- [x] **1.4** Integrar Claude AI con Tool Calling ✅
  - [x] Configurar Anthropic SDK (AsyncAnthropic, lazy init)
  - [x] Cargar system prompt v2.0 (sofia_system_prompt.md) — data_loader.py completo
  - [x] Cargar base de tratamientos (tratamientos_stick.md) — data_loader.py completo
  - [x] Definir 15 tools en src/tools/definitions.py (buscar_paciente, agendar_turno, crear_tarea, etc.)
  - [x] Manejar tool_use responses con callback ToolExecutor
  - [x] Loop de tool calling hasta respuesta final (max 15 iteraciones)
  - [x] Enviar contexto: patient_context inyectado en system prompt
  - [x] generate_response_with_image para comprobantes (Vision)

- [x] **1.5** Memoria conversacional (PostgreSQL) ✅
  - [x] Tabla conversations: id, phone, patient_id, created_at, updated_at
  - [x] Tabla messages: id, conversation_id, role, content, timestamp
  - [x] Almacenar cada mensaje entrante y saliente (metodo en conversation_manager)
  - [x] Recuperar ultimos N mensajes como contexto para Claude — _build_message_history()
  - [ ] TTL configurable para limpiar conversaciones viejas

- [x] **1.6** Envio de mensajes WhatsApp ✅
  - [x] Funcion enviar texto (WhatsApp Cloud API)
  - [x] Funcion enviar imagen/documento (media upload + send)
  - [x] Funcion enviar template messages (para recordatorios)
  - [x] Manejo de errores y timeout
  - [x] Logging de cada mensaje enviado
  - [x] mark_as_read (doble tilde azul)
  - [x] download_media (2-step: URL → download)

- [~] **1.7** Deteccion de numeros admin
  - [x] Detectar si viene de 1123266671 (Franco) o 5491171342438 (Cynthia) — phone.py is_admin_phone()
  - [ ] Cambiar modo de respuesta: directo y operativo
  - [ ] Parsear ordenes del admin (cobrar, enviar facturas, etc.)

- [~] **1.8** Tests unitarios del core
  - [x] Tests de webhook handler (payloads reales de Meta) — 4 tests
  - [ ] Tests de AppSheetClient (mocked)
  - [ ] Tests de identificacion de contacto
  - [ ] Tests de integracion con Claude (mocked)
  - [ ] Tests de envio de mensajes (mocked)
  - [ ] CI pipeline basico

---

## FASE 2 — Modulo Turnos (Semana 6-8)

- [ ] **2.1** Consultar horarios de atencion
  - [ ] Tool: consultar_horarios -> leer O-HORARIOS DE ATENCION via AppSheet
  - [ ] Parsear horarios por dia y profesional
  - [ ] Cache en memoria con TTL

- [ ] **2.2** Buscar disponibilidad
  - [ ] Tool: buscar_disponibilidad(dia_preferido, horario_preferido)
  - [ ] Leer BBDD Sesiones proximas 3 semanas
  - [ ] Cruzar horarios de atencion vs turnos ocupados
  - [ ] Filtrar por preferencia del paciente
  - [ ] Retornar 2-3 opciones disponibles

- [ ] **2.3** Agendar turno estandar
  - [ ] Tool: agendar_turno(paciente, fecha, hora, tratamiento, profesional)
  - [ ] Claude maneja el flujo conversacional (preguntar, ofrecer, confirmar)
  - [ ] Crear turno en BBDD Sesiones via AppSheet (Add)
  - [ ] Payload: Paciente, Fecha MM/DD/YYYY, Hora, Tratamiento, Profesional, Estado=Planificada
  - [ ] Respuesta con confirmacion: fecha, hora, profesional, direccion

- [ ] **2.4** Agendar turno de urgencia
  - [ ] Tool: buscar_urgencia() -> turnos libres esta semana
  - [ ] NO preguntar disponibilidad, ofrecer directo
  - [ ] Tipo de turno: Urgencia, Observaciones: descripcion breve
  - [ ] Si no hay opciones: crear tarea en GSheet tipo Urgencia, prioridad Alta

- [ ] **2.5** Reprogramar turno
  - [ ] Tool: buscar_turno_paciente(paciente_id) -> turno actual
  - [ ] Tool: modificar_turno(turno_id, nueva_fecha, nueva_hora, profesional)
  - [ ] Buscar opciones en proximas 2 semanas
  - [ ] Si no hay opciones: crear tarea en GSheet tipo Reprogramacion

- [ ] **2.6** Cancelar turno
  - [ ] Tool: cancelar_turno(turno_id) -> estado = Cancelada
  - [ ] Claude confirma con el paciente antes de ejecutar
  - [ ] Preguntar si quiere reagendar

- [ ] **2.7** Regla miercoles Dra. Ana Mino
  - [ ] Logica en buscar_disponibilidad: si cae Mi 14:30-20:00 -> profesional = Ana Mino
  - [ ] Informar al paciente con quien se atiende

- [ ] **2.8** Turnos que NO se agendan directamente
  - [ ] Endodoncia -> crear tarea Coordinacion Endodoncia + avisar paciente
  - [ ] Implantes -> crear tarea Coordinacion Implantes + avisar paciente
  - [ ] Cirugia -> crear tarea Coordinacion Cirugia + avisar paciente
  - [ ] Tool: crear_tarea_coordinacion(tipo, paciente, contexto)

- [ ] **2.9** Regla pacientes nuevos
  - [ ] Todo paciente nuevo -> tipo = Odontologia primera vez
  - [ ] Anotar motivo real en campo Observaciones

---

## FASE 3 — Conversion Lead -> Paciente (Semana 9-10)

- [ ] **3.1** Registro de leads nuevos
  - [ ] Detectar contacto desconocido
  - [ ] Claude pregunta nombre y motivo
  - [ ] Tool: crear_lead(nombre, telefono, canal, motivo)

- [ ] **3.2** Flujo primera vez completo
  - [ ] Paso 1: Acordar fecha y horario (flujo turnos)
  - [ ] Paso 2: Enviar bloque informativo completo en UN mensaje
  - [ ] Tool: consultar_tarifario(tratamiento) para valor consulta y sena
  - [ ] Incluir alias ODONTO.CYNTHIA para transferir
  - [ ] Solicitar datos: nombre completo, DNI, fecha nacimiento, mail, referido

- [ ] **3.3** Crear paciente en BBDD Pacientes
  - [ ] Tool: crear_paciente(nombre, dni, fecha_nac, telefono, mail, referido)
  - [ ] Validar datos completos
  - [ ] SIEMPRE crear paciente ANTES de crear turno

- [ ] **3.4** Registrar sena — Escenario A (datos sin sena)
  - [ ] Crear paciente
  - [ ] Crear turno con "Falta sena" en Observaciones
  - [ ] Cuando confirme sena -> registrar_pago(tipo=SENA)
  - [ ] Quitar "Falta sena" de Observaciones

- [ ] **3.5** Registrar sena — Escenario B (datos + comprobante juntos)
  - [ ] Crear paciente
  - [ ] Registrar pago (Tipo=SENA)
  - [ ] Crear turno (sin "Falta sena")
  - [ ] Enviar confirmacion final

- [ ] **3.6** Consultar BBDD Tarifario
  - [ ] Tool: consultar_tarifario(tratamiento)
  - [ ] NUNCA hardcodear valores
  - [ ] Cache con TTL corto

---

## FASE 4 — Precios, Pagos y Cobros (Semana 11-13)

- [ ] **4.1** Informar precios
  - [ ] Consultar BBDD Tarifario
  - [ ] Regla descuentos: solo Alineadores, Brackets, Blanqueamiento
  - [ ] Resto: NO mencionar descuentos

- [ ] **4.2** Informar saldo pendiente
  - [ ] Consultar BBDD Presupuestos -> Saldo Pendiente
  - [ ] Multiples presupuestos: preguntar cual

- [ ] **4.3** Leer comprobantes (Claude Vision)
  - [ ] Detectar imagen en webhook
  - [ ] Descargar media de WhatsApp API
  - [ ] Claude extrae: monto, fecha, operacion
  - [ ] Confirmar al paciente

- [ ] **4.4** Regla anti-duplicado de pagos
  - [ ] Buscar pago existente antes de registrar
  - [ ] Mismo paciente + fecha + monto + metodo

- [ ] **4.5** Registrar pago
  - [ ] Tool: registrar_pago(...)
  - [ ] Add en BBDD Pagos via AppSheet

- [ ] **4.6** Cobro por orden admin
  - [ ] Detectar orden desde numero admin
  - [ ] Enviar mensaje amable + alias ODONTO.CYNTHIA
  - [ ] Max 2 intentos, NUNCA usar "deuda"

- [ ] **4.7** Manejo de objeciones de precio
  - [ ] Protocolos documentados en system prompt

---

## FASE 5 — Recordatorios y Automatizaciones (Semana 14-15)

- [ ] **5.1** Setup APScheduler
  - [ ] Integrar con FastAPI
  - [ ] Timezone America/Buenos_Aires
  - [ ] Logging y error handling

- [ ] **5.2** Cron: Recordatorio de turnos
  - [ ] Job diario, turnos de manana
  - [ ] Formato exacto documentado
  - [ ] Respuesta SI/NO

- [ ] **5.3** Flujo SI/NO a recordatorio
  - [ ] SI -> Confirmada + verificar consentimiento + link Tally
  - [ ] NO -> reprogramar o cancelar

- [ ] **5.4** Cron: Recordatorio cambio alineadores
  - [ ] Logica de ciclos (12/15/15 dias)
  - [ ] Solo si tiene proximo turno planificado

- [ ] **5.5** Alerta admin: EN CURSO sin proximo turno

- [ ] **5.6** Cron: Seguimiento de leads
  - [ ] 3 dias -> 7 dias -> cerrar

- [ ] **5.7** Protocolo de ghosting
  - [ ] Max 2 mensajes sin respuesta

---

## FASE 6 — Panel Admin (Frontend) (Semana 16-18)

- [ ] **6.1** Setup proyecto frontend
  - [ ] Next.js + React + TypeScript + Tailwind
  - [ ] Auth JWT (Franco, Cynthia)

- [ ] **6.2** Backend: endpoints API para el panel
  - [ ] CRUD conversaciones, mensajes, pacientes, tareas
  - [ ] WebSocket /ws para real-time

- [ ] **6.3** Vista de conversaciones (sidebar)
  - [ ] Lista con indicadores y filtros

- [ ] **6.4** Vista de chat (centro)
  - [ ] Thread real-time estilo WhatsApp

- [ ] **6.5** Sidebar datos del paciente
  - [ ] Info completa + turnos + saldo + tratamiento

- [ ] **6.6** Takeover humano
  - [ ] Tomar control / devolver a Sofia

- [ ] **6.7** Panel de tareas pendientes
  - [ ] Lista, filtros, resolver

- [ ] **6.8** Notificaciones
  - [ ] Web Push + sonido + badge

- [ ] **6.9** Responsive + Mobile

---

## FASE 7 — Escalado y Facturacion (Semana 19-20)

- [ ] **7.1** Sistema de escalado via panel
- [ ] **7.2** Re-engagement post-escalado
- [ ] **7.3** Consultas sin respuesta
- [ ] **7.4** Solicitud de factura
- [ ] **7.5** Envio de facturas PDF
- [ ] **7.6** Archivos y estudios recibidos

---

## FASE 8 — Testing y Go-Live (Semana 21-24)

- [ ] **8.1** Testing piloto (10-15 pacientes)
- [ ] **8.2** Ajuste del system prompt
- [ ] **8.3** Optimizar costos Claude
- [ ] **8.4** Metricas y dashboard
- [ ] **8.5** Documentacion operativa
- [ ] **8.6** Go-live gradual (30% -> 60% -> 100%)
- [ ] **8.7** Soporte post-lanzamiento (2 semanas)

---

## Resumen

| Fase | Modulo | Semanas |
|---|---|---|
| 0 | Infraestructura Base | 1-2 |
| 1 | Backend Core | 3-5 |
| 2 | Turnos | 6-8 |
| 3 | Conversion Lead -> Paciente | 9-10 |
| 4 | Precios, Pagos y Cobros | 11-13 |
| 5 | Recordatorios | 14-15 |
| 6 | Panel Admin (Frontend) | 16-18 |
| 7 | Escalado y Facturacion | 19-20 |
| 8 | Testing y Go-Live | 21-24 |
| **TOTAL** | | **~24 semanas (6 meses)** |
