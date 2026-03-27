"""Ajusta seletor Tramandai para link javascript da certidao

Revision ID: d4b8e1a9c3f7
Revises: f2a7d1c9e4b6
Create Date: 2026-03-27 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4b8e1a9c3f7'
down_revision = 'f2a7d1c9e4b6'
branch_labels = None
depends_on = None


CONFIG_TRAMANDAI_SELETOR_JS = (
    '{"after_cnpj": ['
    '{"tipo": "click", "by": "name", "locator": "pesquisa", "sleep": 0.7}, '
    '{"tipo": "click", "by": "xpath", "locator": "//a[contains(@class,\'links\') and contains(normalize-space(.), \'Emitir Certidão\')]", "sleep": 0.7}, '
    '{"tipo": "click_if_text_or_close", "by": "css_selector", "locator": "a[href*=\'js_certidao(\']", '
    '"expected_text_contains": "NEGATIVA", "wait_url_contains": "cai3_certidao.php", "timeout": 20, "sleep": 0.7}'
    ']}'
)


CONFIG_TRAMANDAI_ANTERIOR = (
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
            'config_automacao': CONFIG_TRAMANDAI_SELETOR_JS,
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
            'config_automacao': CONFIG_TRAMANDAI_ANTERIOR,
        }
    )
