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
        'RS': {
            'url': 'https://www.sefaz.rs.gov.br/sat/CertidaoSitFiscalSolic.aspx',
            'cnpj_field_id': 'campoCnpj',
            'by': 'name'
        },
         'SP': {
            'url': 'https://www10.fazenda.sp.gov.br/CertidaoNegativaDeb/Pages/EmissaoCertidaoNegativa.aspx',
            'pre_fill_click_id': "input[value='cnpjradio']",
            'pre_fill_click_by': 'css_selector',
            'cnpj_field_id': 'MainContent_txtDocumento',
            'by': 'id'
        },
        'MT': {
            'url': 'https://www.sefaz.mt.gov.br/cnd/certidao/servlet/ServletRotd?origem=60',
            'pre_fill_click_id': "input[value='CNPJ']",
            'pre_fill_click_by': 'css_selector',
            'cnpj_field_id': 'numeroDocumento',
            'by': 'name',
            'slow_typing': True
        }
    },
    
    'TRABALHISTA': {
        'url': 'https://cndt-certidao.tst.jus.br/inicio.faces',
        'pre_fill_click_id': "input[value='Emitir Certidão']",
        'pre_fill_click_by': 'css_selector',                  
        'cnpj_field_id': 'gerarCertidaoForm:cpfCnpj',
        'by': 'id'
    }
}