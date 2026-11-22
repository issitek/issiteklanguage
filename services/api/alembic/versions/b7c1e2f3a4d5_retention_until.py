"""retención explícita de grabaciones del alumno

Revision ID: b7c1e2f3a4d5
Revises: 5ebfd9175ba2
Create Date: 2026-11-22

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b7c1e2f3a4d5"
down_revision = "5ebfd9175ba2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "speech_assets",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    # Filas existentes: 30 días desde su creación (valor por defecto de F1).
    op.execute(
        "UPDATE speech_assets "
        "SET retention_until = created_at + interval '30 days' "
        "WHERE retention_until IS NULL"
    )
    op.alter_column("speech_assets", "retention_until", nullable=False)
    op.create_index(
        "idx_speech_assets_retention",
        "speech_assets",
        ["retention_until"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_speech_assets_retention", table_name="speech_assets")
    op.drop_column("speech_assets", "retention_until")
