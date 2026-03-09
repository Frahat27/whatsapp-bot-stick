-- =============================================
-- CONFIG TABLES: Complete data from AppSheet screenshots
-- Generated: 2026-03-07
-- Source: Exact data from user-provided screenshots
-- Run: gcloud sql connect stick-db --user=postgres --database=nexus_clinic_os < config_inserts.sql
-- =============================================

-- Truncate all config tables for clean insert
-- (LISTA O already migrated via API - skip it)
TRUNCATE config."LISTA A | tipo tratamientos" CASCADE;
TRUNCATE config."LISTA B | FUENTE CAPTACION" CASCADE;
TRUNCATE config."LISTA C | STATUS LEAD" CASCADE;
TRUNCATE config."LISTA D | Estado Paciente" CASCADE;
TRUNCATE config."LISTA E | TIPO DE ENCUESTA" CASCADE;
TRUNCATE config."LISTA F | TIPO DE GASTO" CASCADE;
TRUNCATE config."LISTA G | Metodo de Pago" CASCADE;
TRUNCATE config."LISTA G1 | Estado de Pago" CASCADE;
TRUNCATE config."LISTA H | Unidad de medida" CASCADE;
TRUNCATE config."LISTA I | Estado de Tratamiento" CASCADE;
TRUNCATE config."LISTA J | Estado de Sesion" CASCADE;
TRUNCATE config."Lista L | Insumos y Packaging" CASCADE;
TRUNCATE config."LISTA M | CATEGORIA DE PAGOS" CASCADE;
TRUNCATE config."LISTA N | UNIDAD DE NEGOCIO" CASCADE;

-- =============================================
-- LISTA A | tipo tratamientos (14 rows)
-- =============================================
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (1, 'Alineadores', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (2, 'Blanqueamiento', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (3, 'Ortodoncia (Brackets)', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (4, 'Implantes', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (5, 'Cirugia', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (6, 'Protesis', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (7, 'Urgencia odontologica', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (8, 'Control', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (9, 'Odontologia primera vez', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (10, 'Limpieza', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (11, 'Caries', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (12, 'Endodoncia (Tratamiento de Conducto)', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (13, 'Odontopediatria', 'ACTIVADO');
INSERT INTO config."LISTA A | tipo tratamientos" ("ID TIPO TRATAMIENTO", "TIPO DE TRATAMIENTO", "Status Servicio") VALUES (14, 'Otro', 'ACTIVADO');

-- =============================================
-- LISTA B | FUENTE CAPTACION (7 rows)
-- =============================================
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (1, 'Instagram', 'Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (2, 'Tik Tok', 'No Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (3, 'Google Maps', 'Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (4, 'Google Ads', 'No Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (5, 'Organico', 'Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (6, 'Referido (Boca en Boca)', 'Activo');
INSERT INTO config."LISTA B | FUENTE CAPTACION" ("ID Fuente", "Fuente Captacion", "Status Fuente") VALUES (7, '3P Alineadores', 'Activo');

-- =============================================
-- LISTA C | STATUS LEAD (7 rows)
-- =============================================
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (1, 'Nuevo');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (2, 'Contactado');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (3, 'Cerrada Ganada');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (4, 'Cerrada Perdida');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (5, 'Recontactado');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (6, 'Contactado Frio');
INSERT INTO config."LISTA C | STATUS LEAD" ("ID Temp Lead", "Status Lead") VALUES (7, 'Contactado Caliente');

-- =============================================
-- LISTA D | Estado Paciente (4 rows)
-- =============================================
INSERT INTO config."LISTA D | Estado Paciente" ("ID Status Paciente", "Estado Paciente") VALUES (1, 'ACTIVO');
INSERT INTO config."LISTA D | Estado Paciente" ("ID Status Paciente", "Estado Paciente") VALUES (2, 'FINALIZADO');
INSERT INTO config."LISTA D | Estado Paciente" ("ID Status Paciente", "Estado Paciente") VALUES (3, 'INACTIVO');
INSERT INTO config."LISTA D | Estado Paciente" ("ID Status Paciente", "Estado Paciente") VALUES (4, 'ABANDONO');

-- =============================================
-- LISTA E | TIPO DE ENCUESTA (6 rows)
-- =============================================
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (1, 'NPS Tratamiento');
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (2, 'NPS 3M');
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (3, 'Google Review');
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (4, 'CSAT Gestion Lead');
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (5, 'CSAT Atencion presencial');
INSERT INTO config."LISTA E | TIPO DE ENCUESTA" ("ID Encuesta", "Tipo de Encuesta") VALUES (6, 'CSAT Seguimiento Tratamiento');

-- =============================================
-- LISTA F | TIPO DE GASTO (40 rows)
-- =============================================
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (1, 'INSUMOS', '- Resinas y plasticos (Alineadores)', 'Botella (1lt)');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (2, 'INSUMOS', '-Alcohol (Alineadores)', 'Litros');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (3, 'INSUMOS', '-Servilletas (Alineadores)', 'Rollos');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (4, 'INSUMOS', '-Laminas termoformado (Alineadores)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (5, 'INSUMOS', '-Insumos quirurgicos (Cirugias)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (6, 'INSUMOS', '-Materiales endodonticos (Conductos)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (7, 'INSUMOS', '-Insumos generales (Chequeos)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (8, 'PACKAGING', '- Bolso (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (9, 'PACKAGING', '- Estuche (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (10, 'PACKAGING', '- Estuche flexible (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (11, 'PACKAGING', '- Cepillo electrico (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (12, 'PACKAGING', '- Cepillo comun (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (13, 'PACKAGING', '- Corega taps (Alineadores)', 'Cajita');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (14, 'PACKAGING', '- Palillos extraccion y colocacion (Alineadores)', 'Units');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (15, 'PACKAGING', '- Otros (Alineadores)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (16, 'HONORARIOS CLINICOS', '- Comision profesional (Alineadores)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (17, 'HONORARIOS CLINICOS', '- Comision profesional (Cirugias)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (18, 'HONORARIOS CLINICOS', '- Comision profesional (Conductos)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (19, 'HONORARIOS CLINICOS', '- Comision profesional (Chequeos)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (50, 'HONORARIOS CLINICOS', '- Comision profesional (Implantes)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (20, 'HONORARIOS CLINICOS', '- Comision profesional (Otros)', '50%');
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (21, 'LOGISTICA', '-Envio moto', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (22, 'MARKETING', '-Branding', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (23, 'MARKETING', '-Instagram Spend (Meta Ads)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (24, 'MARKETING', '-Tik Tok Spend', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (25, 'MARKETING', '-Google Spend (Google Ads)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (26, 'MARKETING', '-Otros Spend (Influencers)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (27, 'MARKETING', '-Agencias', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (28, 'SOFTWARE', '-Google suite', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (29, 'SOFTWARE', '-Meducar', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (30, 'SOFTWARE', '-Nemocast', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (31, 'SOFTWARE', '-Chitubox', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (32, 'SALARIOS', '-Salarios', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (33, 'SALARIOS', '-Bonos', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (34, 'SALARIOS', '-Carga sociales', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (35, 'SALARIOS', '-Otros (RRHH)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (36, 'ALQUILERES Y SERVICIOS', '-Alquileres', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (37, 'ALQUILERES Y SERVICIOS', '-Impuestos & expensas', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (38, 'ALQUILERES Y SERVICIOS', '-Servicios (Luz, gas, agua, etc)', NULL);
INSERT INTO config."LISTA F | TIPO DE GASTO" ("ID TIPO GASTO", "TIPO DE GASTO", "Detalle", "Unidad") VALUES (39, 'ALQUILERES Y SERVICIOS', '-Seguridad', NULL);

-- =============================================
-- LISTA G | Metodo de Pago (5 rows)
-- =============================================
INSERT INTO config."LISTA G | Metodo de Pago" ("ID Metodo Pago", "Metodo de Pago") VALUES (1, 'Efectivo');
INSERT INTO config."LISTA G | Metodo de Pago" ("ID Metodo Pago", "Metodo de Pago") VALUES (2, 'Transferencia');
INSERT INTO config."LISTA G | Metodo de Pago" ("ID Metodo Pago", "Metodo de Pago") VALUES (3, 'Mercado Pago');
INSERT INTO config."LISTA G | Metodo de Pago" ("ID Metodo Pago", "Metodo de Pago") VALUES (4, 'Tarjeta de Credito');
INSERT INTO config."LISTA G | Metodo de Pago" ("ID Metodo Pago", "Metodo de Pago") VALUES (5, 'Tarjeta de Debito');

-- =============================================
-- LISTA G1 | Estado de Pago (4 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA G1 | Estado de Pago" ("Row ID", "ID Status Pago", "Status pago") VALUES ('g1-1', 1, 'Confirmado');
INSERT INTO config."LISTA G1 | Estado de Pago" ("Row ID", "ID Status Pago", "Status pago") VALUES ('g1-2', 2, 'Pendiente');
INSERT INTO config."LISTA G1 | Estado de Pago" ("Row ID", "ID Status Pago", "Status pago") VALUES ('g1-3', 3, 'Rechazado');
INSERT INTO config."LISTA G1 | Estado de Pago" ("Row ID", "ID Status Pago", "Status pago") VALUES ('g1-4', 4, 'Reembolso');

-- =============================================
-- LISTA H | Unidad de medida (4 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA H | Unidad de medida" ("Row ID", "ID Unidad", "Unidad medida") VALUES ('h-1', 1, 'Litros');
INSERT INTO config."LISTA H | Unidad de medida" ("Row ID", "ID Unidad", "Unidad medida") VALUES ('h-2', 2, 'Kg');
INSERT INTO config."LISTA H | Unidad de medida" ("Row ID", "ID Unidad", "Unidad medida") VALUES ('h-3', 3, 'cm3');
INSERT INTO config."LISTA H | Unidad de medida" ("Row ID", "ID Unidad", "Unidad medida") VALUES ('h-4', 4, 'unidades');

-- =============================================
-- LISTA I | Estado de Tratamiento (4 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA I | Estado de Tratamiento" ("Row ID", "ID Status Trat", "Status Tratamiento") VALUES ('i-1', 1, 'En curso');
INSERT INTO config."LISTA I | Estado de Tratamiento" ("Row ID", "ID Status Trat", "Status Tratamiento") VALUES ('i-2', 2, 'Finalizado');
INSERT INTO config."LISTA I | Estado de Tratamiento" ("Row ID", "ID Status Trat", "Status Tratamiento") VALUES ('i-3', 3, 'Suspendido');
INSERT INTO config."LISTA I | Estado de Tratamiento" ("Row ID", "ID Status Trat", "Status Tratamiento") VALUES ('i-4', 4, 'Abandonado');

-- =============================================
-- LISTA J | Estado de Sesion (6 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-1', 1, 'PLANIFICADA');
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-2', 2, 'CONFIRMADA');
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-3', 3, 'REPROGRAMADA');
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-4', 4, 'REALIZADA');
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-5', 5, 'CANCELADA');
INSERT INTO config."LISTA J | Estado de Sesion" ("Row ID", "ID Status Sesion", "Status Sesion") VALUES ('j-6', 6, 'NO ASISTIO');

-- =============================================
-- Lista L | Insumos y Packaging (4 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."Lista L | Insumos y Packaging" ("Row ID", "Title", "Material", "Categoria", "Date") VALUES ('Item 1', 'Jane Doe', NULL, 'Insumos', '2025-02-18');
INSERT INTO config."Lista L | Insumos y Packaging" ("Row ID", "Title", "Material", "Categoria", "Date") VALUES ('Item 2', 'John Doe', NULL, 'Packaging', '2025-02-17');
INSERT INTO config."Lista L | Insumos y Packaging" ("Row ID", "Title", "Material", "Categoria", "Date") VALUES ('Item 3', 'Hannah Smith', NULL, 'Packaging', '2025-02-17');
INSERT INTO config."Lista L | Insumos y Packaging" ("Row ID", "Title", "Material", "Categoria", "Date") VALUES ('Item 4', 'Jim Smith', NULL, NULL, '2025-02-16');

-- =============================================
-- LISTA M | CATEGORIA DE PAGOS (10 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-1', 'Sena');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-2', 'Arancel');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-3', 'Cuota');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-4', 'Implante');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-5', 'Endodoncia');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-6', 'Cirugia');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-7', 'Tratamiento Protesis');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-8', 'Blanqueamiento');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-9', 'Tratamiento ortodoncia');
INSERT INTO config."LISTA M | CATEGORIA DE PAGOS" ("Row ID", "Tipo de Pago") VALUES ('m-10', 'Tratamiento alineadores');

-- =============================================
-- LISTA N | UNIDAD DE NEGOCIO (4 rows)
-- PK = "Row ID" TEXT
-- =============================================
INSERT INTO config."LISTA N | UNIDAD DE NEGOCIO" ("Row ID", "Unidad de negocio") VALUES ('n-1', 'CYNTHIA H');
INSERT INTO config."LISTA N | UNIDAD DE NEGOCIO" ("Row ID", "Unidad de negocio") VALUES ('n-2', 'STICK');
INSERT INTO config."LISTA N | UNIDAD DE NEGOCIO" ("Row ID", "Unidad de negocio") VALUES ('n-3', 'STICK PRO');
INSERT INTO config."LISTA N | UNIDAD DE NEGOCIO" ("Row ID", "Unidad de negocio") VALUES ('n-4', 'STICK TEEN');

-- =============================================
-- Verification query
-- =============================================
SELECT 'LISTA A' as tabla, count(*) as filas FROM config."LISTA A | tipo tratamientos"
UNION ALL SELECT 'LISTA B', count(*) FROM config."LISTA B | FUENTE CAPTACION"
UNION ALL SELECT 'LISTA C', count(*) FROM config."LISTA C | STATUS LEAD"
UNION ALL SELECT 'LISTA D', count(*) FROM config."LISTA D | Estado Paciente"
UNION ALL SELECT 'LISTA E', count(*) FROM config."LISTA E | TIPO DE ENCUESTA"
UNION ALL SELECT 'LISTA F', count(*) FROM config."LISTA F | TIPO DE GASTO"
UNION ALL SELECT 'LISTA G', count(*) FROM config."LISTA G | Metodo de Pago"
UNION ALL SELECT 'LISTA G1', count(*) FROM config."LISTA G1 | Estado de Pago"
UNION ALL SELECT 'LISTA H', count(*) FROM config."LISTA H | Unidad de medida"
UNION ALL SELECT 'LISTA I', count(*) FROM config."LISTA I | Estado de Tratamiento"
UNION ALL SELECT 'LISTA J', count(*) FROM config."LISTA J | Estado de Sesion"
UNION ALL SELECT 'LISTA L', count(*) FROM config."Lista L | Insumos y Packaging"
UNION ALL SELECT 'LISTA M', count(*) FROM config."LISTA M | CATEGORIA DE PAGOS"
UNION ALL SELECT 'LISTA N', count(*) FROM config."LISTA N | UNIDAD DE NEGOCIO"
UNION ALL SELECT 'LISTA O', count(*) FROM config."LISTA O | HORARIOS DE ATENCION"
ORDER BY tabla;
