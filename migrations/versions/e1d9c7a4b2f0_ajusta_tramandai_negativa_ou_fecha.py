"""Ajusta fluxo de Tramandai para clicar NEGATIVA ou fechar janela

Revision ID: e1d9c7a4b2f0
Revises: c9f1a2d4e7b3
Create Date: 2026-03-27 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1d9c7a4b2f0'
down_revision = 'c9f1a2d4e7b3'
branch_labels = None
depends_on = None


CONFIG_TRAMANDAI = (
    '{"after_cnpj": ['
    '{"tipo": "click", "by": "name", "locator": "pesquisa", "sleep": 0.7}, '
    '{"tipo": "click_if_text_or_close", "by": "xpath", "locator": "//a[contains(@class, \'links\')]", '
    '"expected_text_contains": "NEGATIVA", "timeout": 10, "sleep": 0.7}'
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
            'nome': 'Tramandai',
            'config_automacao': CONFIG_TRAMANDAI,
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
            'nome': 'Tramandai',
            'config_automacao': '{"after_cnpj": [{"tipo": "click", "by": "name", "locator": "pesquisa"}, {"tipo": "click", "by": "xpath", "locator": "//a[contains(@class,\'links\') and contains(normalize-space(.), \'Emitir Certidão\')]"}]}',
        }
    )
