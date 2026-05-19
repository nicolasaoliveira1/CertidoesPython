"""Cria tabela configuracao_sistema

Revision ID: f3b9c2d1a7e4
Revises: e6f2c1b9a4d8
Create Date: 2026-05-19 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b9c2d1a7e4'
down_revision = 'e6f2c1b9a4d8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'configuracao_sistema',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('a_vencer_dias', sa.Integer(), nullable=False, server_default='7'),
    )


def downgrade():
    op.drop_table('configuracao_sistema')
