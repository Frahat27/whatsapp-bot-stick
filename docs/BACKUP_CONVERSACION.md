# Backup de Conversación — Bot Sofía STICK
# Fecha: 4 de Marzo de 2026
# Propósito: Retomar desarrollo en PC nueva sin perder contexto

---

## INSTRUCCIONES PARA RETOMAR

Cuando arranques en la PC nueva, copiar toda la carpeta `Whatsapp BOT - STICK` y pegá este mensaje a Claude Code:

> Estoy retomando el desarrollo del Bot Sofía para STICK. Leé el archivo `BACKUP_CONVERSACION.md` en la raíz del proyecto para entender el contexto completo. Después leé `MEMORY.md` en `.claude/projects/.../memory/`. Quedamos en el Paso 3 de la Fase 0: crear la base de datos PostgreSQL en Neon. Después de eso queda hacer Alembic migrations, test end-to-end, y primer commit. Luego empezamos Fase 1.

---

## RESUMEN DEL PROYECTO

**¿Qué es?** Bot de WhatsApp ("Sofía") para la clínica odontológica STICK. Atiende pacientes, agenda turnos, cobra pagos, escala a humanos. Debe ser indistinguible de una persona real.

**Stack definido:**
- Backend: **Python + FastAPI**
- Frontend admin (Fase 6): **React + Next.js + TypeScript + Tailwind**
- Base de datos: **PostgreSQL** (Neon, cloud) — memoria conversacional
- Cache (futuro): **Redis** (Upstash) — rate limiting AppSheet
- IA: **Claude API** (Anthropic) con tool calling
- Datos clínica: **AppSheet** (16 tablas, API REST v2)
- Tareas pendientes: **Google Sheets**
- Mensajería: **WhatsApp Business API** (Meta Cloud API)

**Costo estimado:** ~$20-45/mes

---

## QUÉ SE HIZO (Pre-fase + Fase 0)

### Pre-fase (sesiones anteriores) ✅
- System prompt Sofía v2.0 completo (691 líneas)
- Mapa de operaciones API v3.0 (25 operaciones + 14 cadenas)
- Tests API exhaustivos contra AppSheet real (Find, Edit, Add, Delete)
- Info tratamientos documentada
- Estructura Google Sheets documentada
- Protocolos de quejas extraídos de PDF de 62 páginas

### Fase 0 — Infraestructura Base (esta sesión) ✅ (casi completa)

| Paso | Descripción | Estado |
|---|---|---|
| 0 | Actualizar API key + alinear MEMORY.md | ✅ |
| 1 | Scaffold proyecto (git init, carpetas, archivos) | ✅ |
| 2 | Config y .env (pydantic-settings) | ✅ |
| 3 | Setup PostgreSQL (Neon) en la nube | ⏳ PENDIENTE |
| 4 | Modelos DB + Alembic config | ✅ |
| 5 | Utilidades (phone, dates, logging, data_loader) | ✅ |
| 6 | FastAPI app + endpoints (health, webhook) | ✅ |
| 7 | AppSheet client (rate limiting, retry) | ✅ |
| 8 | Stubs clientes (WhatsApp, Claude, GSheets) | ✅ |
| 9 | Conversation manager skeleton | ✅ |
| 10 | Tests (30/30 pasan) | ✅ |
| 11 | Test conectividad end-to-end | ⏳ PENDIENTE (necesita Neon DB) |

---

## PRÓXIMOS PASOS INMEDIATOS

### Paso 3: Crear Neon PostgreSQL
1. Ir a [neon.tech](https://neon.tech), crear cuenta
2. Crear proyecto: `stick-sofia-bot`, región São Paulo
3. Copiar connection string y agregar `+asyncpg`:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.sa-east-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Crear `.env` en `whatsapp-bot-stick/` con ese DATABASE_URL

### Paso 11: Test end-to-end
1. `cd whatsapp-bot-stick`
2. Activar venv: `venv\Scripts\activate`
3. `alembic upgrade head` → crea las 4 tablas en Neon
4. `uvicorn src.main:app --reload` → levantar server
5. Ir a `http://localhost:8000/health` → debe mostrar `"database": "connected"`
6. Ir a `http://localhost:8000/docs` → Swagger UI
7. Probar AppSheet Find real (necesita API key en .env)

### Después: Primer commit
- `git add` todos los archivos
- Commit con todo el scaffold

### Después: Fase 1 — Backend Core
- Webhook handler completo
- AppSheet client con cache
- Claude AI con tool calling (system prompt + tools)
- Memoria conversacional real (guardar/recuperar mensajes)
- Detección admin
- Tests de integración

---

## CREDENCIALES Y CONFIGURACIÓN

### AppSheet
- **App ID:** `cfc7574f-e4ec-4cf4-8a63-f04d84d347d4`
- **API Key:** `V2-vnqyX-ZhkYA-kCDLU-narl7-gMXiz-h9vit-L8hNP-I037X`
- **Owner:** consultorio@sticksmile.com
- **User:** franco.hatzerian@kavak.com
- **15 tablas verificadas** (detalles en `appsheet-api.md`)

### Admin phones
- Franco: `1123266671` (normalizado 10 dígitos)
- Cynthia: `1171342438`

### Google Sheets — Tareas Pendientes
- Sheet ID: `1Ql5Li8PdpZGg7obxmEjoyH1h-rmjQw0F_WOnwn34GRU`
- Service account: `credentials/franco.json`

### Lo que FALTA configurar en .env
- `DATABASE_URL` → crear cuenta en Neon
- `WHATSAPP_TOKEN` → configurar WhatsApp Business API
- `WHATSAPP_PHONE_NUMBER_ID` → de Meta Business
- `WHATSAPP_VERIFY_TOKEN` → string custom que vos elegís
- `WHATSAPP_APP_SECRET` → de Meta Business
- `ANTHROPIC_API_KEY` → de console.anthropic.com
- `REDIS_URL` → opcional, para futuro

---

## ESTRUCTURA DEL PROYECTO

```
Whatsapp BOT - STICK/                      ← Carpeta raíz de documentación
├── BACKUP_CONVERSACION.md                 ← ESTE ARCHIVO
├── plan_de_accion_checklist.md            ← Plan maestro (8 fases, 24 semanas)
├── sofia_system_prompt.md                 ← System prompt Sofía v2.0
├── tratamientos_stick.md                  ← Base de conocimiento tratamientos
├── api_calls_map.md                       ← 25 operaciones AppSheet mapeadas
├── google_sheets_estructura.md            ← Columnas de Tareas Pendientes
├── data/
│   └── protocolos_quejas.md               ← Protocolo manejo de quejas
│
├── whatsapp-bot-stick/                    ← PROYECTO PYTHON (código)
│   ├── .env.example                       ← Template de variables de entorno
│   ├── .gitignore
│   ├── requirements.txt                   ← Dependencias (ya instaladas en venv/)
│   ├── alembic.ini                        ← Config Alembic
│   ├── venv/                              ← Virtual environment (recrear en PC nueva)
│   ├── alembic/
│   │   ├── env.py                         ← Async migrations config
│   │   └── versions/                      ← Migraciones (vacío, generar con Alembic)
│   ├── data/                              ← Copia de docs para el bot
│   │   ├── sofia_system_prompt.md
│   │   ├── tratamientos_stick.md
│   │   └── protocolos_quejas.md
│   ├── src/
│   │   ├── main.py                        ← FastAPI app + lifespan
│   │   ├── config.py                      ← pydantic-settings (lee .env)
│   │   ├── dependencies.py
│   │   ├── api/
│   │   │   ├── router.py                  ← Router principal
│   │   │   ├── health.py                  ← GET /health
│   │   │   └── webhook.py                 ← GET+POST /webhook (WhatsApp)
│   │   ├── models/
│   │   │   ├── base.py                    ← DeclarativeBase + TimestampMixin
│   │   │   ├── conversation.py            ← Tabla conversations
│   │   │   ├── message.py                 ← Tabla messages
│   │   │   └── conversation_state.py      ← Tablas states + summaries
│   │   ├── schemas/
│   │   │   ├── webhook.py                 ← WhatsApp payload parsing
│   │   │   └── message.py                 ← Response schemas
│   │   ├── clients/
│   │   │   ├── appsheet.py                ← ⭐ CRÍTICO — CRUD con rate limiting
│   │   │   ├── whatsapp.py                ← Stub (implementar Fase 1)
│   │   │   ├── claude_ai.py               ← Stub (implementar Fase 1)
│   │   │   └── google_sheets.py           ← Stub (implementar Fase 1)
│   │   ├── services/
│   │   │   └── conversation_manager.py    ← Orquestador central (skeleton)
│   │   ├── db/
│   │   │   ├── session.py                 ← AsyncSession factory (lazy init)
│   │   │   └── repository.py              ← CRUD genérico
│   │   └── utils/
│   │       ├── phone.py                   ← Normalizar teléfonos argentinos
│   │       ├── dates.py                   ← MM/DD/YYYY para AppSheet
│   │       ├── logging_config.py          ← structlog (JSON prod, color dev)
│   │       └── data_loader.py             ← Cargar .md para Claude context
│   └── tests/
│       ├── conftest.py                    ← Fixtures (webhook payloads)
│       ├── test_phone_utils.py            ← 14 tests teléfono
│       ├── test_date_utils.py             ← 12 tests fechas
│       └── test_health.py                 ← 4 tests webhook parsing
```

---

## DECISIONES TÉCNICAS TOMADAS

1. **n8n descartado** → demasiada lógica custom para workflow visual, Python es mejor
2. **Chatwoot descartado** → overkill para 2-3 admins, panel custom en Next.js (Fase 6)
3. **No RAG** → knowledge base cabe en context window de Claude (~5-10K tokens)
4. **Memoria largo plazo** → Opción A: resúmenes comprimidos por Claude (no RAG sobre historial)
5. **Cloud-first** → Neon PostgreSQL + Upstash Redis, sin Docker durante desarrollo
6. **Tres capas de contexto para Claude:**
   - Fijo: system prompt + tratamientos + protocolos
   - Dinámico por conversación: datos paciente de AppSheet
   - Dinámico por mensaje: historial chat de PostgreSQL
7. **AppSheet rate limiting** → ~45s entre requests, 200 vacío = rate limited, retry con backoff
8. **BBDD PACIENTES Edit con keys "ANT" legacy** → no funciona, workaround: GS-1 tarea para humano

---

## ARCHIVOS DE MEMORIA DE CLAUDE CODE

Estos archivos están en `.claude/projects/.../memory/` y Claude Code los lee automáticamente:

- **MEMORY.md** — Contexto general del proyecto (stack, fases, estado)
- **appsheet-api.md** — Referencia técnica AppSheet (12 reglas, 15 tablas, tests)
- **project-details.md** — Detalles extra (si existe)

---

## PLAN MAESTRO (8 fases, ~24 semanas)

| Fase | Módulo | Semanas | Estado |
|---|---|---|---|
| 0 | Infraestructura Base | 1-2 | ✅ 90% (falta Neon + e2e test) |
| 1 | Backend Core (webhook, Claude, tools, memoria) | 3-5 | ⏳ Próximo |
| 2 | Turnos (agendar, reprogramar, cancelar) | 6-8 | |
| 3 | Conversión Lead → Paciente | 9-10 | |
| 4 | Precios, Pagos y Cobros | 11-13 | |
| 5 | Recordatorios (APScheduler) | 14-15 | |
| 6 | Panel Admin Frontend (Next.js + React) | 16-18 | |
| 7 | Escalado y Facturación | 19-20 | |
| 8 | Testing y Go-Live | 21-24 | |

---

## SETUP EN PC NUEVA

```bash
# 1. Copiar toda la carpeta "Whatsapp BOT - STICK" a la nueva PC

# 2. Instalar Python 3.13+ si no está
python --version

# 3. Ir al proyecto
cd "Whatsapp BOT - STICK/whatsapp-bot-stick"

# 4. Recrear virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 5. Crear .env (copiar de .env.example y llenar)
copy .env.example .env
# Editar .env con las credenciales reales

# 6. Verificar que todo funciona
python -m pytest tests/ -v
# Debe dar: 30 passed

# 7. Verificar que la app carga
python -c "from src.main import app; print(app.title)"
# Debe imprimir: Bot Sofía — STICK Alineadores
```

---

## NOTAS IMPORTANTES

- El **venv/** NO se copia entre PCs, se recrea con `python -m venv venv && pip install -r requirements.txt`
- La **API key de AppSheet** ya está en `appsheet-api.md` (sección Seguridad)
- Los **tests no necesitan DB** — corren sin .env configurado
- El **AppSheet client** (`src/clients/appsheet.py`) es el archivo más importante — implementa las 12 reglas de la API
- **No hay commits todavía** — el git está inicializado pero sin commits
- Las **migraciones de Alembic** no están generadas aún — se generan después de conectar Neon
