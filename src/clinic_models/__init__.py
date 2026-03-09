"""
Clinic Models — SQLAlchemy ORM para Cloud SQL (nexus_clinic_os).

Modelos separados de los bot-internal (src/models/) que viven en Neon.
Estos modelos mapean las 31 tablas de la clinica en PostgreSQL.

Schemas:
  - operacional: 16 tablas de datos dinamicos (pacientes, sesiones, pagos, etc.)
  - config: 15 tablas de referencia (listas estaticas A-O)
"""

# Base
from src.clinic_models.base import ClinicBase

# =========================================================================
# OPERACIONAL (16 tablas)
# =========================================================================
from src.clinic_models.paciente import Paciente
from src.clinic_models.lead import Lead
from src.clinic_models.sesion import Sesion
from src.clinic_models.pago import Pago
from src.clinic_models.presupuesto import Presupuesto
from src.clinic_models.tarifario import Tarifario
from src.clinic_models.alineador import Alineador
from src.clinic_models.conciliacion import Conciliacion
from src.clinic_models.factura import Factura
from src.clinic_models.gasto import Gasto
from src.clinic_models.insumo_stock import InsumoStock
from src.clinic_models.nota import Nota
from src.clinic_models.orden import Orden
from src.clinic_models.produccion import Produccion
from src.clinic_models.profesional import Profesional
from src.clinic_models.proveedor import Proveedor

# =========================================================================
# CONFIG (15 tablas)
# =========================================================================
from src.clinic_models.tipo_tratamiento import TipoTratamiento        # LISTA A
from src.clinic_models.fuente_captacion import FuenteCaptacion         # LISTA B
from src.clinic_models.status_lead import StatusLead                   # LISTA C
from src.clinic_models.estado_paciente import EstadoPaciente           # LISTA D
from src.clinic_models.tipo_encuesta import TipoEncuesta               # LISTA E
from src.clinic_models.tipo_gasto import TipoGasto                     # LISTA F
from src.clinic_models.metodo_pago import MetodoPago                   # LISTA G
from src.clinic_models.estado_pago import EstadoPago                   # LISTA G1
from src.clinic_models.unidad_medida import UnidadMedida               # LISTA H
from src.clinic_models.estado_tratamiento import EstadoTratamiento     # LISTA I
from src.clinic_models.estado_sesion import EstadoSesion               # LISTA J
from src.clinic_models.insumo_packaging import InsumoPackaging         # LISTA L
from src.clinic_models.categoria_pago import CategoriaPago             # LISTA M
from src.clinic_models.unidad_negocio import UnidadNegocio             # LISTA N
from src.clinic_models.horario_atencion import HorarioAtencion         # LISTA O

__all__ = [
    # Base
    "ClinicBase",
    # Operacional (16)
    "Paciente",
    "Lead",
    "Sesion",
    "Pago",
    "Presupuesto",
    "Tarifario",
    "Alineador",
    "Conciliacion",
    "Factura",
    "Gasto",
    "InsumoStock",
    "Nota",
    "Orden",
    "Produccion",
    "Profesional",
    "Proveedor",
    # Config (15)
    "TipoTratamiento",
    "FuenteCaptacion",
    "StatusLead",
    "EstadoPaciente",
    "TipoEncuesta",
    "TipoGasto",
    "MetodoPago",
    "EstadoPago",
    "UnidadMedida",
    "EstadoTratamiento",
    "EstadoSesion",
    "InsumoPackaging",
    "CategoriaPago",
    "UnidadNegocio",
    "HorarioAtencion",
]
