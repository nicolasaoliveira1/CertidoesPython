"""Adiciona a_vencer_dias por tipo de certidao

Revision ID: a1b2c3d4e5f6
Revises: f3b9c2d1a7e4
Branch Labels: None
Depends On: None

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f3b9c2d1a7e4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('configuracao_sistema') as batch_op:
        batch_op.add_column(sa.Column('a_vencer_dias_federal', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('a_vencer_dias_fgts', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('a_vencer_dias_estadual', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('a_vencer_dias_municipal', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('a_vencer_dias_trabalhista', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('configuracao_sistema') as batch_op:
        batch_op.drop_column('a_vencer_dias_trabalhista')
        batch_op.drop_column('a_vencer_dias_municipal')
        batch_op.drop_column('a_vencer_dias_estadual')
        batch_op.drop_column('a_vencer_dias_fgts')
        batch_op.drop_column('a_vencer_dias_federal')
