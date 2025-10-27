SITES_CERTIDOES = {
    'FEDERAL': {
        'url': 'https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj',
        'cnpj_field_id': 'input[id^="id"][name="niContribuinte"]',
        'by': 'css_selector'
    },
    'FGTS': {
        'url': 'https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf',
        'cnpj_field_id': 'mainForm:txtInscricao1',
        'by': 'id' 
    },
    'ESTADUAL': {
        'url': 'https://www.sefaz.rs.gov.br/sat/CertidaoSitFiscalSolic.aspx',
        'cnpj_field_id': 'campoCnpj',
        'by': 'name' 
    },
    'TRABALHISTA': {
        'url': 'https://cndt-certidao.tst.jus.br/inicio.faces',
        'pre_fill_click_id': "input[value='Emitir Certidão']",
        'pre_fill_click_by': 'css_selector',                  
        'cnpj_field_id': 'gerarCertidaoForm:cpfCnpj',
        'by': 'id'
    },
    'MUNICIPAL': {
        'url': '#',
        'cnpj_field_id': None,
        'by': None
    }
}