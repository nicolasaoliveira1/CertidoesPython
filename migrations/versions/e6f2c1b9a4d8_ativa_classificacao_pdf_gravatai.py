"""Ativa classificacao de status via PDF para Gravatai

Revision ID: e6f2c1b9a4d8
Revises: d4b8e1a9c3f7
Create Date: 2026-03-27 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6f2c1b9a4d8'
down_revision = 'd4b8e1a9c3f7'
branch_labels = None
depends_on = None


CONFIG_GRAVATAI_COM_CLASSIFICACAO = (
    '{"skip_cnpj_fill": true, "classificar_pdf_status": true, "before_cnpj": ['
    '{"tipo": "wait_for", "by": "name", "locator": "opcaoEmissao", "timeout": 120, "state": "clickable"}, '
    '{"tipo": "select", "by": "name", "locator": "opcaoEmissao", "text_contains": "CNPJ"}, '
    '{"tipo": "fill", "by": "name", "locator": "cpfCnpj", "value": "cnpj"}, '
    '{"tipo": "select", "by": "name", "locator": "FinalidadeCertidaoDebito.codigo", "text_contains": "CONTRIBUINTE"}, '
    '{"tipo": "click", "by": "name", "locator": "confirmar"}'
    ']}'
)


CONFIG_GRAVATAI_ANTERIOR = (
    '{"skip_cnpj_fill": true, "before_cnpj": ['
    '{"tipo": "wait_for", "by": "name", "locator": "opcaoEmissao", "timeout": 120, "state": "clickable"}, '
    '{"tipo": "select", "by": "name", "locator": "opcaoEmissao", "text_contains": "CNPJ"}, '
    '{"tipo": "fill", "by": "name", "locator": "cpfCnpj", "value": "cnpj"}, '
    '{"tipo": "select", "by": "name", "locator": "FinalidadeCertidaoDebito.codigo", "text_contains": "CONTRIBUINTE"}, '
    '{"tipo": "click", "by": "name", "locator": "confirmar"}'
    ']}'
)


def upgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET config_automacao = :config_automacao
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'nome': 'Gravataí',
            'config_automacao': CONFIG_GRAVATAI_COM_CLASSIFICACAO,
        }
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET config_automacao = :config_automacao
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'nome': 'Gravataí',
            'config_automacao': CONFIG_GRAVATAI_ANTERIOR,
        }
    )
