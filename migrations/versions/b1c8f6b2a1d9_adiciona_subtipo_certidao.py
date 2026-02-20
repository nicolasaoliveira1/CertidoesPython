"""Adiciona subtipo em certidao

Revision ID: b1c8f6b2a1d9
Revises: 7c3f5a2b9d10
Create Date: 2026-02-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import unicodedata


# revision identifiers, used by Alembic.
revision = 'b1c8f6b2a1d9'
down_revision = '7c3f5a2b9d10'
branch_labels = None
depends_on = None


def _normalizar(texto):
    if not texto:
        return ''
    normalized = unicodedata.normalize('NFD', texto)
    sem_acentos = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    return sem_acentos.upper().strip()


def upgrade():
    subtipo_enum = sa.Enum('Geral', 'Mobiliário', name='subtipocertidao')
    subtipo_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table('certidao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subtipo', subtipo_enum, nullable=True))

    conn = op.get_bind()
    empresas = conn.execute(sa.text('SELECT id, cidade FROM empresa')).fetchall()
    imbe_ids = [row[0] for row in empresas if _normalizar(row[1]) == 'IMBE']

    if not imbe_ids:
        return

    update_stmt = sa.text(
        'UPDATE certidao SET subtipo = :subtipo '
        'WHERE tipo = :tipo AND empresa_id IN :ids'
    ).bindparams(sa.bindparam('ids', expanding=True))

    conn.execute(update_stmt, {
        'subtipo': 'Mobiliário',
        'tipo': 'MUNICIPAL',
        'ids': imbe_ids
    })

    select_stmt = sa.text(
        'SELECT empresa_id, data_validade, status_especial '
        'FROM certidao '
        'WHERE tipo = :tipo AND empresa_id IN :ids AND subtipo = :subtipo'
    ).bindparams(sa.bindparam('ids', expanding=True))

    rows = conn.execute(select_stmt, {
        'tipo': 'MUNICIPAL',
        'ids': imbe_ids,
        'subtipo': 'Mobiliário'
    }).fetchall()

    insert_stmt = sa.text(
        'INSERT INTO certidao (tipo, subtipo, data_validade, empresa_id, status_especial) '
        'VALUES (:tipo, :subtipo, :data_validade, :empresa_id, :status_especial)'
    )

    for row in rows:
        conn.execute(insert_stmt, {
            'tipo': 'MUNICIPAL',
            'subtipo': 'Geral',
            'data_validade': row[1],
            'empresa_id': row[0],
            'status_especial': row[2]
        })


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text('DELETE FROM certidao WHERE subtipo = :subtipo'), {
        'subtipo': 'Geral'
    })

    with op.batch_alter_table('certidao', schema=None) as batch_op:
        batch_op.drop_column('subtipo')

    subtipo_enum = sa.Enum('Geral', 'Mobiliário', name='subtipocertidao')
    subtipo_enum.drop(op.get_bind(), checkfirst=True)