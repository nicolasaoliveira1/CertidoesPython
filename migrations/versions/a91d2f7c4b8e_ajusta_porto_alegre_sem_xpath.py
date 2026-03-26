"""Ajusta Porto Alegre para seletores sem XPath

Revision ID: a91d2f7c4b8e
Revises: f4a91d6c2b3e
Create Date: 2026-03-26 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision = 'a91d2f7c4b8e'
down_revision = 'f4a91d6c2b3e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    config_automacao = json.dumps(
        {
            'skip_cnpj_fill': False,
            'before_cnpj': [
                {
                    'tipo': 'click',
                    'by': 'id',
                    'locator': 'gwt-uid-2',
                    'sleep': 0.6,
                }
            ],
            'after_cnpj': []
        },
        ensure_ascii=False,
        separators=(',', ':')
    )

    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET config_automacao = :config_automacao,
                   cnpj_field_id = :cnpj_field_id,
                   `by` = :by
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'config_automacao': config_automacao,
            'cnpj_field_id': "input.gwt-TextBox[maxlength='18'][size='23']",
            'by': 'css_selector',
            'nome': 'Porto Alegre',
        }
    )


def downgrade():
    bind = op.get_bind()

    config_automacao = json.dumps(
        {
            'skip_cnpj_fill': True,
            'before_cnpj': [
                {
                    'tipo': 'click',
                    'by': 'xpath',
                    'locator': '/html/body/table/tbody/tr[2]/td/table/tbody/tr/td/div/div/div[3]/table/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td/div/div[1]/table/tbody/tr[1]/td/table/tbody/tr[2]/td[2]/div/table/tbody/tr[1]/td[2]/table/tbody/tr/td[3]/span/input',
                    'sleep': 0.6,
                },
                {
                    'tipo': 'fill',
                    'by': 'xpath',
                    'locator': '/html/body/table/tbody/tr[2]/td/table/tbody/tr/td/div/div/div[3]/table/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr[2]/td/div/div[1]/table/tbody/tr[1]/td/table/tbody/tr[2]/td[2]/div/table/tbody/tr[3]/td[2]/input',
                    'value': 'cnpj',
                    'sleep': 0.5,
                }
            ],
            'after_cnpj': []
        },
        ensure_ascii=False,
        separators=(',', ':')
    )

    bind.execute(
        sa.text(
            """
            UPDATE municipio
               SET config_automacao = :config_automacao,
                   cnpj_field_id = NULL,
                   `by` = NULL
             WHERE UPPER(nome) = UPPER(:nome)
            """
        ),
        {
            'config_automacao': config_automacao,
            'nome': 'Porto Alegre',
        }
    )
