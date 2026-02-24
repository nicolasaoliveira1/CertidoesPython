"""Adiciona caminho_arquivo em certidao

Revision ID: e2f7c1a9f2b4
Revises: b1c8f6b2a1d9
Create Date: 2026-02-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f7c1a9f2b4'
down_revision = 'b1c8f6b2a1d9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('certidao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('caminho_arquivo', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('certidao', schema=None) as batch_op:
        batch_op.drop_column('caminho_arquivo')
