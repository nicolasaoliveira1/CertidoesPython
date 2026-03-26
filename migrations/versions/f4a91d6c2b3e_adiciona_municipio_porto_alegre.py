"""Adiciona configuracao municipal de Porto Alegre

Revision ID: f4a91d6c2b3e
Revises: e2f7c1a9f2b4
Create Date: 2026-03-26 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision = 'f4a91d6c2b3e'
down_revision = 'e2f7c1a9f2b4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    municipio = sa.table(
        'municipio',
        sa.column('nome', sa.String()),
        sa.column('url_certidao', sa.String()),
        sa.column('automacao_ativa', sa.Boolean()),
        sa.column('validade_dias', sa.Integer()),
        sa.column('usar_slow_typing', sa.Boolean()),
        sa.column('config_automacao', sa.Text()),
        sa.column('cnpj_field_id', sa.String()),
        sa.column('by', sa.String()),
        sa.column('inscricao_field_id', sa.String()),
        sa.column('inscricao_field_by', sa.String()),
        sa.column('pre_fill_click_id', sa.String()),
        sa.column('pre_fill_click_by', sa.String()),
        sa.column('shadow_host_selector', sa.String()),
        sa.column('inner_input_selector', sa.String()),
    )

    nome = 'Porto Alegre'
    url = 'https://siat.procempa.com.br/siat/ArrSolicitarCertidaoGeralDebTributarios_Internet.do'

    radio_cnpj_id = 'gwt-uid-2'
    campo_cnpj_css = "input.gwt-TextBox[maxlength='18'][size='23']"

    config_automacao = json.dumps(
        {
            'skip_cnpj_fill': False,
            'before_cnpj': [
                {
                    'tipo': 'click',
                    'by': 'id',
                    'locator': radio_cnpj_id,
                    'sleep': 0.6,
                }
            ],
            'after_cnpj': []
        },
        ensure_ascii=False,
        separators=(',', ':')
    )

    ja_existe = bind.execute(
        sa.text('SELECT id FROM municipio WHERE UPPER(nome) = UPPER(:nome)'),
        {'nome': nome}
    ).first()

    if ja_existe:
        return

    bind.execute(
        municipio.insert().values(
            nome=nome,
            url_certidao=url,
            automacao_ativa=True,
            validade_dias=None,
            usar_slow_typing=False,
            config_automacao=config_automacao,
            cnpj_field_id=campo_cnpj_css,
            by='css_selector',
            inscricao_field_id=None,
            inscricao_field_by=None,
            pre_fill_click_id=None,
            pre_fill_click_by=None,
            shadow_host_selector=None,
            inner_input_selector=None,
        )
    )


def downgrade():
    bind = op.get_bind()

    bind.execute(
        sa.text(
            'DELETE FROM municipio WHERE nome = :nome AND url_certidao = :url_certidao'
        ),
        {
            'nome': 'Porto Alegre',
            'url_certidao': 'https://siat.procempa.com.br/siat/ArrSolicitarCertidaoGeralDebTributarios_Internet.do'
        }
    )
