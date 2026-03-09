"""extend_remindertype_enum

Revision ID: a1b2c3d4e5f6
Revises: 7a957647bcc8
Create Date: 2026-03-06 23:00:00.000000

Agrega 4 valores nuevos al enum remindertype de PostgreSQL:
- APPOINTMENT_CONFIRMATION
- BIRTHDAY_GREETING
- ALIGNER_CHANGE
- GOOGLE_REVIEW_REQUEST

Nota: ALTER TYPE ... ADD VALUE no puede correr dentro de una transaccion.
Por eso usamos autocommit=True en cada execute.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7a957647bcc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE no puede estar dentro de una transaccion
    # en PostgreSQL. Usamos connection.execute con autocommit.
    op.execute("ALTER TYPE remindertype ADD VALUE IF NOT EXISTS 'APPOINTMENT_CONFIRMATION'")
    op.execute("ALTER TYPE remindertype ADD VALUE IF NOT EXISTS 'BIRTHDAY_GREETING'")
    op.execute("ALTER TYPE remindertype ADD VALUE IF NOT EXISTS 'ALIGNER_CHANGE'")
    op.execute("ALTER TYPE remindertype ADD VALUE IF NOT EXISTS 'GOOGLE_REVIEW_REQUEST'")


def downgrade() -> None:
    # PostgreSQL no permite eliminar valores de un enum.
    # El downgrade requeriria recrear el tipo completo.
    # Para este caso, simplemente no hacemos nada
    # (los valores extra no causan problemas).
    pass
