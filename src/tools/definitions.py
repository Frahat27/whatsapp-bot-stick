"""
Definiciones de Tools para Claude AI (formato Anthropic).

Cada tool tiene:
- name: identificador único
- description: qué hace (Claude lo usa para decidir cuándo llamarla)
- input_schema: JSON Schema de los parámetros

Estas tools se pasan al parámetro `tools` de messages.create().
"""

# =============================================================================
# 1. IDENTIFICACIÓN DE CONTACTO
# =============================================================================

BUSCAR_PACIENTE = {
    "name": "buscar_paciente",
    "description": (
        "Busca un paciente en BBDD PACIENTES por número de teléfono. "
        "Retorna todos los datos del paciente si existe (nombre, DNI, "
        "fecha nacimiento, mail, estado tratamiento, etc). "
        "Usar SIEMPRE como primer paso al recibir un mensaje."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "telefono": {
                "type": "string",
                "description": "Teléfono del contacto (últimos 10 dígitos, ej: 1112345678)",
            }
        },
        "required": ["telefono"],
    },
}

BUSCAR_LEAD = {
    "name": "buscar_lead",
    "description": (
        "Busca un lead en BBDD LEADS por número de teléfono. "
        "Usar cuando buscar_paciente no encuentra resultados. "
        "Retorna nombre, canal, motivo, estado del lead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "telefono": {
                "type": "string",
                "description": "Teléfono del contacto (últimos 10 dígitos)",
            }
        },
        "required": ["telefono"],
    },
}

CREAR_LEAD = {
    "name": "crear_lead",
    "description": (
        "Registra un contacto nuevo como lead en BBDD LEADS. "
        "Usar cuando el contacto no existe ni como paciente ni como lead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre del lead (Apellido y Nombre)",
            },
            "telefono": {
                "type": "string",
                "description": "Teléfono WhatsApp",
            },
            "motivo": {
                "type": "string",
                "description": "Motivo de consulta o interés del lead",
            },
        },
        "required": ["nombre", "telefono"],
    },
}

CREAR_PACIENTE = {
    "name": "crear_paciente",
    "description": (
        "Crea un paciente nuevo en BBDD PACIENTES. "
        "IMPORTANTE: Crear SIEMPRE antes de agendar un turno. "
        "Requiere datos completos del paciente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre completo (Apellido, Nombre)",
            },
            "dni": {
                "type": "string",
                "description": "DNI o Pasaporte",
            },
            "fecha_nacimiento": {
                "type": "string",
                "description": "Fecha de nacimiento (DD/MM/YYYY)",
            },
            "telefono": {
                "type": "string",
                "description": "Teléfono WhatsApp",
            },
            "mail": {
                "type": "string",
                "description": "Email del paciente",
            },
            "referido_por": {
                "type": "string",
                "description": "Quién lo recomendó (o cómo nos encontró)",
                "default": "",
            },
            "sexo": {
                "type": "string",
                "description": "Sexo del paciente (Masculino, Femenino, Otro)",
                "default": "Otro",
            },
        },
        "required": ["nombre", "dni", "fecha_nacimiento", "telefono", "mail"],
    },
}

# =============================================================================
# 2. TURNOS
# =============================================================================

CONSULTAR_HORARIOS = {
    "name": "consultar_horarios",
    "description": (
        "Consulta los horarios de atención de la clínica desde "
        "O-HORARIOS DE ATENCION. Retorna los horarios por día y profesional. "
        "Usar antes de buscar_disponibilidad."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}

BUSCAR_DISPONIBILIDAD = {
    "name": "buscar_disponibilidad",
    "description": (
        "Busca turnos disponibles cruzando horarios de atención con "
        "turnos ya agendados en BBDD SESIONES. Busca en las próximas 3 semanas. "
        "Retorna 2-3 opciones disponibles."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "preferencia_dia": {
                "type": "string",
                "description": (
                    "Días preferidos por el paciente "
                    "(ej: 'lunes y jueves', 'cualquier dia', 'miércoles')"
                ),
                "default": "cualquier dia",
            },
            "preferencia_horario": {
                "type": "string",
                "description": (
                    "Horario preferido por el paciente "
                    "(ej: 'por la mañana', 'por la tarde', 'después de las 17')"
                ),
                "default": "cualquier horario",
            },
            "tipo_turno": {
                "type": "string",
                "description": "Tipo de turno (ej: Odontología primera vez, Control, Alineadores, Urgencia)",
                "default": "Odontología primera vez",
            },
            "semanas": {
                "type": "integer",
                "description": "Cantidad de semanas a buscar (default 3, urgencias 1)",
                "default": 3,
            },
        },
    },
}

AGENDAR_TURNO = {
    "name": "agendar_turno",
    "description": (
        "Agenda un turno nuevo en BBDD SESIONES. "
        "IMPORTANTE: El paciente debe existir en BBDD PACIENTES antes de agendar. "
        "Pacientes nuevos SIEMPRE se agendan como 'Odontología primera vez'. "
        "Endodoncia, Implantes y Cirugía NO se agendan — usar crear_tarea_pendiente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID del paciente en AppSheet (ej: ANT-15)",
            },
            "paciente_nombre": {
                "type": "string",
                "description": "Nombre completo del paciente (Apellido, Nombre)",
            },
            "fecha": {
                "type": "string",
                "description": "Fecha del turno (DD/MM/YYYY)",
            },
            "hora": {
                "type": "string",
                "description": "Hora del turno (HH:MM, formato 24h)",
            },
            "tratamiento": {
                "type": "string",
                "description": (
                    "Tipo de turno/tratamiento "
                    "(ej: Odontología primera vez, Control, Alineadores, Limpieza, Urgencia)"
                ),
            },
            "profesional": {
                "type": "string",
                "description": "Profesional asignado (ej: Cynthia Hatzerian, Ana Miño)",
            },
            "observaciones": {
                "type": "string",
                "description": (
                    "Observaciones del turno (motivo real del paciente, "
                    "'Falta seña' si corresponde, etc)"
                ),
                "default": "",
            },
        },
        "required": [
            "paciente_id", "paciente_nombre", "fecha", "hora",
            "tratamiento", "profesional",
        ],
    },
}

BUSCAR_TURNO_PACIENTE = {
    "name": "buscar_turno_paciente",
    "description": (
        "Busca los turnos (próximos y recientes) de un paciente en BBDD SESIONES. "
        "Retorna turnos Planificados, Confirmados y Realizados recientes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID del paciente en AppSheet",
            },
        },
        "required": ["paciente_id"],
    },
}

MODIFICAR_TURNO = {
    "name": "modificar_turno",
    "description": (
        "Modifica un turno existente en BBDD SESIONES "
        "(cambiar fecha, hora y/o profesional). El estado se mantiene en Planificada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "turno_id": {
                "type": "string",
                "description": "ID del turno en AppSheet",
            },
            "nueva_fecha": {
                "type": "string",
                "description": "Nueva fecha (DD/MM/YYYY)",
            },
            "nueva_hora": {
                "type": "string",
                "description": "Nueva hora (HH:MM)",
            },
            "profesional": {
                "type": "string",
                "description": "Profesional (puede cambiar si el día lo requiere)",
            },
        },
        "required": ["turno_id", "nueva_fecha", "nueva_hora", "profesional"],
    },
}

CANCELAR_TURNO = {
    "name": "cancelar_turno",
    "description": (
        "Cancela un turno cambiando su estado a 'Cancelada' en BBDD SESIONES. "
        "Confirmar SIEMPRE con el paciente antes de ejecutar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "turno_id": {
                "type": "string",
                "description": "ID del turno a cancelar",
            },
        },
        "required": ["turno_id"],
    },
}

# =============================================================================
# 3. PRECIOS Y PRESUPUESTOS
# =============================================================================

CONSULTAR_TARIFARIO = {
    "name": "consultar_tarifario",
    "description": (
        "Consulta el precio de un tratamiento en BBDD TARIFARIO. "
        "NUNCA hardcodear valores — siempre consultar esta herramienta."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tratamiento": {
                "type": "string",
                "description": (
                    "Nombre del tratamiento "
                    "(ej: Alineadores, Blanqueamiento, Brackets metálicos, "
                    "Odontología primera vez, Limpieza, etc)"
                ),
            },
        },
        "required": ["tratamiento"],
    },
}

CONSULTAR_PRESUPUESTO = {
    "name": "consultar_presupuesto",
    "description": (
        "Consulta presupuestos de un paciente en BBDD PRESUPUESTOS. "
        "Retorna detalle, monto total y saldo pendiente. "
        "Si tiene múltiples presupuestos, retorna todos."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID del paciente en AppSheet",
            },
        },
        "required": ["paciente_id"],
    },
}

# =============================================================================
# 4. PAGOS
# =============================================================================

BUSCAR_PAGO = {
    "name": "buscar_pago",
    "description": (
        "Busca si ya existe un pago registrado para un paciente (REGLA ANTI-DUPLICADO). "
        "Verificar SIEMPRE antes de registrar un pago nuevo. "
        "Busca por paciente + fecha + monto + método."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID del paciente",
            },
            "fecha": {
                "type": "string",
                "description": "Fecha del pago (DD/MM/YYYY)",
            },
            "monto": {
                "type": "string",
                "description": "Monto del pago",
            },
            "metodo_pago": {
                "type": "string",
                "description": "Método (Transferencia, Efectivo, MercadoPago, Tarjeta)",
            },
        },
        "required": ["paciente_id", "fecha", "monto"],
    },
}

REGISTRAR_PAGO = {
    "name": "registrar_pago",
    "description": (
        "Registra un pago nuevo en BBDD PAGOS. "
        "IMPORTANTE: Verificar primero con buscar_pago que no exista un duplicado. "
        "Duplicar un pago es un ERROR GRAVE."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "paciente_id": {
                "type": "string",
                "description": "ID del paciente (ej: ANT-15)",
            },
            "paciente_nombre": {
                "type": "string",
                "description": "Nombre completo del paciente (Apellido, Nombre)",
            },
            "tratamiento": {
                "type": "string",
                "description": "Tratamiento asociado al pago (ej: Odontologia primera vez)",
            },
            "fecha": {
                "type": "string",
                "description": "Fecha del pago (DD/MM/YYYY)",
            },
            "monto": {
                "type": "string",
                "description": "Monto del pago",
            },
            "moneda": {
                "type": "string",
                "description": "Moneda: PESOS o USD",
                "default": "PESOS",
            },
            "metodo_pago": {
                "type": "string",
                "description": (
                    "Método de pago: Efectivo, Transferencia, Mercado Pago, "
                    "Tarjeta de Credito, Tarjeta de Debito"
                ),
            },
            "tipo_pago": {
                "type": "string",
                "description": (
                    "Tipo de pago: Seña, Arancel, Cuota, Implante, Endodoncia, "
                    "Cirugia, Tratamiento Protesis, Blanqueamiento, "
                    "Tratamiento ortodoncia, Tratamiento alineadores"
                ),
            },
            "observaciones": {
                "type": "string",
                "description": "Número de operación del comprobante u observaciones",
                "default": "",
            },
        },
        "required": [
            "paciente_id", "paciente_nombre", "tratamiento",
            "fecha", "monto", "metodo_pago", "tipo_pago",
        ],
    },
}

# =============================================================================
# 5. TAREAS PENDIENTES (Google Sheets)
# =============================================================================

CREAR_TAREA_PENDIENTE = {
    "name": "crear_tarea_pendiente",
    "description": (
        "Crea una tarea en la Google Sheet de Tareas Pendientes para que el equipo "
        "(Franco/Cynthia) la resuelva. Usar cuando Sofía no puede resolver algo: "
        "Coordinación Endodoncia/Implantes/Cirugía, Urgencias sin turno, "
        "Reprogramaciones sin opciones, Consultas sin respuesta, Facturas pendientes, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tipo": {
                "type": "string",
                "description": (
                    "Tipo de tarea: Coordinación Endodoncia, Coordinación Implantes, "
                    "Coordinación Cirugía, Urgencia, Reprogramación, Sin disponibilidad, "
                    "Consulta sin respuesta, Factura pendiente, Problema alineadores, "
                    "Archivo/estudio recibido"
                ),
            },
            "contexto": {
                "type": "string",
                "description": (
                    "Descripción detallada: qué necesita el paciente, "
                    "por qué no se pudo resolver, preferencias, etc."
                ),
            },
            "paciente": {
                "type": "string",
                "description": "Nombre del paciente",
                "default": "",
            },
            "telefono": {
                "type": "string",
                "description": "Teléfono WhatsApp del paciente",
                "default": "",
            },
            "paciente_id": {
                "type": "string",
                "description": "ID AppSheet del paciente (si existe)",
                "default": "",
            },
            "profesional": {
                "type": "string",
                "description": "Especialista relacionado (auto para coordinaciones)",
                "default": "",
            },
            "prioridad": {
                "type": "string",
                "description": "Prioridad: '🔴 Alta' o '🟡 Normal' (default Normal, urgencias siempre Alta)",
                "default": "🟡 Normal",
            },
        },
        "required": ["tipo", "contexto"],
    },
}

# =============================================================================
# LISTA COMPLETA DE TOOLS
# =============================================================================

ALL_TOOLS = [
    # Identificación
    BUSCAR_PACIENTE,
    BUSCAR_LEAD,
    CREAR_LEAD,
    CREAR_PACIENTE,
    # Turnos
    CONSULTAR_HORARIOS,
    BUSCAR_DISPONIBILIDAD,
    AGENDAR_TURNO,
    BUSCAR_TURNO_PACIENTE,
    MODIFICAR_TURNO,
    CANCELAR_TURNO,
    # Precios
    CONSULTAR_TARIFARIO,
    CONSULTAR_PRESUPUESTO,
    # Pagos
    BUSCAR_PAGO,
    REGISTRAR_PAGO,
    # Tareas
    CREAR_TAREA_PENDIENTE,
]

# Set de nombres para validación rápida
TOOL_NAMES = {t["name"] for t in ALL_TOOLS}
