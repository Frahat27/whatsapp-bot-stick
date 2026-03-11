# Plan de Accion — Bot Sofia STICK
# Checklist v4 — Actualizado 2026-03-10 (estado real del codigo)
# Python + React (sin n8n, sin Chatwoot — Panel Admin custom)

**Stack:** Python (FastAPI) + React (Next.js 16) + PostgreSQL (Neon + Cloud SQL) + Claude API + AppSheet API + Google Sheets + Redis (Upstash)

**Leyenda:** [x] = implementado y funcionando | [~] = parcial | [ ] = pendiente

---

## FASE 0 — Infraestructura Base ⚠️ (parcial)

- [ ] **0.1** Configurar WhatsApp Business API 🔴 CRITICO
  - [ ] Registrar numero de telefono en Meta Business
  - [ ] Verificar negocio en Meta Business Manager
  - [ ] Obtener token permanente de acceso (WHATSAPP_TOKEN)
  - [ ] Obtener PHONE_NUMBER_ID
  - [ ] Configurar webhook URL apuntando al backend

- [x] **0.2** Setup proyecto Python (FastAPI) ✅
  - [x] Crear estructura del proyecto (src/, tests/, config/)
  - [x] Instalar dependencias: fastapi, uvicorn, anthropic, httpx, sqlalchemy, apscheduler
  - [x] Configurar variables de entorno (.env): API keys, DB URL, etc.
  - [~] Setup Docker — Dockerfile existe, falta docker-compose
  - [x] Configurar logging estructurado

- [x] **0.3** Configurar PostgreSQL ✅
  - [x] Instalar/configurar PostgreSQL (Neon — sa-east-1 Sao Paulo) — bot-internal
  - [x] Instalar/configurar Cloud SQL (GCP) — clinic data (nexus_clinic_os)
  - [x] Disenar schema: conversaciones, mensajes, estados de flujo
  - [x] Crear migraciones con Alembic — migracion inicial aplicada
  - [x] Testear conexion desde FastAPI — 5 tablas verificadas

- [~] **0.4** Configurar credenciales externas
  - [x] AppSheet API Key — configurada en .env
  - [x] Google Sheets service account (Franco.json) — configurada en .env
  - [x] Claude API Key (Anthropic) — configurada, modelo configurable via CLAUDE_MODEL (default: Haiku 4.5)
  - [ ] WhatsApp Business API Token — 🔴 bloqueante

- [x] **0.5** Crear Google Sheet "Tareas Pendientes WhatsApp" ✅
  - [x] Crear spreadsheet con columnas documentadas (A-L)
  - [x] Configurar dropdowns: Tipo, Prioridad, Estado
  - [x] Compartir con service account (Franco.json)
  - [x] Verificar acceso desde Python — client implementado + test OK

- [ ] **0.6** Test de conectividad end-to-end 🔴 CRITICO (bloqueado por 0.1)
  - [ ] Recibir webhook de WhatsApp en FastAPI
  - [x] Llamar AppSheet API y recibir datos reales
  - [x] Llamar Claude API y recibir respuesta real
  - [ ] Enviar respuesta de vuelta por WhatsApp
  - [ ] Verificar ciclo completo: mensaje -> proceso -> respuesta

---

## FASE 1 — Backend Core: Identificacion + IA ✅ 95%

- [x] **1.1** Webhook handler de WhatsApp ✅
  - [x] Endpoint POST /webhook para recibir mensajes
  - [x] Endpoint GET /webhook para verificacion de Meta
  - [x] Validar firma del webhook (X-Hub-Signature)
  - [x] Parsear tipos de mensaje: texto, imagen, audio, documento, ubicacion
  - [x] Procesamiento asincrono (background tasks)

- [x] **1.2** Modulo AppSheet API (cliente reutilizable) ✅
  - [x] Clase AppSheetClient con metodos Find, Add, Edit, Delete
  - [x] Parametrizable por tabla (Pacientes, Sesiones, Pagos, etc.)
  - [x] Manejo de rate limits (~45s entre requests)
  - [x] Formato de fechas MM/DD/YYYY automatico
  - [x] Manejo de errores: 200 con body vacio = rate limited
  - [x] Properties: {} (sin Locale, causa respuestas vacias)
  - [x] **Cloud SQL directo via ClinicRepository (~5ms vs ~45s)** — reemplazo completo

- [x] **1.3** Identificar contacto ✅
  - [x] Extraer telefono del mensaje (formato +5491112345678) — phone.py completo
  - [x] Buscar en BBDD Pacientes via Cloud SQL → _identify_contact()
  - [x] Si no existe, buscar en BBDD Leads
  - [x] Si no existe en ninguna, marcar como contacto nuevo
  - [x] Armar objeto de contexto con datos del contacto → patient_context dict

- [x] **1.4** Integrar Claude AI con Tool Calling ✅
  - [x] Configurar Anthropic SDK (AsyncAnthropic, lazy init)
  - [x] Cargar system prompt v2.0 (sofia_system_prompt.md) — data_loader.py
  - [x] Cargar base de tratamientos (tratamientos_stick.md) — data_loader.py
  - [x] Definir 15 tools en src/tools/definitions.py
  - [x] Manejar tool_use responses con callback ToolExecutor
  - [x] Loop de tool calling hasta respuesta final (max 15 iteraciones)
  - [x] Enviar contexto: patient_context + fecha/hora actual inyectados en system prompt
  - [x] generate_response_with_image para comprobantes (Vision)
  - [x] Modelo configurable via CLAUDE_MODEL env var (default: Haiku 4.5)

- [~] **1.5** Memoria conversacional (PostgreSQL) ✅ parcial
  - [x] Tabla conversations: id, phone, patient_id, created_at, updated_at
  - [x] Tabla messages: id, conversation_id, role, content, timestamp
  - [x] Almacenar cada mensaje entrante y saliente
  - [x] Recuperar ultimos N mensajes como contexto para Claude — _build_message_history()
  - [x] Deteccion de opciones de turno caducadas (>1h) — inyecta nota forzando buscar_disponibilidad
  - [ ] TTL configurable para limpiar conversaciones viejas

- [x] **1.6** Envio de mensajes WhatsApp ✅
  - [x] Funcion enviar texto (WhatsApp Cloud API)
  - [x] Funcion enviar imagen/documento (media upload + send)
  - [x] Funcion enviar template messages (para recordatorios)
  - [x] Manejo de errores y timeout — retry con backoff exponencial
  - [x] Logging de cada mensaje enviado
  - [x] mark_as_read (doble tilde azul)
  - [x] download_media (2-step: URL → download)

- [~] **1.7** Deteccion de numeros admin
  - [x] Detectar si viene de 1123266671 (Franco) o 5491171342438 (Cynthia) — phone.py is_admin_phone()
  - [ ] Cambiar modo de respuesta: directo y operativo
  - [ ] Parsear ordenes del admin (cobrar, enviar facturas, etc.)

- [x] **1.8** Tests unitarios del core ✅ COMPLETO
  - [x] Tests de webhook handler (payloads reales de Meta) — 4 tests
  - [x] Tests de AppSheetClient/cache (mocked) — 12 tests
  - [x] Tests de identificacion de contacto — en test_tool_handlers.py
  - [x] Tests de integracion con Claude (mocked) — 13 tests
  - [x] Tests de envio de mensajes (mocked) — 9 tests con retry/backoff
  - [x] Tests de tool handlers (15 tools) — 28 tests
  - [x] Tests de disponibilidad — 86 tests
  - [x] Tests de recordatorios — 67 tests
  - [x] Tests de integracion E2E (mocked) — 20 tests
  - [x] Tests de AppSheet sync — 9 tests
  - [x] **Total: 352 tests, 19 archivos, 100% pass**
  - [ ] CI pipeline basico

---

## FASE 2 — Modulo Turnos ✅ COMPLETA

- [x] **2.1** Consultar horarios de atencion ✅
  - [x] Tool: consultar_horarios → leer "LISTA O | HORARIOS DE ATENCION" via Cloud SQL
  - [x] Parsear horarios por dia y profesional — _parse_horarios() en availability.py
  - [x] Cache Redis con TTL 24h para tablas estaticas

- [x] **2.2** Buscar disponibilidad ✅
  - [x] Tool: buscar_disponibilidad(dia_preferido, horario_preferido, semanas, tipo_turno)
  - [x] Leer BBDD Sesiones proximas semanas — calculate_available_slots()
  - [x] Cruzar horarios vs ocupados — _find_free_slots()
  - [x] Filtrar por preferencia — _matches_day_preference() + _matches_time_preference()
  - [x] Retornar 2-3 opciones — _select_best_options() round-robin diversificado
  - [x] Duracion por tipo tratamiento — get_treatment_duration()

- [x] **2.3** Agendar turno estandar ✅
  - [x] Tool: agendar_turno(paciente_id, paciente, tratamiento, fecha, hora, profesional, observaciones)
  - [x] Claude maneja flujo conversacional
  - [x] Crear turno en BBDD SESIONES via Cloud SQL + sync AppSheet instantaneo

- [x] **2.4** Agendar turno de urgencia ✅
  - [x] Via buscar_disponibilidad con semanas=1, tipo_turno="Urgencia"
  - [x] Si no hay opciones: crear_tarea_pendiente tipo Urgencia, prioridad Alta

- [x] **2.5** Reprogramar turno ✅
  - [x] Tool: buscar_turno_paciente(paciente_id) → turno actual
  - [x] Tool: modificar_turno(turno_id, fecha, hora, profesional, observaciones)
  - [x] Recalculo automatico de hora_fin al modificar

- [x] **2.6** Cancelar turno ✅
  - [x] Tool: cancelar_turno(turno_id) → Estado = "Cancelada"
  - [x] Claude confirma con paciente (via system prompt)

- [x] **2.7** Regla miercoles Dra. Ana Mino ✅
  - [x] _get_professional(): Mi 14:30-20:00 → "Ana Mino", resto → "Cynthia Hatzerian"
  - [x] Se informa automaticamente en opciones de disponibilidad

- [x] **2.8** Turnos que NO se agendan directamente ✅
  - [x] Endodoncia, Implantes, Cirugia → crear_tarea_pendiente con tipo Coordinacion
  - [x] Tool description instruye a Claude: "NO se agendan — usar crear_tarea_pendiente"

- [x] **2.9** Regla pacientes nuevos ✅
  - [x] Default tipo_turno = "Odontologia primera vez"
  - [x] Tool description: "Pacientes nuevos SIEMPRE se agendan como Odontologia primera vez"

---

## FASE 3 — Conversion Lead -> Paciente ✅ COMPLETA

- [x] **3.1** Registro de leads nuevos ✅
  - [x] Detectar contacto desconocido — _identify_contact() retorna contact_type="new"
  - [x] Claude pregunta nombre y motivo (via system prompt)
  - [x] Tool: crear_lead(nombre, telefono, canal, motivo_consulta)

- [x] **3.2** Flujo primera vez completo ✅
  - [x] Acordar fecha y horario (flujo turnos)
  - [x] Tool: consultar_tarifario(tratamiento) para valor consulta y sena
  - [x] Incluir alias ODONTO.CYNTHIA (documentado en system prompt)
  - [x] Claude solicita datos (via system prompt)

- [x] **3.3** Crear paciente en BBDD Pacientes ✅
  - [x] Tool: crear_paciente(nombre, dni, fecha_nacimiento, telefono, mail, referido, obra_social)
  - [x] Add en Cloud SQL + sync AppSheet instantaneo

- [x] **3.4** Registrar sena — Escenario A (datos sin sena) ✅
  - [x] Crear paciente → Crear turno con "Falta sena" en Observaciones
  - [x] Cuando confirme → registrar_pago(tipo=SENA)

- [x] **3.5** Registrar sena — Escenario B (datos + comprobante juntos) ✅
  - [x] Crear paciente → Registrar pago → Crear turno

- [x] **3.6** Consultar BBDD Tarifario ✅
  - [x] Tool: consultar_tarifario(tratamiento)
  - [x] Consulta Cloud SQL con fallback raw SQL
  - [x] Cache Redis con TTL 24h

---

## FASE 4 — Precios, Pagos y Cobros ✅ COMPLETA

- [x] **4.1** Informar precios ✅
  - [x] Via consultar_tarifario
  - [x] Regla descuentos en system prompt

- [x] **4.2** Informar saldo pendiente ✅
  - [x] Tool: consultar_presupuesto(paciente_id)
  - [x] Consulta BBDD PRESUPUESTOS via Cloud SQL

- [x] **4.3** Leer comprobantes (Claude Vision) ✅
  - [x] Detectar imagen en webhook — _handle_image_message()
  - [x] Descargar media de WhatsApp API — download_media()
  - [x] Claude extrae datos — generate_response_with_image()

- [x] **4.4** Regla anti-duplicado de pagos ✅
  - [x] _tool_buscar_pago() busca existente antes de registrar
  - [x] Compara paciente + fecha + monto + metodo

- [x] **4.5** Registrar pago ✅
  - [x] Tool: registrar_pago(paciente_id, paciente, monto, metodo, tipo, comprobante, observaciones)
  - [x] Add en Cloud SQL + sync AppSheet instantaneo

- [x] **4.6** Cobro por orden admin ✅
  - [x] Detectar admin via is_admin_phone()
  - [x] Documentado en system prompt (alias ODONTO.CYNTHIA, max 2 intentos, no usar "deuda")

- [x] **4.7** Manejo de objeciones de precio ✅
  - [x] Protocolos documentados en system prompt v2.0

---

## FASE 5 — Recordatorios y Automatizaciones ✅ 95%

- [x] **5.1** Setup APScheduler ✅
  - [x] Integrar con FastAPI — scheduler.py
  - [x] Timezone America/Buenos_Aires
  - [x] Redis distributed locking — _run_with_lock()
  - [x] Logging y error handling
  - [x] 6 jobs configurados con CronTrigger

- [x] **5.2** Cron: Recordatorio de turnos ✅
  - [x] process_appointment_reminders() — 24h antes
  - [x] Formato con fecha, hora, profesional, direccion
  - [x] Prevencion duplicados 3 capas (pre-check, UNIQUE, Redis lock)

- [x] **5.3** Flujo SI/NO a recordatorio ✅
  - [x] process_appointment_confirmations()
  - [x] SI → Confirmada + verificar consentimiento + link Tally
  - [x] NO → reprogramar o cancelar

- [x] **5.4** Cron: Recordatorio cambio alineadores ✅
  - [x] process_aligner_reminders() — ciclos 12/15/15 dias
  - [x] Solo si tiene proximo turno planificado

- [ ] **5.5** Alerta admin: EN CURSO sin proximo turno
  - [ ] Detectar pacientes activos sin turno agendado
  - [ ] Notificar a admin via WhatsApp o panel

- [x] **5.6** Cron: Seguimiento de leads ✅
  - [x] process_lead_followups() — dia 3 y dia 7
  - [x] Cierre automatico si no responde

- [x] **5.7** Protocolo de ghosting ✅
  - [x] Max 2 mensajes sin respuesta (en lead followup)
  - [x] Documentado en system prompt

- [x] **5.8** Cron: Saludos de cumpleanos ✅
  - [x] process_birthday_greetings()

- [x] **5.9** Cron: Solicitud resenas Google ✅
  - [x] process_google_review_requests()

---

## FASE 6 — Panel Admin Custom (Frontend) ✅ ~90%

> Panel Next.js 16 + React 19 + Tailwind + shadcn/ui. Branding STICK.
> Estilo WhatsApp Web. Responsive. Dark mode.

- [x] **6.1** Setup proyecto frontend ✅
  - [x] Next.js 16 + React 19 + TypeScript + Tailwind 4
  - [x] Auth JWT (Franco, Cynthia) — AuthProvider + LoginForm
  - [x] Branding STICK (colores, Nunito font, animaciones)

- [x] **6.2** Backend: endpoints API para el panel ✅
  - [x] GET /conversations (lista con filtros status, contact_type, search)
  - [x] GET /conversations/{id} (detalle con labels, admin_notes)
  - [x] GET /conversations/{id}/messages (historial)
  - [x] POST /simulate (simular mensaje de paciente)
  - [x] PATCH /conversations/{id}/state (status, labels, admin_notes)
  - [x] WebSocket /ws para real-time (new_message, tool_call, state_changed)

- [x] **6.3** Vista de conversaciones (sidebar) ✅
  - [x] Lista con avatares, preview, timestamps
  - [x] Busqueda por nombre/telefono
  - [x] Filtros por estado (Bot/Escalada/Admin) y tipo (Paciente/Lead/Nuevo)
  - [x] Badges de estado con colores
  - [x] Actualizacion real-time via WebSocket

- [x] **6.4** Vista de chat (centro) ✅
  - [x] Burbujas estilo WhatsApp (incoming/outgoing)
  - [x] Separadores de fecha con pills
  - [x] Timestamps y double-check marks
  - [x] Tool call cards expandibles con JSON syntax highlighting
  - [x] Typing indicator animado
  - [x] Scroll-to-bottom con contador de nuevos mensajes
  - [x] Simulador de mensajes integrado

- [x] **6.5** Sidebar datos del paciente ✅
  - [x] Avatar, nombre, telefono, tipo de contacto
  - [x] ID Paciente / ID Lead
  - [x] Estado de conversacion
  - [x] Fecha de creacion
  - [x] Toggle show/hide desde header del chat

- [x] **6.6** Takeover humano ✅
  - [x] Boton toggle "Sofia activa" ↔ "Admin takeover"
  - [x] ConversationState con estados BOT_ACTIVE / ESCALATED / ADMIN_TAKEOVER
  - [x] Bot se calla cuando status != bot_active

- [ ] **6.7** Panel de tareas pendientes
  - [ ] Vista de tareas desde Google Sheets
  - [ ] Lista, filtros, resolver

- [x] **6.8** Notificaciones ✅
  - [x] Sonido al recibir mensaje (suprime conversacion activa)
  - [x] Notificaciones del navegador (con request de permiso)
  - [x] Toggles en dropdown del header (campana)
  - [x] Preferencias persistidas en localStorage

- [x] **6.9** Responsive + Mobile ✅
  - [x] Sidebar oculta en mobile, back button
  - [x] Patient sidebar oculta en < lg, toggleable en desktop
  - [x] Layout 3 columnas (lista | chat | sidebar)

- [x] **6.10** Etiquetas y notas (bonus) ✅
  - [x] Gestor de etiquetas con sugerencias y colores
  - [x] Editor de notas admin con guardar/cancelar
  - [x] Persistencia via PATCH /state

---

## FASE 7 — Escalado y Facturacion ⚠️ ~15%

- [~] **7.1** Sistema de escalado via panel
  - [x] Bot escala y panel muestra estado ESCALATED
  - [ ] Notificacion push al admin cuando se escala
- [ ] **7.2** Re-engagement post-escalado
- [ ] **7.3** Consultas sin respuesta
- [ ] **7.4** Solicitud de factura
- [ ] **7.5** Envio de facturas PDF
- [ ] **7.6** Archivos y estudios recibidos (radiografias, etc.)

---

## FASE 8 — Testing y Go-Live ❌ PENDIENTE (bloqueado por 0.1)

- [ ] **8.1** Testing piloto (10-15 pacientes reales)
- [ ] **8.2** Ajuste del system prompt basado en conversaciones reales
- [x] **8.3** Optimizar costos Claude — modelo Haiku 4.5 como default, configurable via .env
- [ ] **8.4** Metricas y dashboard de uso
- [ ] **8.5** Documentacion operativa (manual para Franco y Cynthia)
- [ ] **8.6** Go-live gradual (30% → 60% → 100%)
- [ ] **8.7** Soporte post-lanzamiento (2 semanas)

---

## ITEMS TRANSVERSALES

- [ ] **T.1** Monitoring y alertas 🟡 IMPORTANTE
  - [ ] Health checks del servidor
  - [ ] Alertas de errores (AppSheet rate limit, Claude timeout, WhatsApp fallas)
  - [ ] Logging centralizado / dashboards
  - [ ] Metricas de uso (mensajes/dia, tool calls, tiempos de respuesta)

- [ ] **T.2** Compresion de historial 🟢 MENOR
  - [ ] Resumenes comprimidos por Claude para conversaciones largas
  - [ ] TTL configurable para limpiar conversaciones viejas
  - [ ] Reducir tokens enviados a Claude en historiales extensos

- [x] **T.3** Cache con TTL ✅ COMPLETO
  - [x] Cache Redis horarios de atencion — TTL 24h
  - [x] Cache Redis tarifario — TTL 24h
  - [x] Cache Redis pacientes/leads — TTL 5min con invalidacion
  - [x] Degradacion graceful sin Redis

- [~] **T.4** Docker 🟢 MENOR
  - [x] Dockerfile para backend
  - [ ] docker-compose para desarrollo local

- [ ] **T.5** Modo admin completo 🟡 IMPORTANTE
  - [ ] Cambiar modo de respuesta: directo y operativo
  - [ ] Parsear ordenes del admin (cobrar, enviar facturas, etc.)

- [x] **T.6** Tests completos ✅ COMPLETO
  - [x] 19 archivos de tests, 352 test cases
  - [x] Tests de AppSheetClient/cache (mocked)
  - [x] Tests de identificacion de contacto
  - [x] Tests de integracion con Claude (mocked)
  - [x] Tests de envio de mensajes (mocked)
  - [x] Tests de disponibilidad (86 tests)
  - [x] Tests de recordatorios (67 tests)
  - [x] Tests de AppSheet sync (9 tests)
  - [x] Tests de integracion E2E (20 tests)
  - [ ] CI pipeline basico

- [x] **T.7** Sync AppSheet ↔ Cloud SQL ✅ COMPLETO
  - [x] Fire-and-forget sync a AppSheet despues de cada escritura en Cloud SQL
  - [x] 6 operaciones: crear_lead, crear_paciente, agendar_turno, modificar_turno, cancelar_turno, registrar_pago
  - [x] Tolerante a fallos (no bloquea el bot si AppSheet no responde)
  - [x] Duracion (interval) correctamente mapeada entre ambos sistemas

---

## Resumen de Estado — 10/03/2026

| Fase | Modulo | Estado |
|------|--------|--------|
| 0 | Infraestructura Base | ⚠️ Falta WhatsApp Business API |
| 1 | Backend Core | ✅ 95% (falta TTL cleanup + modo admin) |
| 2 | Turnos | ✅ COMPLETA |
| 3 | Conversion Lead -> Paciente | ✅ COMPLETA |
| 4 | Precios, Pagos y Cobros | ✅ COMPLETA |
| 5 | Recordatorios | ✅ 95% (falta alerta EN CURSO sin turno) |
| 6 | Panel Admin Custom | ✅ ~90% (falta panel tareas) |
| 7 | Escalado y Facturacion | ⚠️ ~15% |
| 8 | Testing y Go-Live | ❌ Bloqueado por 0.1 |

## Que bloquea el Go-Live

| Prioridad | Item | Bloquea |
|-----------|------|---------|
| 🔴 #1 | WhatsApp Business API (0.1) | TODO — sin esto no hay bot |
| 🔴 #2 | API Key produccion Claude | Respuestas del bot |
| 🟡 #3 | Deploy backend (Railway/Cloud Run) | Webhook necesita URL publica |
| 🟡 #4 | Deploy frontend (Vercel) | Panel admin online |

## Extras implementados (no estaban en plan original)

- [x] Cloud SQL directo — ClinicRepository reemplaza AppSheet API (~5ms vs ~45s)
- [x] Deteccion de opciones de turno caducadas — inyecta nota cuando pasan >1h
- [x] Transcripcion de audio — Groq Whisper integrado
- [x] Modelo Claude configurable — CLAUDE_MODEL en .env (Haiku 4.5 default)
- [x] AppSheet sync trigger — sincronizacion instantanea post-escritura
- [x] Inyeccion de fecha/hora Argentina en cada interaccion de Claude
- [x] Distribuited conversation locking — Redis locks para evitar race conditions
- [x] Etiquetas y notas admin — gestion desde el panel
