-- ============================================================================
-- NEXUS Clinic OS — Schema Completo v2
-- 31 tablas: 16 operacional + 15 config
-- Generado desde mapeo de columnas AppSheet — Marzo 2026
-- ============================================================================
-- INSTRUCCIONES:
--   1. Conectate a Cloud SQL:  gcloud sql connect stick-db --user=postgres --quiet
--   2. Conectate a la base:    \c nexus_clinic_os
--   3. Copiá y pegá este contenido completo en la terminal
-- ============================================================================

-- Limpiar schemas existentes (safe reset)
DROP SCHEMA IF EXISTS operacional CASCADE;
DROP SCHEMA IF EXISTS config CASCADE;

CREATE SCHEMA operacional;
CREATE SCHEMA config;

-- ============================================================================
-- SCHEMA: config — 15 tablas de referencia (datos estáticos)
-- ============================================================================

CREATE TABLE config."LISTA A | tipo tratamientos" (
    "Row ID"                TEXT,
    "ID TIPO TRATAMIENTO"   INTEGER PRIMARY KEY,
    "TIPO DE TRATAMIENTO"   TEXT,
    "Status Servicio"       TEXT,
    "Duracion Turno"        INTERVAL DEFAULT '00:00:00'
);

CREATE TABLE config."LISTA B | FUENTE CAPTACION" (
    "Row ID"                TEXT,
    "ID Fuente"             INTEGER PRIMARY KEY,
    "Fuente Captacion"      TEXT,
    "Status Fuente"         TEXT
);

CREATE TABLE config."LISTA C | STATUS LEAD" (
    "Row ID"                TEXT,
    "ID Temp Lead"          INTEGER PRIMARY KEY,
    "Status Lead"           TEXT
);

CREATE TABLE config."LISTA D | Estado Paciente" (
    "Row ID"                TEXT,
    "ID Status Paciente"    INTEGER PRIMARY KEY,
    "Estado Paciente"       TEXT
);

CREATE TABLE config."LISTA E | TIPO DE ENCUESTA" (
    "Row ID"                TEXT,
    "ID Encuesta"           INTEGER PRIMARY KEY,
    "Tipo de Encuesta"      TEXT
);

CREATE TABLE config."LISTA F | TIPO DE GASTO" (
    "Row ID"                TEXT,
    "ID TIPO GASTO"         INTEGER PRIMARY KEY,
    "TIPO DE GASTO"         TEXT NOT NULL,
    "Detalle"               TEXT NOT NULL,
    "Unidad"                TEXT
);

CREATE TABLE config."LISTA G | Metodo de Pago" (
    "Row ID"                TEXT,
    "ID Metodo Pago"        INTEGER PRIMARY KEY,
    "Metodo de Pago"        TEXT
);

-- Nota: G1-J usan Row ID como KEY (diferente a A-G que usan ID numerico)
CREATE TABLE config."LISTA G1 | Estado de Pago" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Status Pago"        INTEGER,
    "Status pago"           TEXT
);

CREATE TABLE config."LISTA H | Unidad de medida" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Unidad"             INTEGER,
    "Unidad medida"         TEXT
);

CREATE TABLE config."LISTA I | Estado de Tratamiento" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Status Trat"        INTEGER,
    "Status Tratamiento"    TEXT
);

CREATE TABLE config."LISTA J | Estado de Sesion" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Status Sesion"      INTEGER,
    "Status Sesion"         TEXT
);

CREATE TABLE config."Lista L | Insumos y Packaging" (
    "Row ID"                TEXT PRIMARY KEY,
    "Title"                 TEXT,
    "Material"              TEXT,
    "Categoria"             TEXT,
    "Date"                  DATE DEFAULT CURRENT_DATE
);

CREATE TABLE config."LISTA M | CATEGORIA DE PAGOS" (
    "Row ID"                TEXT PRIMARY KEY,
    "Tipo de Pago"          TEXT
);

CREATE TABLE config."LISTA N | UNIDAD DE NEGOCIO" (
    "Row ID"                TEXT PRIMARY KEY,
    "Unidad de negocio"     TEXT
);

CREATE TABLE config."LISTA O | HORARIOS DE ATENCION" (
    "Row ID"                TEXT PRIMARY KEY,
    "DIA"                   TEXT,
    "HORA INICIO"           TIME,
    "HORA CIERRE"           TIME,
    "Sede"                  TEXT DEFAULT 'SALA 1',
    "Consultorio"           TEXT DEFAULT 'Virrey del Pino'
);

-- ============================================================================
-- SCHEMA: operacional — 16 tablas de negocio (datos dinámicos)
-- ============================================================================

-- 1. BBDD PACIENTES
-- Columnas virtuales NO almacenadas: SALDO PEND, Proximo Turno, Ultimo Turno,
-- Facturacion Acumulada, todos los Related*
CREATE TABLE operacional."BBDD PACIENTES" (
    "ID Paciente"           TEXT PRIMARY KEY,
    "Paciente"              TEXT NOT NULL,
    "Telefono (Whatsapp)"   TEXT,
    "email"                 TEXT DEFAULT '__1@1.com__',
    "Fecha Nacimiento"      DATE,
    "Sexo"                  TEXT DEFAULT 'Otro',
    "DNI / Pasaporte"       TEXT DEFAULT 'COMPLETAR',
    "Estado del Paciente"   TEXT DEFAULT 'Activo',
    "Fecha de Alta"         DATE DEFAULT CURRENT_DATE,
    "Fuente de Captacion"   TEXT,
    "Referido"              TEXT,
    "CONSGEN FIRMADO"       TEXT DEFAULT '',
    "Notas"                 TEXT
);

-- 2. BBDD LEADS
-- Columna virtual NO almacenada: Related BBDD SESIONES
CREATE TABLE operacional."BBDD LEADS" (
    "ID Lead"               TEXT PRIMARY KEY,
    "Apellido y Nombre"     TEXT,
    "Telefono (Whatsapp)"   TEXT NOT NULL,
    "email"                 TEXT,
    "Fecha Creacion"        DATE DEFAULT CURRENT_DATE,
    "Estado del Lead (Temp)" TEXT DEFAULT 'Nuevo',
    "Motivo Interes"        TEXT,
    "Fuente Captacion"      TEXT,
    "Notas y Seguimientos"  TEXT
);

-- 3. BBDD SESIONES
-- Columnas virtuales NO almacenadas: cols 26-36 (LOOKUPs, IFs, SUMs)
-- +2 campos nuevos: Consultorio, Sede
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
    "Consultorio"           TEXT DEFAULT 'SALA 1',
    "Sede"                  TEXT DEFAULT 'Virrey del Pino'
);

-- 4. BBDD PAGOS
-- +2 campos nuevos: Consultorio, Sede
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
    "Consultorio"           TEXT DEFAULT 'SALA 1',
    "Sede"                  TEXT DEFAULT 'Virrey del Pino'
);

-- 5. BBDD PRESUPUESTOS
-- Key compuesto en AppSheet: _ComputedKey = CONCATENATE(Row ID, ID Presupuesto)
-- Columnas virtuales NO almacenadas: IDENTIFICADOR (formula),
-- _ComputedKey (formula), Monto Pagado (SUM), Saldo Pendiente (formula)
CREATE TABLE operacional."BBDD PRESUPUESTOS" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Presupuesto"        TEXT,
    "ID Paciente"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT,
    "Telefono"              TEXT,
    "Tratamiento"           TEXT,
    "Descripción"           TEXT,
    "Fecha Presupuesto"     DATE DEFAULT CURRENT_DATE,
    "Monto Total"           NUMERIC(12,2),
    "Moneda"                TEXT DEFAULT 'PESOS',
    "ESTADO"                TEXT DEFAULT 'ACTIVO',
    "ID Alineadores"        TEXT,
    "Cuotas"                TEXT
);

-- 6. BBDD TARIFARIO
CREATE TABLE operacional."BBDD TARIFARIO" (
    "Tratamiento"           TEXT PRIMARY KEY,
    "Tratamiento Detalle"   TEXT,
    "Precio Lista"          NUMERIC(12,2),
    "Precio Efectivo"       NUMERIC(12,2),
    "Moneda"                TEXT DEFAULT 'PESOS',
    "Seña"                  NUMERIC(12,2)
);

-- 7. BBDD ALINEADORES (38 cols en AppSheet, ~30 reales)
-- Columnas virtuales NO almacenadas: ID PACIENTE (LOOKUP), 1P/3P (IF LOOKUP),
-- ULTIMO TURNO, PROXIMO TURNO, PROXIMOS ALINEADORES, Related BBDD PRODUCCION
CREATE TABLE operacional."BBDD ALINEADORES" (
    "ID ALINEADORES"        INTEGER PRIMARY KEY,
    "PACIENTE"              TEXT,
    "TIPO TRATAMIENTO"      TEXT DEFAULT '1era Etapa',
    "MAXILAR"               TEXT DEFAULT 'SUP e INF',
    "TIPO DE PRODUCCION"    TEXT DEFAULT 'MENSUAL',
    "FECHA INICIO"          DATE DEFAULT CURRENT_DATE,
    "ESTADO TRATAMIENTO"    TEXT DEFAULT 'ESCANEADO',
    "ACCION PENDIENTE"      BOOLEAN DEFAULT FALSE,
    "A1"                    BOOLEAN DEFAULT FALSE,
    "A2"                    BOOLEAN DEFAULT FALSE,
    "A3"                    BOOLEAN DEFAULT FALSE,
    "A4"                    BOOLEAN DEFAULT FALSE,
    "A5"                    BOOLEAN DEFAULT FALSE,
    "A6"                    BOOLEAN DEFAULT FALSE,
    "A7"                    BOOLEAN DEFAULT FALSE,
    "A8"                    BOOLEAN DEFAULT FALSE,
    "A9"                    BOOLEAN DEFAULT FALSE,
    "A10"                   BOOLEAN DEFAULT FALSE,
    "A11"                   BOOLEAN DEFAULT FALSE,
    "A12"                   BOOLEAN DEFAULT FALSE,
    "CO"                    BOOLEAN DEFAULT FALSE,
    "PRESUPUESTO"           NUMERIC(12,2),
    "NPS TRATAMIENTO"       INTEGER,
    "NOTAS CLINICAS"        TEXT,
    "ADJUNTOS"              TEXT,
    "P1"                    BOOLEAN DEFAULT FALSE,
    "P2"                    BOOLEAN DEFAULT FALSE,
    "P CO"                  BOOLEAN DEFAULT FALSE,
    "FECHA UPDATE"          DATE,
    "IDENTIFICADOR"         TEXT
);

-- 8. BBDD CONCILIACION (23 cols, muchas virtuales de SUM/COUNT)
-- Columnas virtuales NO almacenadas: Sesiones_Realizadas, Sesiones_Sin_Cobro,
-- Total_Cobrado, Saldo_Esperado, Efectivo_Sistema_Pesos, Efectivo_Sistema_USD,
-- Gastos_Efectivo_Dia, Diferencia_Efectivo, Transferencia_Sistema_P/U,
-- Gastos_Transferencia_Dia, Diferencia_Transferencia, Estado
CREATE TABLE operacional."BBDD CONCILIACION" (
    "ID CIERRE"             TEXT PRIMARY KEY,
    "Fecha"                 DATE DEFAULT CURRENT_DATE,
    "Responsable"           TEXT NOT NULL DEFAULT 'Hatzerian, Cynthia',
    "Hora de Cierre"        TIME,
    "Saldo_Caja_Inicio"     NUMERIC(12,2) DEFAULT 0,
    "Efectivo_Contado_PESOS" NUMERIC(12,2),
    "Transferencia_Banco_PESOS" NUMERIC(12,2),
    "Observaciones"         TEXT
);

-- 9. BBDD FACTURAS (22 cols, 4 lineas de items hardcoded)
CREATE TABLE operacional."BBDD FACTURAS" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID PACIENTE"           TEXT,
    "PACIENTE"              TEXT,
    "Whatsapp"              TEXT,
    "ID Sesion"             TEXT,
    "Fecha Emision"         DATE DEFAULT CURRENT_DATE,
    "Tipo Documento"        TEXT DEFAULT 'DNI',
    "N Documento"           TEXT,
    "Condicion IVA"         TEXT DEFAULT '5',
    "1- Item"               TEXT,
    "1- Cant"               NUMERIC(12,2),
    "1- Precio unitario"    NUMERIC(12,2),
    "2- Item"               TEXT,
    "2- Cant"               NUMERIC(12,2),
    "2- Precio unitario"    NUMERIC(12,2),
    "3- Item"               TEXT,
    "3- Cant"               NUMERIC(12,2),
    "3- Precio unitario"    NUMERIC(12,2),
    "4- Item"               TEXT,
    "4- Cant"               NUMERIC(12,2),
    "4- Precio unitario"    NUMERIC(12,2)
);

-- 10. BBDD GASTOS (19 cols)
-- Columnas virtuales NO almacenadas: Unidad de medida (LOOKUP),
-- ID PROVEEDOR, ID INSUMO, ID EMPLEADO (formulas IF)
CREATE TABLE operacional."BBDD GASTOS" (
    "ID Gasto"              INTEGER PRIMARY KEY,
    "Fecha de gasto"        DATE DEFAULT CURRENT_DATE,
    "Tipo de gasto"         TEXT,
    "Tipo de gasto (Detalle)" TEXT,
    "Descripcion de Gasto"  TEXT,
    "Proveedor"             TEXT DEFAULT 'Otro',
    "Monto ($)"             NUMERIC(12,2),
    "Metodo de Pago"        TEXT,
    "Factura proveedor"     TEXT,
    "MONEDA"                TEXT DEFAULT 'PESOS',
    "Cantidad Comprada"     NUMERIC(12,2),
    "Profesionales y Empleados" TEXT,
    "Observaciones"         TEXT
);

-- 11. BBDD INSUMOS y STOCK (10 cols)
CREATE TABLE operacional."BBDD INSUMOS y STOCK" (
    "Row ID"                TEXT PRIMARY KEY,
    "Untitled Text"         TEXT,
    "Untitled Dropdown"     TEXT,
    "ID INSUMO"             TEXT,
    "INSUMO"                TEXT,
    "STOCK DISPOIBLE"       TEXT,
    "PUNTO REORDEN"         TEXT,
    "STATUS REABASTECIMIENTO" TEXT,
    "ID PROVEEDOR"          TEXT
);

-- 12. BBDD NOTAS (8 cols)
CREATE TABLE operacional."BBDD NOTAS" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Paciente"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT,
    "Tratamiento"           TEXT,
    "Comentario"            TEXT,
    "Fecha de Nota"         DATE DEFAULT CURRENT_DATE,
    "Status"                TEXT DEFAULT 'Pendiente'
);

-- 13. BBDD ORDENES (9 cols)
CREATE TABLE operacional."BBDD ORDENES" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID Paciente"           TEXT REFERENCES operacional."BBDD PACIENTES"("ID Paciente"),
    "Paciente"              TEXT,
    "Orden necesaria"       TEXT,
    "Fecha creacion"        DATE DEFAULT CURRENT_DATE,
    "Status"                TEXT DEFAULT 'Pendiente',
    "DNI"                   NUMERIC,
    "Obra Social"           TEXT
);

-- 14. BBDD PRODUCCION (22 cols, muchas virtuales LOOKUP)
-- Columnas virtuales NO almacenadas: ID PRODUCCION (MAX formula),
-- PACIENTE, ALINEADORES A PRODUCIR, FECHA PLANIFICADA, PROXIMO TURNO,
-- PRIORIDAD, 1P/3P, TIPO TRATAMIENTO, MAXILAR, TIPO SEGUIMIENTO,
-- ESTADO TRATAMIENTO, ULTIMO TURNO (todas LOOKUP)
CREATE TABLE operacional."BBDD PRODUCCION" (
    "Row ID"                TEXT PRIMARY KEY,
    "ID ALINEADORES"        TEXT,
    "STATUS PRODUCCION"     TEXT DEFAULT 'PLANIFICADO',
    "FECHA PRODUCIDO"       DATE DEFAULT CURRENT_DATE,
    "IMPRESORA"             TEXT,
    "LAV/SEC"               TEXT,
    "ESTAMPADORA"           TEXT,
    "RESINA"                TEXT,
    "ULTIMA ENTREGA"        DATE DEFAULT CURRENT_DATE
);

-- 15. BBDD PROFESIONALES
CREATE TABLE operacional."BBDD PROFESIONALES" (
    "ID Profesional"        INTEGER PRIMARY KEY,
    "Profesional"           TEXT DEFAULT 'APELLIDO, NOMBRE',
    "TIPO"                  TEXT,
    "Status"                TEXT DEFAULT 'ACTIVADO',
    "Fecha inicio"          DATE DEFAULT CURRENT_DATE,
    "Fecha Finalizacion"    DATE,
    "FOTO"                  TEXT
);

-- 16. BBDD PROVEEDORES (15 cols)
CREATE TABLE operacional."BBDD PROVEEDORES" (
    "ID Proveedor"          INTEGER PRIMARY KEY,
    "Proveedor"             TEXT,
    "email"                 TEXT,
    "Telefono (Whatsapp)"   TEXT,
    "CUIT"                  NUMERIC,
    "Direccion"             TEXT,
    "Banco"                 TEXT,
    "CBU"                   NUMERIC,
    "Alias"                 TEXT,
    "Fecha ultima compra"   DATE DEFAULT CURRENT_DATE,
    "Insumo"                TEXT,
    "Estado Proveedor"      TEXT,
    "Gastos acumulados ($)" NUMERIC(12,2)
);

-- ============================================================================
-- INDEXES — Optimizados para consultas frecuentes del bot
-- ============================================================================

-- Búsqueda de pacientes/leads por teléfono (la query más frecuente del bot)
CREATE INDEX idx_pacientes_telefono ON operacional."BBDD PACIENTES"("Telefono (Whatsapp)");
CREATE INDEX idx_pacientes_estado ON operacional."BBDD PACIENTES"("Estado del Paciente");
CREATE INDEX idx_leads_telefono ON operacional."BBDD LEADS"("Telefono (Whatsapp)");

-- Búsqueda de sesiones (disponibilidad, turnos del paciente)
CREATE INDEX idx_sesiones_fecha_estado ON operacional."BBDD SESIONES"("Fecha de Sesion", "Estado de Sesion");
CREATE INDEX idx_sesiones_paciente ON operacional."BBDD SESIONES"("ID PACIENTE");
CREATE INDEX idx_sesiones_profesional ON operacional."BBDD SESIONES"("Profesional Asignado");

-- Búsqueda de pagos por paciente
CREATE INDEX idx_pagos_paciente ON operacional."BBDD PAGOS"("ID PACIENTE");

-- Búsqueda de presupuestos por paciente
CREATE INDEX idx_presupuestos_paciente ON operacional."BBDD PRESUPUESTOS"("ID Paciente");

-- Notas y órdenes por paciente
CREATE INDEX idx_notas_paciente ON operacional."BBDD NOTAS"("ID Paciente");
CREATE INDEX idx_ordenes_paciente ON operacional."BBDD ORDENES"("ID Paciente");

-- Gastos por fecha
CREATE INDEX idx_gastos_fecha ON operacional."BBDD GASTOS"("Fecha de gasto");

-- Conciliación por fecha
CREATE INDEX idx_conciliacion_fecha ON operacional."BBDD CONCILIACION"("Fecha");

-- ============================================================================
-- RESUMEN
-- ============================================================================
-- Schema config:  15 tablas (LISTA A-O)
-- Schema operacional: 16 tablas (BBDD)
-- Total: 31 tablas
-- Indexes: 12 para queries frecuentes del bot
-- ============================================================================
