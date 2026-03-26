"""Seed baseline de municipios configurados

Revision ID: c9f1a2d4e7b3
Revises: b6c4d2e8f1a0
Create Date: 2026-03-26 17:12:00.746423

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9f1a2d4e7b3'
down_revision = 'b6c4d2e8f1a0'
branch_labels = None
depends_on = None


MUNICIPIOS = [{'nome': 'Canoas', 'url_certidao': 'https://sistemas.canoas.rs.gov.br/e-agata/servlet/hwscertidaonegativadebito?3', 'automacao_ativa': True, 'validade_dias': 90, 'usar_slow_typing': False, 'config_automacao': '{"after_cnpj": [{"tipo": "click", "by": "name", "locator": "BUTTONIMPRIMIR"}]}', 'cnpj_field_id': 'vCPFCNPJ', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Capao da Canoa', 'url_certidao': 'https://e-gov.betha.com.br/cdweb/03114-527/contribuinte/rel_cndcontribuinte.faces', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': True, 'config_automacao': '{"before_cnpj": [{"tipo": "select", "by": "id", "locator": "mainForm:estados", "text": "RS - Rio Grande do Sul"}, {"tipo": "wait_for", "by": "id", "locator": "mainForm:municipios", "timeout": 10, "state": "clickable"}, {"tipo": "select", "by": "id", "locator": "mainForm:municipios", "text_contains": "CAPÃO DA CANOA"}, {"tipo": "click_js", "by": "id", "locator": "mainForm:selecionar"}, {"tipo": "click", "by": "xpath", "locator": "//a[contains(@class,\'boxMenu\') and .//span[normalize-space()=\'Certidão negativa de contribuinte\']]"}], "after_cnpj": [{"tipo": "click", "by": "id", "locator": "mainForm:btCnpj"}, {"tipo": "click", "by": "css_selector", "locator": "img[title=\'Emite a CND para este contribuinte\']"}]}', 'cnpj_field_id': 'mainForm:cnpj', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': 'a.dontCancelClick.cnpj.btModo', 'pre_fill_click_by': 'css_selector', 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Cidreira', 'url_certidao': 'https://cidreira.multi24h.com.br/multi24/sistemas/portal/#tab-emitir-certidoes', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"before_cnpj": [{"tipo": "refresh"}, {"tipo": "click", "by": "class_name", "locator": "emitir-certidoes"}, {"tipo": "click", "by": "xpath", "locator": "//a[contains(text(), \'CNPJ\')]"}], "after_cnpj": [{"tipo": "click", "by": "id", "locator": "btn_buscar_cadastros"}, {"tipo": "click", "by": "css_selector", "locator": "button[data-tipo=\'1\'].btn-info"}]}', 'cnpj_field_id': 'emitir_certidoes[cnpj]', 'by': 'name', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Gravataí', 'url_certidao': 'https://gravatai.atende.net/autoatendimento/servicos/embed/data/eyJpZCI6ImVsLWljMzg2MGQyOTFhIiwiY29kaWdvIjoiMzYiLCJ0aXBvIjoiMSIsInBhcmFtZXRybyI6e30sImNoYXZlIjp7fSwicHJveHkiOnRydWV9/servicos/certidao-negativa-de-debitos/detalhar/1', 'automacao_ativa': True, 'validade_dias': 90, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "wait_for", "by": "name", "locator": "opcaoEmissao", "timeout": 120, "state": "clickable"}, {"tipo": "select", "by": "name", "locator": "opcaoEmissao", "text_contains": "CNPJ"}, {"tipo": "fill", "by": "name", "locator": "cpfCnpj", "value": "cnpj"}, {"tipo": "select", "by": "name", "locator": "FinalidadeCertidaoDebito.codigo", "text_contains": "CONTRIBUINTE"}, {"tipo": "click", "by": "name", "locator": "confirmar"}]}', 'cnpj_field_id': 'cpfCnpj', 'by': 'name', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Imbe', 'url_certidao': 'https://grp.imbe.rs.gov.br/grp/acessoexterno/programaAcessoExterno.faces?codigo=689513', 'automacao_ativa': True, 'validade_dias': 90, 'usar_slow_typing': False, 'config_automacao': '{"before_cnpj": [], "after_cnpj": [], "imbe_variantes": {"geral": {"url": "https://grp.imbe.rs.gov.br/grp/acessoexterno/programaAcessoExterno.faces?codigo=684509", "cnpj_field_id": "form:cnpjD", "by": "name", "pre_fill_click_id": "input[value=\'J\']", "pre_fill_click_by": "css_selector"}}}', 'cnpj_field_id': "input[id='form:cnpjDI']", 'by': 'css_selector', 'inscricao_field_id': "input[id='form:inscricaoDI']", 'inscricao_field_by': 'css_selector', 'pre_fill_click_id': "input[value='J']", 'pre_fill_click_by': 'css_selector', 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Novo Hamburgo', 'url_certidao': 'https://novohamburgo.atende.net/autoatendimento/servicos/embed/data/eyJpZCI6ImVsLWkzNTY2MjMyNGYzIiwiY29kaWdvIjoiMzYiLCJ0aXBvIjoiMSIsInBhcmFtZXRybyI6e30sImNoYXZlIjp7fSwicHJveHkiOnRydWV9/servicos/certidao-negativa-de-debitos/detalhar/1', 'automacao_ativa': True, 'validade_dias': 60, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "wait_for", "by": "name", "locator": "opcaoEmissao", "timeout": 120, "state": "clickable"}, {"tipo": "select", "by": "name", "locator": "opcaoEmissao", "text_contains": "CNPJ"}, {"tipo": "fill", "by": "name", "locator": "cpfCnpj", "value": "cnpj"}, {"tipo": "select", "by": "name", "locator": "FinalidadeCertidaoDebito.codigo", "text_contains": "PMNH"}, {"tipo": "click", "by": "name", "locator": "confirmar"}]}', 'cnpj_field_id': 'cpfCnpj', 'by': 'name', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Osorio', 'url_certidao': 'https://osorio.atende.net/autoatendimento/servicos/embed/data/eyJpZCI6ImVsLWk3MjRhMzA5ZjcwIiwiY29kaWdvIjoiMzYiLCJ0aXBvIjoiMSIsInBhcmFtZXRybyI6e30sImNoYXZlIjp7fSwicHJveHkiOnRydWV9/servicos/certidao-negativa-de-debitos/detalhar/1', 'automacao_ativa': True, 'validade_dias': 90, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "wait_for", "by": "name", "locator": "opcaoEmissao", "timeout": 120, "state": "clickable"}, {"tipo": "select", "by": "name", "locator": "opcaoEmissao", "text_contains": "CNPJ"}, {"tipo": "fill", "by": "name", "locator": "cpfCnpj", "value": "cnpj"}, {"tipo": "select", "by": "name", "locator": "FinalidadeCertidaoDebito.codigo", "text_contains": "CONTRIBUINTE"}, {"tipo": "click", "by": "name", "locator": "confirmar"}]}', 'cnpj_field_id': 'cpfCnpj', 'by': 'name', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Ponta Pora', 'url_certidao': 'https://sia.pontapora.ms.gov.br/servicosweb/home.jsf', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "click", "by": "xpath", "locator": "//a[span[contains(text(), \'Contribuinte\')]]"}, {"tipo": "click", "by": "xpath", "locator": "//input[@type=\'radio\' and @value=\'J\']"}, {"tipo": "fill", "by": "id", "locator": "compInformarContribuinte:formNumero:itIdent", "value": "cnpj"}, {"tipo": "click", "by": "id", "locator": "compInformarContribuinte:formNumero:btnValidar"}, {"tipo": "click", "by": "id", "locator": "formContribuinte:repeat:1:clLinkImobiliario"}, {"tipo": "click", "by": "xpath", "locator": "//span[contains(@class, \'ui-button-text\') and contains(text(), \'Imprimir\')]"}]}', 'cnpj_field_id': 'compInformarContribuinte:formNumero:itIdent', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Porto Alegre', 'url_certidao': 'https://siat.procempa.com.br/siat/ArrSolicitarCertidaoGeralDebTributarios_Internet.do', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill":false,"before_cnpj":[{"tipo":"click","by":"id","locator":"gwt-uid-2","sleep":0.6}],"after_cnpj":[]}', 'cnpj_field_id': "input.gwt-TextBox[maxlength='18'][size='23']", 'by': 'css_selector', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Sao Paulo', 'url_certidao': 'https://duc.prefeitura.sp.gov.br/certidoes/forms_anonimo/frmConsultaEmissaoCertificado.aspx', 'automacao_ativa': False, 'validade_dias': 180, 'usar_slow_typing': False, 'config_automacao': None, 'cnpj_field_id': 'ctl00_ConteudoPrincipal_txtCNPJ', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Sapucaia do Sul', 'url_certidao': 'https://sapucaiadosul.multi24h.com.br/multi24/sistemas/portal/#tab-emitir-certidoes', 'automacao_ativa': True, 'validade_dias': 120, 'usar_slow_typing': False, 'config_automacao': '{"before_cnpj": [{"tipo": "refresh"}, {"tipo": "click", "by": "class_name", "locator": "emitir-certidoes"}, {"tipo": "click", "by": "xpath", "locator": "//a[contains(text(), \'CNPJ\')]"}], "after_cnpj": [{"tipo": "click", "by": "id", "locator": "btn_buscar_cadastros"}, {"tipo": "click", "by": "css_selector", "locator": "button[data-tipo=\'1\'].btn-info"}]}', 'cnpj_field_id': 'emitir_certidoes[cnpj]', 'by': 'name', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Sorriso', 'url_certidao': 'https://prefsorriso-mt.agilicloud.com.br/portal/sorriso/#/certidao', 'automacao_ativa': True, 'validade_dias': 60, 'usar_slow_typing': False, 'config_automacao': '{"after_cnpj": [{"tipo": "click", "by": "id", "locator": "btnImprimirCertidaoDebitos"}]}', 'cnpj_field_id': 'cpfcnpjCertidoes', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': 'input[name="tipoPessoa"][value="99.999.999/9999-99"]', 'pre_fill_click_by': 'css_selector', 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Tramandai', 'url_certidao': 'https://ecidadeonline.tramandai.rs.gov.br/certidaonome003.php', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"after_cnpj": [{"tipo": "click", "by": "name", "locator": "pesquisa"}, {"tipo": "click", "by": "xpath", "locator": "//a[contains(@class,\'links\') and contains(normalize-space(.), \'Emitir Certidão\')]"}]}', 'cnpj_field_id': 'cgc', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Xangri-Lá', 'url_certidao': 'https://xangrila.msgestaopublica.app.br:8443/servicosweb/home.jsf', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "click", "by": "xpath", "locator": "//a[span[contains(text(), \'Contribuinte\')]]"}, {"tipo": "click", "by": "xpath", "locator": "//input[@type=\'radio\' and @value=\'J\']"}, {"tipo": "fill", "by": "id", "locator": "compInformarContribuinte:formNumero:itIdent", "value": "cnpj"}, {"tipo": "click", "by": "id", "locator": "compInformarContribuinte:formNumero:btnValidar"}, {"tipo": "click", "by": "id", "locator": "formContribuinte:repeat:1:clLinkImobiliario"}, {"tipo": "click", "by": "xpath", "locator": "//span[contains(@class, \'ui-button-text\') and contains(text(), \'Imprimir\')]"}]}', 'cnpj_field_id': 'compInformarContribuinte:formNumero:itIdent', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}, {'nome': 'Xangrila', 'url_certidao': 'https://xangrila.msgestaopublica.app.br:8443/servicosweb/home.jsf', 'automacao_ativa': True, 'validade_dias': 30, 'usar_slow_typing': False, 'config_automacao': '{"skip_cnpj_fill": true, "before_cnpj": [{"tipo": "click", "by": "xpath", "locator": "//a[span[contains(text(), \'Contribuinte\')]]"}, {"tipo": "click", "by": "xpath", "locator": "//input[@type=\'radio\' and @value=\'J\']"}, {"tipo": "fill", "by": "id", "locator": "compInformarContribuinte:formNumero:itIdent", "value": "cnpj"}, {"tipo": "click", "by": "id", "locator": "compInformarContribuinte:formNumero:btnValidar"}, {"tipo": "click", "by": "id", "locator": "formContribuinte:repeat:1:clLinkImobiliario"}, {"tipo": "click", "by": "xpath", "locator": "//span[contains(@class, \'ui-button-text\') and contains(text(), \'Imprimir\')]"}]}', 'cnpj_field_id': 'compInformarContribuinte:formNumero:itIdent', 'by': 'id', 'inscricao_field_id': None, 'inscricao_field_by': None, 'pre_fill_click_id': None, 'pre_fill_click_by': None, 'shadow_host_selector': None, 'inner_input_selector': None}]


def upgrade():
    bind = op.get_bind()

    for item in MUNICIPIOS:
        existente = bind.execute(
            sa.text('SELECT id FROM municipio WHERE UPPER(nome) = UPPER(:nome)'),
            {'nome': item['nome']}
        ).first()

        if existente:
            bind.execute(
                sa.text(
                    """
                    UPDATE municipio
                       SET url_certidao = :url_certidao,
                           automacao_ativa = :automacao_ativa,
                           validade_dias = :validade_dias,
                           usar_slow_typing = :usar_slow_typing,
                           config_automacao = :config_automacao,
                           cnpj_field_id = :cnpj_field_id,
                           `by` = :by,
                           inscricao_field_id = :inscricao_field_id,
                           inscricao_field_by = :inscricao_field_by,
                           pre_fill_click_id = :pre_fill_click_id,
                           pre_fill_click_by = :pre_fill_click_by,
                           shadow_host_selector = :shadow_host_selector,
                           inner_input_selector = :inner_input_selector
                     WHERE UPPER(nome) = UPPER(:nome)
                    """
                ),
                item
            )
        else:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO municipio (
                        nome,
                        url_certidao,
                        automacao_ativa,
                        validade_dias,
                        usar_slow_typing,
                        config_automacao,
                        cnpj_field_id,
                        `by`,
                        inscricao_field_id,
                        inscricao_field_by,
                        pre_fill_click_id,
                        pre_fill_click_by,
                        shadow_host_selector,
                        inner_input_selector
                    ) VALUES (
                        :nome,
                        :url_certidao,
                        :automacao_ativa,
                        :validade_dias,
                        :usar_slow_typing,
                        :config_automacao,
                        :cnpj_field_id,
                        :by,
                        :inscricao_field_id,
                        :inscricao_field_by,
                        :pre_fill_click_id,
                        :pre_fill_click_by,
                        :shadow_host_selector,
                        :inner_input_selector
                    )
                    """
                ),
                item
            )


def downgrade():
    # Seed baseline: não remove dados para evitar perda de configuração em ambientes ativos.
    pass
