"""Enriquece municipio com campos de automacao

Revision ID: 7c3f5a2b9d10
Revises: daa6f22ace0d
Create Date: 2026-02-05 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c3f5a2b9d10'
down_revision = 'daa6f22ace0d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('municipio', schema=None) as batch_op:
        batch_op.add_column(sa.Column('automacao_ativa', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('validade_dias', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('usar_slow_typing', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('config_automacao', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('municipio', schema=None) as batch_op:
        batch_op.drop_column('config_automacao')
        batch_op.drop_column('usar_slow_typing')
        batch_op.drop_column('validade_dias')
        batch_op.drop_column('automacao_ativa')
