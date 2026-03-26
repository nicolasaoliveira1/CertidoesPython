"""Define validade de Porto Alegre em 30 dias

Revision ID: b6c4d2e8f1a0
Revises: a91d2f7c4b8e
Create Date: 2026-03-26 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b6c4d2e8f1a0'
down_revision = 'a91d2f7c4b8e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET validade_dias = :validade_dias
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'validade_dias': 30,
            'nome': 'Porto Alegre',
        }
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET validade_dias = NULL
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'nome': 'Porto Alegre',
        }
    )
