"""Corrige fluxo Tramandai: emitir antes de validar negativa

Revision ID: f2a7d1c9e4b6
Revises: e1d9c7a4b2f0
Create Date: 2026-03-27 11:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a7d1c9e4b6'
down_revision = 'e1d9c7a4b2f0'
branch_labels = None
depends_on = None


CONFIG_TRAMANDAI_CORRIGIDO = (
    '{"after_cnpj": ['
    '{"tipo": "click", "by": "name", "locator": "pesquisa", "sleep": 0.7}, '
    '{"tipo": "click", "by": "xpath", "locator": "//a[contains(@class,\'links\') and contains(normalize-space(.), \'Emitir Certidão\')]", "sleep": 0.7}, '
    '{"tipo": "click_if_text_or_close", "by": "xpath", "locator": "//a[contains(@class, \'links\')]", '
    '"expected_text_contains": "NEGATIVA", "wait_url_contains": "cai3_certidao.php", "timeout": 20, "sleep": 0.7}'
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
            'config_automacao': CONFIG_TRAMANDAI_CORRIGIDO,
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
            'config_automacao': '{"after_cnpj": [{"tipo": "click", "by": "name", "locator": "pesquisa", "sleep": 0.7}, {"tipo": "click_if_text_or_close", "by": "xpath", "locator": "//a[contains(@class, \'links\')]", "expected_text_contains": "NEGATIVA", "timeout": 10, "sleep": 0.7}]}',
        }
    )
