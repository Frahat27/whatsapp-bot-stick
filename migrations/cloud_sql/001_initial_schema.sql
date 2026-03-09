-- ============================================================================
-- NEXUS Clinic OS — Schema Inicial
-- Base: Cloud SQL PostgreSQL (stick-db, sa-east-1)
-- Database: nexus_clinic_os
-- ============================================================================
-- Ejecutar en Cloud Shell:
--   \c nexus_clinic_os
--   \i 001_initial_schema.sql
-- ============================================================================

-- Crear schemas
CREATE SCHEMA IF NOT EXISTS operacional;
CREATE SCHEMA IF NOT EXISTS config;

-- ============================================================================
-- SCHEMA: operacional (datos dinamicos de negocio)
-- ============================================================================

-- 1. BBDD PACIENTES
CREATE TABLE operacional."BBDD PACIENTES" (
    "ID Paciente"           TEXT PRIMARY KEY,
    "Paciente"              TEXT NOT NULL,
    "Telefono (Whatsapp)"   TEXT,
    "email"                 TEXT DEFAULT '1@1.com',
    "Fecha Nacimiento"      DATE,
    "Sexo"                  TEXT DEFAULT 'Otro',
    "DNI / Pasaporte"       TEXT DEFAULT 'COMPLETAR',
    "Estado del Paciente"   TEXT DEFAULT 'Activo',
    "Fecha de Alta"         DATE DEFAULT CURRENT_DATE,
    "Fuente de Captacion"   TEXT,
    "Referido"              TEXT,
    "Notas"                 TEXT,
    "CONSGEN FIRMADO"       TEXT DEFAULT '',
    -- Columnas virtuales en AppSheet (NO almacenadas aqui):
    -- SALDO PEND = SUM(presupuestos)
    -- Proximo Turno = MIN(SELECT sesiones futuras)
    -- Ultimo Turno = MAX(SELECT sesiones pasadas)
    -- Facturacion Acumulada = SUM(pagos)
    -- Related BBDD SESIONES, PAGOS, PRESUPUESTOS, NOTAS, ORDENES, ALINEADORES
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pacientes_telefono ON operacional."BBDD PACIENTES" ("Telefono (Whatsapp)");
CREATE INDEX idx_pacientes_estado ON operacional."BBDD PACIENTES" ("Estado del Paciente");

-- 2. BBDD LEADS
CREATE TABLE operacional."BBDD LEADS" (
    "ID Lead"               TEXT PRIMARY KEY,
    "Apellido y Nombre"     TEXT,
    "Telefono (Whatsapp)"   TEXT NOT NULL,
    "email"                 TEXT,
    "Fecha Creacion"        DATE DEFAULT CURRENT_DATE,
    "Estado del Lead (Temp)" TEXT DEFAULT 'Nuevo',
    "Motivo Interes"        TEXT,
    "Fuente Captacion"      TEXT,
    "Notas y Seguimientos"  TEXT,
    -- Related BBDD SESIONES (virtual)
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_leads_telefono ON operacional."BBDD LEADS" ("Telefono (Whatsapp)");
CREATE INDEX idx_leads_estado_fecha ON operacional."BBDD LEADS" ("Estado del Lead (Temp)", "Fecha Creacion");

-- 3. BBDD SESIONES
CREATE TABLE operacional."BBDD SESIONES" (
    "ID Sesion"             TEXT PRIMARY KEY,
    "ID PACIENTE"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT NOT NULL,
    "Tratamiento"           TEXT,
    "Motivo Sesion"         TEXT,
    "Fecha de Sesion"       DATE,
    "Hora Sesion"           TIME,
    "Horario Finalizacion"  TIME,
    "Duracion"              INTEGER,
    "Profesional Asignado"  TEXT,
    "Estado de Sesion"      TEXT DEFAULT 'Planificada',
    "Descripcion de la sesion" TEXT,
    "Observaciones"         TEXT,
    "Solapamiento turnos"   TEXT,
    "Fecha Creacion"        DATE DEFAULT CURRENT_DATE,
    "Telefono (Whatsapp)"   TEXT,
    "Email"                 TEXT,
    -- Columnas virtuales en AppSheet (NO almacenadas aqui):
    -- cols 26-36: LOOKUPs, IFs, SUMs, SELECTs
    -- Campos nuevos para futuro:
    "Consultorio"           TEXT DEFAULT 'SALA 1',
    "Sede"                  TEXT DEFAULT 'Virrey del Pino',
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sesiones_fecha_estado ON operacional."BBDD SESIONES" ("Fecha de Sesion", "Estado de Sesion");
CREATE INDEX idx_sesiones_paciente_estado ON operacional."BBDD SESIONES" ("ID PACIENTE", "Estado de Sesion");
CREATE INDEX idx_sesiones_fecha ON operacional."BBDD SESIONES" ("Fecha de Sesion");
CREATE INDEX idx_sesiones_estado ON operacional."BBDD SESIONES" ("Estado de Sesion");

-- 4. BBDD PAGOS
CREATE TABLE operacional."BBDD PAGOS" (
    "ID Pago"               TEXT PRIMARY KEY,
    "ID PACIENTE"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT,
    "Tratamiento"           TEXT,
    "Fecha del Pago"        DATE,
    "Monto Pagado"          NUMERIC(12,2),
    "Moneda"                TEXT DEFAULT 'PESOS',
    "Metodo de Pago"        TEXT,
    "Estado del Pago"       TEXT DEFAULT 'Confirmado',
    "Tipo de Pago"          TEXT,
    "CUENTA"                TEXT DEFAULT 'CYNTHIA',
    "Nro de Operacion"      TEXT,
    "Quiere Factura?"       BOOLEAN DEFAULT FALSE,
    "Observaciones"         TEXT,
    "Tipo de Paciente"      TEXT,
    -- Campos nuevos para futuro:
    "Consultorio"           TEXT DEFAULT 'SALA 1',
    "Sede"                  TEXT DEFAULT 'Virrey del Pino',
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pagos_paciente_fecha ON operacional."BBDD PAGOS" ("ID PACIENTE", "Fecha del Pago");
CREATE INDEX idx_pagos_paciente_fecha_monto ON operacional."BBDD PAGOS" ("ID PACIENTE", "Fecha del Pago", "Monto Pagado");

-- 5. BBDD PRESUPUESTOS
CREATE TABLE operacional."BBDD PRESUPUESTOS" (
    "Row ID"                TEXT,
    "ID Presupuesto"        TEXT,
    "ID Paciente"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT,
    "Telefono"              TEXT,
    "Tratamiento"           TEXT,
    -- Saldo Pendiente puede ser virtual (formula) o real — TBD con screenshot completo
    "Saldo Pendiente"       NUMERIC(12,2),
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY ("Row ID")
);
CREATE INDEX idx_presupuestos_paciente ON operacional."BBDD PRESUPUESTOS" ("ID Paciente");

-- 6. BBDD TARIFARIO
CREATE TABLE operacional."BBDD TARIFARIO" (
    "Tratamiento"           TEXT PRIMARY KEY,
    "Tratamiento Detalle"   TEXT,
    "Precio Lista"          NUMERIC(12,2),
    "Precio efectivo"       NUMERIC(12,2),
    "Moneda"                TEXT DEFAULT 'PESOS',
    "Sena"                  NUMERIC(12,2),
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);

-- 7. BBDD ALINEADORES
CREATE TABLE operacional."BBDD ALINEADORES" (
    "ID ALINEADORES"        TEXT PRIMARY KEY,
    "ID PACIENTE"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "PACIENTE"              TEXT,
    "ESTADO TRATAMIENTO"    TEXT,
    "1P/3P"                 TEXT,
    -- TODO: completar columnas cuando llegue el screenshot
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_alineadores_paciente ON operacional."BBDD ALINEADORES" ("ID PACIENTE");

-- 8. BBDD PROFESIONALES (estructura minima, completar con screenshot)
CREATE TABLE operacional."BBDD PROFESIONALES" (
    "ID Profesional"        TEXT PRIMARY KEY,
    "Nombre"                TEXT NOT NULL,
    "Apellido"              TEXT,
    "Especialidad"          TEXT,
    "Telefono"              TEXT,
    "Email"                 TEXT,
    "Activo"                BOOLEAN DEFAULT TRUE,
    -- TODO: completar columnas cuando llegue el screenshot
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);

-- 9-16: Tablas pendientes de screenshot
-- Se agregaran cuando el usuario comparta los screenshots de:
-- BBDD CONCILIACION, BBDD FACTURAS, BBDD GASTOS, BBDD INSUMOS y STOCK,
-- BBDD NOTAS, BBDD ORDENES, BBDD PRODUCCION, BBDD PROVEEDORES

-- ============================================================================
-- SCHEMA: config (tablas estaticas / lookups)
-- ============================================================================

-- LISTA O | HORARIOS DE ATENCION
CREATE TABLE config."LISTA O | HORARIOS DE ATENCION" (
    "Row ID"                TEXT PRIMARY KEY,
    "DIA"                   TEXT NOT NULL,
    "HORA INICIO"           TIME,
    "HORA CIERRE"           TIME,
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);

-- LISTA A | tipo tratamientos
-- Usada por buscar_disponibilidad para duracion de turnos
CREATE TABLE config."LISTA A I tipo tratamientos" (
    "Row ID"                TEXT PRIMARY KEY,
    "Tipo"                  TEXT NOT NULL,
    "Duracion Turno"        INTEGER DEFAULT 30,
    -- TODO: completar columnas cuando llegue el screenshot
    "created_at"            TIMESTAMPTZ DEFAULT NOW(),
    "updated_at"            TIMESTAMPTZ DEFAULT NOW()
);

-- LISTA B-N: Tablas pendientes de screenshot
-- Se agregaran cuando el usuario comparta los screenshots de:
-- LISTA B | FUENTE CAPTACION
-- LISTA C | STATUS LEAD
-- LISTA D | Estado Paciente
-- LISTA E | TIPO DE ENCUESTA
-- LISTA F | TIPO DE GASTO
-- LISTA G | Metodo de Pago
-- LISTA G1 | Estado de Pago
-- LISTA H | Unidad de medida
-- LISTA I | Estado de Tratamiento
-- LISTA J | Estado de Sesion
-- Lista L | Insumos y Packaging
-- LISTA M | CATEGORIA DE PAGOS
-- LISTA N | UNIDAD DE NEGOCIO

-- ============================================================================
-- FUNCION: auto-update updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updated_at" = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para auto-update updated_at en todas las tablas
CREATE TRIGGER update_pacientes_updated_at BEFORE UPDATE ON operacional."BBDD PACIENTES"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON operacional."BBDD LEADS"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sesiones_updated_at BEFORE UPDATE ON operacional."BBDD SESIONES"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pagos_updated_at BEFORE UPDATE ON operacional."BBDD PAGOS"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_presupuestos_updated_at BEFORE UPDATE ON operacional."BBDD PRESUPUESTOS"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tarifario_updated_at BEFORE UPDATE ON operacional."BBDD TARIFARIO"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alineadores_updated_at BEFORE UPDATE ON operacional."BBDD ALINEADORES"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profesionales_updated_at BEFORE UPDATE ON operacional."BBDD PROFESIONALES"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_horarios_updated_at BEFORE UPDATE ON config."LISTA O | HORARIOS DE ATENCION"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tratamientos_updated_at BEFORE UPDATE ON config."LISTA A I tipo tratamientos"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
