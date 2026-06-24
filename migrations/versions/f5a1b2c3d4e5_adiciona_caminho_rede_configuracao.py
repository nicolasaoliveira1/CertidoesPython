"""Adiciona caminho_rede em configuracao_sistema

Revision ID: f5a1b2c3d4e5
Revises: c1d2e3f4a5b6
Branch Labels: None
Depends On: None

"""
from alembic import op
import sqlalchemy as sa


revision = 'f5a1b2c3d4e5'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_sistema') as batch_op:
        batch_op.add_column(sa.Column('caminho_rede', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('configuracao_sistema') as batch_op:
        batch_op.drop_column('caminho_rede')
