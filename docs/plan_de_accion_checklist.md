# Plan de Accion — Bot Sofia STICK
# Checklist v3 — Actualizado 2026-03-06 (estado real del codigo)
# Python + React (sin n8n, sin Chatwoot — Panel Admin custom)

**Stack:** Python (FastAPI) + React (Next.js) + PostgreSQL + Claude API + AppSheet API + Google Sheets

**Leyenda:** [x] = implementado y funcionando | [~] = parcial | [ ] = pendiente

---

## FASE 0 — Infraestructura Base ✅ (parcial)

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
  - [ ] Setup Docker + docker-compose para desarrollo local
  - [x] Configurar logging estructurado

- [x] **0.3** Configurar PostgreSQL ✅
  - [x] Instalar/configurar PostgreSQL (Neon — sa-east-1 Sao Paulo)
  - [x] Disenar schema: conversaciones, mensajes, estados de flujo
  - [x] Crear migraciones con Alembic — migracion inicial aplicada
  - [x] Testear conexion desde FastAPI — 5 tablas verificadas

- [~] **0.4** Configurar credenciales externas
  - [x] AppSheet API Key — configurada en .env
  - [x] Google Sheets service account (Franco.json) — configurada en .env
  - [~] Claude API Key (Anthropic) — falta clave de produccion
  - [ ] WhatsApp Business API Token — 🔴 bloqueante

- [x] **0.5** Crear Google Sheet "Tareas Pendientes WhatsApp" ✅
  - [x] Crear spreadsheet con columnas documentadas (A-L)
  - [x] Configurar dropdowns: Tipo, Prioridad, Estado
  - [x] Compartir con service account (Franco.json)
  - [x] Verificar acceso desde Python — client implementado + test OK

- [ ] **0.6** Test de conectividad end-to-end 🔴 CRITICO
  - [ ] Recibir webhook de WhatsApp en FastAPI
  - [ ] Llamar AppSheet API y recibir datos reales
  - [ ] Llamar Claude API y recibir respuesta real
  - [ ] Enviar respuesta de vuelta por WhatsApp
  - [ ] Verificar ciclo completo: mensaje -> proceso -> respuesta

---

## FASE 1 — Backend Core: Identificacion + IA ✅ (2 items parciales)

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

- [x] **1.3** Identificar contacto ✅
  - [x] Extraer telefono del mensaje (formato +5491112345678) — phone.py completo
  - [x] Buscar en BBDD Pacientes via AppSheet → _identify_contact()
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
  - [x] Enviar contexto: patient_context inyectado en system prompt
  - [x] generate_response_with_image para comprobantes (Vision)

- [x] **1.5** Memoria conversacional (PostgreSQL) ✅
  - [x] Tabla conversations: id, phone, patient_id, created_at, updated_at
  - [x] Tabla messages: id, conversation_id, role, content, timestamp
  - [x] Almacenar cada mensaje entrante y saliente
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

- [~] **1.8** Tests unitarios del core 🔴 CRITICO
  - [x] Tests de webhook handler (payloads reales de Meta) — 4 tests
  - [ ] Tests de AppSheetClient (mocked)
  - [ ] Tests de identificacion de contacto
  - [ ] Tests de integracion con Claude (mocked)
  - [ ] Tests de envio de mensajes (mocked)
  - [ ] CI pipeline basico

---

## FASE 2 — Modulo Turnos ✅ COMPLETA

- [x] **2.1** Consultar horarios de atencion ✅
  - [x] Tool: consultar_horarios → leer "LISTA O | HORARIOS DE ATENCION" via AppSheet
  - [x] Parsear horarios por dia y profesional — _parse_horarios() en availability.py
  - [ ] Cache en memoria con TTL (consulta AppSheet cada vez)

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
  - [x] Crear turno en BBDD SESIONES via AppSheet (Add)
  - [x] Payload completo: ID PACIENTE, Paciente, Tratamiento, Fecha, Hora, Profesional, Estado=Planificada

- [x] **2.4** Agendar turno de urgencia ✅
  - [x] Via buscar_disponibilidad con semanas=1, tipo_turno="Urgencia"
  - [x] Si no hay opciones: crear_tarea_pendiente tipo Urgencia, prioridad Alta

- [x] **2.5** Reprogramar turno ✅
  - [x] Tool: buscar_turno_paciente(paciente_id) → turno actual
  - [x] Tool: modificar_turno(turno_id, fecha, hora, profesional, observaciones)
  - [x] Edit en BBDD SESIONES via AppSheet

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
  - [x] Add en BBDD PACIENTES via AppSheet

- [x] **3.4** Registrar sena — Escenario A (datos sin sena) ✅
  - [x] Crear paciente → Crear turno con "Falta sena" en Observaciones
  - [x] Cuando confirme → registrar_pago(tipo=SENA)

- [x] **3.5** Registrar sena — Escenario B (datos + comprobante juntos) ✅
  - [x] Crear paciente → Registrar pago → Crear turno

- [x] **3.6** Consultar BBDD Tarifario ✅
  - [x] Tool: consultar_tarifario(tratamiento)
  - [x] Consulta LISTA A I TIPO TRATAMIENTOS via AppSheet
  - [ ] Cache con TTL corto (consulta AppSheet cada vez)

---

## FASE 4 — Precios, Pagos y Cobros ✅ COMPLETA

- [x] **4.1** Informar precios ✅
  - [x] Via consultar_tarifario
  - [x] Regla descuentos en system prompt

- [x] **4.2** Informar saldo pendiente ✅
  - [x] Tool: consultar_presupuesto(paciente_id)
  - [x] Consulta BBDD PRESUPUESTOS via AppSheet

- [x] **4.3** Leer comprobantes (Claude Vision) ✅
  - [x] Detectar imagen en webhook — _handle_image_message()
  - [x] Descargar media de WhatsApp API — download_media()
  - [x] Claude extrae datos — generate_response_with_image()

- [x] **4.4** Regla anti-duplicado de pagos ✅
  - [x] _tool_buscar_pago() busca existente antes de registrar
  - [x] Compara paciente + fecha + monto + metodo

- [x] **4.5** Registrar pago ✅
  - [x] Tool: registrar_pago(paciente_id, paciente, monto, metodo, tipo, comprobante, observaciones)
  - [x] Add en BBDD PAGOS via AppSheet

- [x] **4.6** Cobro por orden admin ✅
  - [x] Detectar admin via is_admin_phone()
  - [x] Documentado en system prompt (alias ODONTO.CYNTHIA, max 2 intentos, no usar "deuda")

- [x] **4.7** Manejo de objeciones de precio ✅
  - [x] Protocolos documentados en system prompt v2.0

---

## FASE 5 — Recordatorios y Automatizaciones ✅ COMPLETA

- [x] **5.1** Setup APScheduler ✅
  - [x] Integrar con FastAPI — scheduler.py (209 lineas)
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

- [x] **5.8** Cron: Saludos de cumpleanos ✅ (bonus, no estaba en plan original)
  - [x] process_birthday_greetings()

- [x] **5.9** Cron: Solicitud resenas Google ✅ (bonus, no estaba en plan original)
  - [x] process_google_review_requests()

---

## FASE 6 — Panel Admin Custom (Frontend) ❌ PENDIENTE

> Panel de alta calidad desarrollado por nosotros. NO Chatwoot.
> Aca es donde llegan las escalaciones y el takeover humano.

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
  - [ ] La escalacion llega ACA (no a Chatwoot, no a la nada)

- [ ] **6.7** Panel de tareas pendientes
  - [ ] Lista, filtros, resolver

- [ ] **6.8** Notificaciones
  - [ ] Web Push + sonido + badge

- [ ] **6.9** Responsive + Mobile

---

## FASE 7 — Escalado y Facturacion ❌ PENDIENTE

- [ ] **7.1** Sistema de escalado via panel
  - [ ] Conectar escalacion del bot → notificacion en panel admin
  - [ ] Hoy la escalacion notifica pero NO llega a nadie
- [ ] **7.2** Re-engagement post-escalado
- [ ] **7.3** Consultas sin respuesta
- [ ] **7.4** Solicitud de factura
- [ ] **7.5** Envio de facturas PDF
- [ ] **7.6** Archivos y estudios recibidos (radiografias, etc.)

---

## FASE 8 — Testing y Go-Live ❌ PENDIENTE

- [ ] **8.1** Testing piloto (10-15 pacientes reales)
- [ ] **8.2** Ajuste del system prompt basado en conversaciones reales
- [ ] **8.3** Optimizar costos Claude (prompt caching, modelo menor para tareas simples)
- [ ] **8.4** Metricas y dashboard de uso
- [ ] **8.5** Documentacion operativa (manual para Franco y Cynthia)
- [ ] **8.6** Go-live gradual (30% → 60% → 100%)
- [ ] **8.7** Soporte post-lanzamiento (2 semanas)

---

## ITEMS TRANSVERSALES (no asignados a una fase)

- [ ] **T.1** Monitoring y alertas 🟡 IMPORTANTE
  - [ ] Health checks del servidor
  - [ ] Alertas de errores (AppSheet rate limit, Claude timeout, WhatsApp fallas)
  - [ ] Logging centralizado / dashboards
  - [ ] Metricas de uso (mensajes/dia, tool calls, tiempos de respuesta)

- [ ] **T.2** Compresion de historial 🟢 MENOR
  - [ ] Resumenes comprimidos por Claude para conversaciones largas
  - [ ] TTL configurable para limpiar conversaciones viejas
  - [ ] Reducir tokens enviados a Claude en historiales extensos

- [ ] **T.3** Cache con TTL para AppSheet 🟢 MENOR
  - [ ] Cache horarios de atencion (cambian poco)
  - [ ] Cache tarifario (cambia poco)
  - [ ] Reduce llamadas a AppSheet y mejora tiempos de respuesta

- [ ] **T.4** Docker 🟢 MENOR
  - [ ] docker-compose para desarrollo local

- [ ] **T.5** Modo admin completo 🟡 IMPORTANTE
  - [ ] Cambiar modo de respuesta: directo y operativo
  - [ ] Parsear ordenes del admin (cobrar, enviar facturas, etc.)

- [ ] **T.6** Tests E2E reales 🔴 CRITICO
  - [ ] Tests con APIs reales (no mockeados)
  - [ ] Tests de AppSheetClient
  - [ ] Tests de identificacion de contacto
  - [ ] Tests de integracion con Claude
  - [ ] Tests de envio de mensajes
  - [ ] CI pipeline basico

- [ ] **T.7** Verificar compatibilidad AppSheet ↔ Cloud SQL 🟡 IMPORTANTE
  - [ ] Crear turno manual desde AppSheet → verificar que Duracion (interval) se guarda bien en Cloud SQL
  - [ ] Verificar que Horario Finalizacion se calcula correctamente en AppSheet al crear turno
  - [ ] Verificar que el bot lee correctamente turnos creados desde AppSheet (duracion, hora_fin)
  - [ ] Verificar que AppSheet lee correctamente turnos creados por el bot
  - [ ] Test bidireccional: crear turno en AppSheet → bot calcula disponibilidad sin ofrecer ese slot

---

## Resumen de Estado

| Fase | Modulo | Estado |
|------|--------|--------|
| 0 | Infraestructura Base | ✅ Parcial (falta WhatsApp API + E2E test) |
| 1 | Backend Core | ✅ Parcial (falta admin mode + tests) |
| 2 | Turnos | ✅ COMPLETA |
| 3 | Conversion Lead -> Paciente | ✅ COMPLETA |
| 4 | Precios, Pagos y Cobros | ✅ COMPLETA |
| 5 | Recordatorios | ✅ COMPLETA (falta alerta EN CURSO sin turno) |
| 6 | Panel Admin Custom | ❌ PENDIENTE |
| 7 | Escalado y Facturacion | ❌ PENDIENTE |
| 8 | Testing y Go-Live | ❌ PENDIENTE |

## Prioridades Pendientes

| Prioridad | Item | Bloquea |
|-----------|------|---------|
| 🔴 Critico | WhatsApp Business API (0.1) | Todo el sistema |
| 🔴 Critico | Tests E2E reales (T.6) | Confianza para go-live |
| 🔴 Critico | Anthropic API Key produccion (0.4) | Todo el sistema |
| 🟡 Importante | Panel Admin Custom (Fase 6) | Escalacion + takeover |
| 🟡 Importante | Monitoring y alertas (T.1) | Operacion en produccion |
| 🟡 Importante | Modo admin completo (T.5) | Ordenes de Franco/Cynthia |
| 🟡 Importante | Escalado via panel (7.1) | Hoy no llega a nadie |
| 🟢 Menor | Compresion historial (T.2) | Costos en conversaciones largas |
| 🟢 Menor | Facturacion / PDF (7.4-7.5) | Post go-live |
| 🟢 Menor | Cache AppSheet (T.3) | Performance |
| 🟢 Menor | Docker (T.4) | Solo dev |
