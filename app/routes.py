import os
import time
import string
import random
import base64
import unicodedata
from datetime import date, datetime, timedelta

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.keys import Keys
from sqlalchemy import or_
from webdriver_manager.chrome import ChromeDriverManager

from app import db, file_manager
from app.automation import SITES_CERTIDOES
from app.models import (Certidao, Empresa, Municipio, StatusEspecial,
                        TipoCertidao)

bp = Blueprint('main', __name__)

def _sem_acento(texto: str) -> str:
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

@bp.route('/')
def dashboard():
    status_filtros = request.args.getlist('status')
    query = db.session.query(Empresa).distinct()

    hoje = date.today()

    if not status_filtros:
        status_filtros = ['todas']

    if 'todas' in status_filtros or not status_filtros:
        status_filtros = ['todas']
    else:
        query = query.join(Certidao)

        conditions = []

        if 'validas' in status_filtros:
            conditions.append(Certidao.data_validade >
                              (hoje + timedelta(days=7)))

        if 'a_vencer' in status_filtros:
            conditions.append(Certidao.data_validade.between(
                hoje, hoje + timedelta(days=7)))

        if 'vencidas' in status_filtros:
            conditions.append(
                (Certidao.data_validade < hoje) & (
                    Certidao.status_especial == None)
            )

        if 'pendentes' in status_filtros:
            conditions.append(Certidao.status_especial ==
                              StatusEspecial.PENDENTE)

        if 'nao_definida' in status_filtros:
            conditions.append(Certidao.data_validade == None)

        if conditions:
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(Empresa.id == -1)

    empresas = query.order_by(Empresa.id).all()

    municipios = Municipio.query.all()
    
    urls_municipais = {}
    for m in municipios:
        if not m.url_certidao:
            continue
        nome = (m.nome or '').strip()
        url = m.url_certidao
        
        urls_municipais[nome] = url
        nome_sem = _sem_acento(nome)
        urls_municipais[nome_sem] = url
        
    return render_template(
        'dashboard.html',
        empresas=empresas,
        status_filtros=status_filtros,
        hoje=hoje,
        sites_urls=SITES_CERTIDOES,
        urls_municipais=urls_municipais
    )


@bp.route('/empresa/adicionar', methods=['POST'])
def adicionar_empresa():
    # dados formulário
    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
    estado = request.form.get('estado')
    cidade = request.form.get('cidade')
    inscricao = request.form.get('inscricao_mobiliaria')

    if not cnpj or len(cnpj) < 18:
        flash('CNPJ incompleto, preencha todos os dígitos.', 'warning')
        return redirect(url_for('main.dashboard'))

    # validacao
    empresa_existente = Empresa.query.filter_by(cnpj=cnpj).first()
    if empresa_existente:
        flash(f'Empresa com CNPJ {cnpj} já está cadastrada.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Cria objeto empresa
    nova_empresa = Empresa(
        nome=nome,
        cnpj=cnpj,
        estado=estado,
        cidade=cidade,
        # Garante que seja nulo se vazio
        inscricao_mobiliaria=inscricao if inscricao else None
    )
    db.session.add(nova_empresa)

    for tipo in TipoCertidao:
        nova_certidao = Certidao(
            tipo=tipo, empresa=nova_empresa, data_validade=None)
        db.session.add(nova_certidao)

    # Salva no banco
    try:
        db.session.commit()
        flash(f'Empresa "{nome}" cadastrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar empresa: {e}', 'danger')

    # redirecionamento para dashboard
    return redirect(url_for('main.dashboard'))


@bp.route('/certidao/atualizar/<int:certidao_id>', methods=['POST'])
def atualizar_validade(certidao_id):
    certidao = Certidao.query.get_or_404(certidao_id)
    nova_data_str = request.form.get('nova_validade')

    if nova_data_str:
        nova_data = datetime.strptime(nova_data_str, '%Y-%m-%d').date()
        certidao.data_validade = nova_data
        certidao.status_especial = None

        try:
            db.session.commit()
            flash(
                f"Validade da certidão {certidao.tipo.value} da empresa {certidao.empresa.nome} atualizada com sucesso!", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar validade: {e}", 'danger')
    else:
        flash("Nenhuma data foi fornecida.", 'warning')
    return redirect(url_for('main.dashboard'))


@bp.route('/certidao/marcar_pendente/<int:certidao_id>', methods=['POST'])
def marcar_pendente(certidao_id):
    certidao = Certidao.query.get_or_404(certidao_id)
    certidao.status_especial = StatusEspecial.PENDENTE
    certidao.data_validade = None
    try:
        db.session.commit()
        flash(
            f'Certidão {certidao.tipo.value} da empresa {certidao.empresa.nome} marcada como Pendente.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao marcar como pendente: {e}', 'danger')

    return redirect(url_for('main.dashboard'))

# baixar certidao com automacao salvamento ||||
# VVVV


@bp.route('/certidao/baixar/<int:certidao_id>')
def baixar_certidao(certidao_id):
    file_manager.criar_chave_interrupcao()
    certidao = Certidao.query.get_or_404(certidao_id)
    tipo_certidao_chave = certidao.tipo.name

    if tipo_certidao_chave == 'FEDERAL':
        return redirect("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")

    info_site = {}
    if tipo_certidao_chave != 'MUNICIPAL':
        if tipo_certidao_chave == 'ESTADUAL':
            estado_emp = (certidao.empresa.estado or '').strip().upper()
            estadual_cfg = SITES_CERTIDOES.get('ESTADUAL', {})
            if isinstance(estadual_cfg, dict) and estado_emp in estadual_cfg:
                info_site = estadual_cfg[estado_emp].copy()
            else:
                info_site = SITES_CERTIDOES.get('ESTADUAL', {}).copy()
        else:
            info_site = SITES_CERTIDOES.get(tipo_certidao_chave, {}).copy()

    else:
        cidade_empresa = certidao.empresa.cidade or ''
        cidade_norm = _sem_acento(cidade_empresa).upper()
        regra_municipio = None
        
        for m in Municipio.query.all():
            nome_norm = _sem_acento(m.nome or '').upper()
            if nome_norm == cidade_norm:
                regra_municipio = m
                break
        
        if regra_municipio:
            info_site = {
                'url': regra_municipio.url_certidao,
                'cnpj_field_id': regra_municipio.cnpj_field_id,
                'by': regra_municipio.by,
                'pre_fill_click_id': regra_municipio.pre_fill_click_id,
                'pre_fill_click_by': regra_municipio.pre_fill_click_by,
                'inscricao_field_id': regra_municipio.inscricao_field_id,
                'inscricao_field_by': regra_municipio.inscricao_field_by
            }
            #temporario
            cidade_upper = (certidao.empresa.cidade or '').upper()
            if cidade_upper in ['CAPAO DA CANOA', 'CAPÃO DA CANOA']:
                info_site['slow_typing'] = True
            
        else:
            return jsonify({'status': 'error', 'message': 'Regra municipal não encontrada'})

    cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
    inscricao_limpa = certidao.empresa.inscricao_mobiliaria or ''

    driver = None
    data_encontrada = None
    arquivo_salvo_msg = None
    pular_monitoramento = False

    tempo_inicio = time.time()

    try:
        print(f"--- INICIANDO AUTOMAÇÃO ({tipo_certidao_chave}) ---")

        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        driver = webdriver.Chrome(service=ChromeService(
            ChromeDriverManager().install()), options=chrome_options)
        
        wait = WebDriverWait(driver, 20)
        print(f"1. Acessando a URL: {info_site.get('url')}")
        driver.get(info_site.get('url'))
        
        if tipo_certidao_chave == 'MUNICIPAL':
            if certidao.empresa.cidade.upper() in ['CAPAO DA CANOA', 'CAPÃO DA CANOA']:
                print("--- NAVEGAÇÃO PORTAL CAPÃO DA CANOA ---")
                try:
                    select_estados_el = wait.until(
                        EC.element_to_be_clickable((By.ID, "mainForm:estados"))
                    )
                    select_estados = Select(select_estados_el)
                    select_estados.select_by_visible_text("RS - Rio Grande do Sul")
                    time.sleep(1)

                    def _municipio_capao_carregado(d):
                        try:
                            sel = Select(d.find_element(By.ID, "mainForm:municipios"))
                            return any(
                                "CAPÃO DA CANOA" in opt.text.upper()
                                for opt in sel.options
                            )
                        except Exception:
                            return False

                    WebDriverWait(driver, 5).until(_municipio_capao_carregado)

                    select_municipios_el = driver.find_element(By.ID, "mainForm:municipios")
                    select_municipios = Select(select_municipios_el)
                    for opt in select_municipios.options:
                        if "CAPÃO DA CANOA" in opt.text.upper():
                            select_municipios.select_by_visible_text(opt.text)
                            print(f"Município selecionado: {opt.text}")
                            break

                    time.sleep(1)

                    btn_acessar = wait.until(
                        EC.element_to_be_clickable((By.ID, "mainForm:selecionar"))
                    )
                    driver.execute_script("arguments[0].click();", btn_acessar)
                    print("Botão Acessar clicado.")
                    time.sleep(1)
                    
                    link_certidao = wait.until(EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[contains(@class,'boxMenu') and .//span[normalize-space()='Certidão negativa de contribuinte']]"
                    )))
                    link_certidao.click()
                    time.sleep(1)

                except Exception as e:
                    print(f"Erro na navegação do portal para Capão da Canoa: {e}")
        
        if info_site.get('pre_fill_click_id'):
            click_by_map = {
                'id': By.ID,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH,
                'name': By.NAME
            }
            click_by = click_by_map.get(info_site.get('pre_fill_click_by'))
            if click_by:
                try:
                    elemento_inicial = wait.until(
                        EC.element_to_be_clickable(
                            (click_by, info_site['pre_fill_click_id'])
                        )
                    )
                    elemento_inicial.click()
                    time.sleep(2)
                except Exception:
                    pass

        if tipo_certidao_chave == 'MUNICIPAL':
            if certidao.empresa.cidade.upper() in ['SAO PAULO', 'SÃO PAULO']:
                return jsonify({
                "status": "manual_required",
                "message": "Para São Paulo, use o botão 'Abrir Site'."
            })
                
            if certidao.empresa.cidade.upper() in ['CIDREIRA', 'SAPUCAIA DO SUL']:
                print(f"--- {certidao.empresa.cidade.upper()} DETECTADA: Executando manobra anti-modal ---")
                time.sleep(2)
                driver.refresh()
                print("Refresh realizado.")

                try:
                    print("Clicando no menu 'Emitir Certidões'...")
                    menu_emitir = wait.until(EC.element_to_be_clickable(
                        (By.CLASS_NAME, "emitir-certidoes")))
                    menu_emitir.click()
                    time.sleep(1)

                    print("Clicando na aba 'CNPJ'...")
                    aba_cnpj = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[contains(text(), 'CNPJ')]")))
                    aba_cnpj.click()
                    time.sleep(1)            
                except Exception as e:
                    print(f"Erro na navegação de {certidao.empresa.cidade.upper()}: {e}")

            elif certidao.empresa.cidade.upper() in ['GRAVATAI', 'GRAVATAÍ', 'OSORIO', 'OSÓRIO', 'NOVO HAMBURGO']:
                print(f"--- {certidao.empresa.cidade.upper()} DETECTADA ---")
                try:
                    print("Aguardando o usuário resolver o captcha...")
                    while True:
                        try:
                            campo_aguardando = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.NAME, "opcaoEmissao")))
                            print("captcha resolvido.")
                            break
                        except TimeoutException:
                            pass
                    
                    select_emissao_el = wait.until(
                        EC.element_to_be_clickable((By.NAME, "opcaoEmissao")))

                    select_emissao = Select(select_emissao_el)
                    for option in select_emissao.options:
                        if "CNPJ" in option.text.upper():
                            select_emissao.select_by_visible_text(option.text)
                            print("Opção CNPJ selecionada.")
                            break

                    time.sleep(1)

                    campo_cnpj = wait.until(
                        EC.element_to_be_clickable((By.NAME, "cpfCnpj")))
                    campo_cnpj.clear()
                    campo_cnpj.send_keys(cnpj_limpo)
                    print("CNPJ preenchido.")

                    select_finalidade_el = wait.until(EC.element_to_be_clickable(
                        (By.NAME, "FinalidadeCertidaoDebito.codigo")))
                    select_finalidade = Select(select_finalidade_el)
                    
                    cidade_upper = certidao.empresa.cidade.upper()
                    
                    if cidade_upper == 'NOVO HAMBURGO':
                        for opt in select_finalidade.options:
                            print(opt.text)
                            if 'PMNH' in opt.text.upper():
                                select_finalidade.select_by_visible_text(
                                opt.text)
                            print("Finalidade correta selecionada.")
                    else:
                        for opt in select_finalidade.options:
                            if "CONTRIBUINTE" in opt.text.upper():
                                select_finalidade.select_by_visible_text(
                                    opt.text)
                                print("Finalidade Contribuinte selecionada.")

                    time.sleep(1)

                    btn_confirmar = driver.find_element(By.NAME, "confirmar")
                    btn_confirmar.click()
                    print("Botão Confirmar clicado.")

                    info_site['cnpj_field_id'] = None

                except Exception as e:
                    print(f"Erro na navegação de {certidao.empresa.cidade.upper()}: {e}")

            elif certidao.empresa.cidade.upper() in ['XANGRI-LA', 'XANGRI-LÁ', 'XANGRILA']:
                print("--- XANGRI-LÁ DETECTADA ---")

                try:
                    print("Clicando em Contribuinte...")
                    btn_contribuinte = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//a[span[contains(text(), 'Contribuinte')]]")))
                    btn_contribuinte.click()

                    print("Selecionando Pessoa Jurídica...")
                    radio_juridica = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//input[@type='radio' and @value='J']")))
                    radio_juridica.click()

                    time.sleep(1)

                    print("Preenchendo CNPJ...")
                    input_cnpj = wait.until(EC.element_to_be_clickable(
                        (By.ID, "compInformarContribuinte:formNumero:itIdent")))
                    input_cnpj.clear()
                    input_cnpj.send_keys(cnpj_limpo)

                    print("Clicando em Validar...")
                    btn_validar = wait.until(EC.element_to_be_clickable(
                        (By.ID, "compInformarContribuinte:formNumero:btnValidar")))
                    btn_validar.click()

                    info_site['cnpj_field_id'] = None

                    print("Aguardando geração do PDF...")

                except Exception as e:
                    print(f"Erro na navegação de Xangri-Lá: {e}")

        if info_site.get('cnpj_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME,
                            'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('by'))
            if field_by:
                try:
                    campo1 = wait.until(EC.element_to_be_clickable(
                        (field_by, info_site['cnpj_field_id'])))
                    if info_site.get('slow_typing'):
                        campo1.clear()
                        apenas_numeros = ''.join(filter(str.isdigit, cnpj_limpo))
                        campo1.click()
                        for digito in apenas_numeros:
                            campo1.send_keys(digito)
                            time.sleep(0.1)
                    else:
                        campo1.click()
                        dado_a_preencher = inscricao_limpa if info_site.get(
                            'cnpj_field_id') == 'inscricao' else cnpj_limpo
                        campo1.send_keys(dado_a_preencher)
                    
                    if tipo_certidao_chave == 'FGTS':
                        try:
                            btn_consultar = wait.until(EC.element_to_be_clickable(
                                (By.ID, "mainForm:btnConsultar")))
                            print("clicando em Consultar")
                            btn_consultar.click()
                            time.sleep(1)
                            
                            btn_certificado = wait.until(EC.element_to_be_clickable(
                                (By.ID, "mainForm:j_id51")))
                            print("clicando em Certificado")
                            btn_certificado.click()
                            time.sleep(1)
                            
                            if not data_encontrada:
                                try:
                                    elemento = driver.find_element(
                                        By.XPATH, "//p[contains(., 'Validade:')]")
                                    texto = elemento.text
                                    if " a " in texto:
                                        parte_data = texto.split(" a ")[-1].strip()[:10]
                                        data_encontrada = datetime.strptime(
                                            parte_data, '%d/%m/%Y').date()
                                except Exception as e:
                                    print(f"erro ao encontrar data fgts: {e}")
                            
                            btn_visualizar = wait.until(EC.element_to_be_clickable(
                                (By.ID, "mainForm:btnVisualizar")))
                            print("clicando em Visualizar")
                            btn_visualizar.click()
                            time.sleep(1)

                            #gerar pdf automaticamente com CDP - novo
                            def _gerar_nome_pdf_aleatorio(tamanho: int = 10) -> str:
                                return ''.join(random.choices(string.ascii_letters + string.digits, k=tamanho))

                            def _caminho_pdf_downloads_unico() -> str:
                                pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                                for _ in range(50):
                                    nome = f"{_gerar_nome_pdf_aleatorio(10)}.pdf"
                                    caminho = os.path.join(pasta_downloads, nome)
                                    if not os.path.exists(caminho):
                                        return caminho
                                return os.path.join(pasta_downloads, f"{int(time.time())}_{_gerar_nome_pdf_aleatorio(6)}.pdf")

                            def _aguardar_pagina_certidao_fgts():
                                try:
                                    WebDriverWait(driver, 20).until(
                                        lambda d: (
                                            d.execute_script("return document.readyState") == "complete"
                                            and (
                                                len(d.find_elements(By.XPATH, "//button[contains(., 'Imprimir')] | //input[@value='Imprimir']")) > 0
                                                or "CERTIFICADO" in (d.page_source or "").upper()
                                            )
                                        )
                                    )
                                except Exception as _e:
                                    print(f"[FGTS] aviso: não confimou âncora da página: {_e}")

                            def _gerar_pdf_da_pagina() -> str:
                                try:
                                    try:
                                        driver.execute_cdp_cmd('Page.enable', {})
                                    except Exception:
                                        pass

                                    result = driver.execute_cdp_cmd('Page.printToPDF', {
                                        'printBackground': True,
                                        'preferCSSPageSize': True
                                    })
                                    data = (result or {}).get('data')
                                    if data:
                                        return data
                                except Exception as e_cdp:
                                    print(f"[FGTS] CDP printToPDF falhou, tentando print_page: {e_cdp}")

                                return driver.print_page()

                            try:
                                _aguardar_pagina_certidao_fgts()

                                pdf_b64 = _gerar_pdf_da_pagina()
                                if not pdf_b64:
                                    raise ValueError("PDF base64 vazio")

                                caminho_pdf = _caminho_pdf_downloads_unico()
                                with open(caminho_pdf, 'wb') as f:
                                    f.write(base64.b64decode(pdf_b64))

                                print(f"[FGTS] PDF gerado em Downloads: {caminho_pdf}")

                                sucesso, msg = file_manager.mover_e_renomear(
                                    caminho_pdf,
                                    certidao.empresa.nome,
                                    certidao.tipo.value
                                )

                                if sucesso:
                                    arquivo_salvo_msg = f"Arquivo salvo em: {msg}"
                                    pular_monitoramento = True
                                    print(arquivo_salvo_msg)

                                    try:
                                        janelas_abertas = driver.window_handles
                                        if janelas_abertas:
                                            driver.switch_to.window(janelas_abertas[-1])

                                        caminho_certidao = msg.replace("\\", "\\\\")

                                        mensagem_alerta = (
                                            "PDF salvo no servidor com sucesso!\n"
                                            f"Salvo em: {caminho_certidao}\n\n"
                                            "Após fechar este alerta, a janela do Chrome será fechada automaticamente."
                                        )

                                        # Dispara o alert de forma assíncrona e espera o usuário fechar (OK)
                                        driver.execute_script(
                                            "var msg = arguments[0]; setTimeout(function(){ alert(msg); }, 50);",
                                            mensagem_alerta
                                        )

                                        try:
                                            WebDriverWait(driver, 10).until(EC.alert_is_present())
                                        except TimeoutException:
                                            print("[FGTS] Aviso: alerta não apareceu; seguindo para fechar Chrome.")
                                        else:
                                            def _alert_fechado(_d):
                                                try:
                                                    _d.switch_to.alert
                                                    return False
                                                except NoAlertPresentException:
                                                    return True

                                            try:
                                                WebDriverWait(driver, 600).until(_alert_fechado)
                                            except TimeoutException:
                                                print("[FGTS] Aviso: timeout esperando usuário fechar o alerta.")

                                        time.sleep(1)
                                        try:
                                            driver.quit()
                                        except Exception as e_quit:
                                            print(f"[FGTS] Aviso: erro ao fechar Chrome: {e_quit}")
                                    except Exception as e_alert:
                                        print(f"[FGTS] Erro ao exibir alerta/fechar Chrome: {e_alert}")
                            except Exception as e_pdf:
                                print(f"[FGTS] Erro ao gerar PDF automaticamente: {e_pdf}")
                            
                        except Exception as e:
                            print(f"erro automação emissao FGTS: {e}")

                    if tipo_certidao_chave == 'MUNICIPAL':   
                        cidade_upper = certidao.empresa.cidade.upper()
                        if cidade_upper in ['CIDREIRA', 'SAPUCAIA DO SUL']:
                            print(f"Clicando no botão Buscar para {cidade_upper}...")
                            try:
                                btn_buscar = wait.until(EC.element_to_be_clickable(
                                    (By.ID, "btn_buscar_cadastros")))
                                btn_buscar.click()
                                print("Botão Buscar clicado com sucesso!")
                                time.sleep(2)
                            except Exception as e:
                                print(f"Erro ao clicar no botão Buscar: {e}")
                        elif cidade_upper == 'CANOAS':
                            print(f"Clicando em Imprimir para {cidade_upper}...")
                            try:
                                btn_imprimir = wait.until(EC.element_to_be_clickable(
                                    (By.NAME, "BUTTONIMPRIMIR")))
                                btn_imprimir.click()
                                print("Botão Imprimir clicado com sucesso!")
                                time.sleep(2)
                            except Exception as e:
                                print(f"Erro ao clicar no botão Imprimir: {e}")
                        elif cidade_upper == 'SORRISO':
                            print(f"Clicando em Imprimir para {cidade_upper}...")
                            try:
                                btn_imprimir = wait.until(EC.element_to_be_clickable(
                                    (By.ID, "btnImprimirCertidaoDebitos")))
                                btn_imprimir.click()
                                print("Botão Imprimir clicado com sucesso!")
                                time.sleep(2)
                            except Exception as e:
                                print(f"Erro ao clicar no botão Imprimir: {e}")
                        elif cidade_upper in ['TRAMANDAI', 'TRAMANDAÍ']:
                            print(f"Clicando em Pesquisar para {cidade_upper}...")
                            try:
                                btn_pesquisar = wait.until(EC.element_to_be_clickable(
                                        (By.NAME, "pesquisa")))
                                btn_pesquisar.click()
                                print("Botão Imprimir clicado com sucesso!")
                                time.sleep(0.6)
                                btn_emitir = wait.until(EC.element_to_be_clickable(
                                        (By.XPATH, "//a[contains(@class,'links') and contains(normalize-space(.), 'Emitir Certidão por Nome')]")))
                                btn_emitir.click()
                                time.sleep(1)
                            except Exception as e:
                                print(f"Erro ao clicar nos botões: {e}")
                        elif cidade_upper == 'CAPAO DA CANOA':
                            print(f"Clicando em Emitir para {cidade_upper}...")
                            try:
                                btn_continuar = wait.until(EC.element_to_be_clickable(
                                        (By.ID, "mainForm:btCnpj")))
                                btn_continuar.click()
                                time.sleep(0.5)
                                
                                btn_emitir = wait.until(EC.element_to_be_clickable(
                                        (By.CSS_SELECTOR, "img[title='Emite a CND para este contribuinte']")))
                                btn_emitir.click()
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"Erro ao clicar em Emitir: {e}")
                except:
                    pass

        if info_site.get('inscricao_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME,
                            'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('inscricao_field_by'))
            if field_by:
                try:
                    campo2 = wait.until(EC.element_to_be_clickable(
                        (field_by, info_site['inscricao_field_id'])))
                    campo2.click()
                    campo2.send_keys(inscricao_limpa)
                    campo2.send_keys(Keys.TAB)
                except:
                    pass

        if not pular_monitoramento:
            print("--- AGUARDANDO DOWNLOAD OU FECHAMENTO ---")

            download_detectado = False

            while True:
                try:
                    driver.window_handles
                except:
                    print("Janela fechada pelo usuário.")
                    break

                if not download_detectado:
                    novo_arquivo = file_manager.verificar_novo_arquivo(
                        tempo_inicio)
                    
                    if novo_arquivo:
                        print(f"Novo arquivo detectado: {novo_arquivo}")
                        download_detectado = True
                        sucesso, msg = file_manager.mover_e_renomear(
                            novo_arquivo,
                            certidao.empresa.nome,
                            certidao.tipo.value
                        )

                        if sucesso:
                            arquivo_salvo_msg = f"Arquivo salvo em: {msg}"
                            print(arquivo_salvo_msg)
                            try:
                                janelas_abertas = driver.window_handles
                                if janelas_abertas:
                                    driver.switch_to.window(janelas_abertas[-1])
                                
                                caminho_certidao = msg.replace("\\", "\\\\")
                                mensagem_alerta = (
                                    "PDF salvo no servidor com sucesso!\n"
                                    f"Salvo em: {caminho_certidao}\n\n"
                                    "Após fechar este alerta, a janela do Chrome será fechada automaticamente."
                                )

                                driver.execute_script(
                                    "var msg = arguments[0]; setTimeout(function(){ alert(msg); }, 50);",
                                    mensagem_alerta
                                )

                                try:
                                    WebDriverWait(driver, 10).until(EC.alert_is_present())
                                except TimeoutException:
                                    print("Aviso: alerta não apareceu; seguindo para fechar Chrome.")
                                else:
                                    def _alert_fechado(_d):
                                        try:
                                            _d.switch_to.alert
                                            return False
                                        except NoAlertPresentException:
                                            return True

                                    try:
                                        WebDriverWait(driver, 600).until(_alert_fechado)
                                    except TimeoutException:
                                        print("Aviso: timeout esperando usuário fechar o alerta.")

                                time.sleep(1)
                                try:
                                    driver.quit()
                                except Exception as e_quit:
                                    print(f"Aviso: erro ao fechar Chrome: {e_quit}")

                                break
                            except Exception as e:
                                print(f"Erro ao exibir alerta: {e}")
                        else:
                            print(f"Erro ao salvar: {msg}")

                time.sleep(1)
        else:
            print("--- FGTS: monitoramento pulado (PDF gerado via CDP) ---")

    except Exception as e:
        print(f"!!!!!!!!!! ERRO NO SELENIUM !!!!!!!!!!\n{e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"status": "error", "message": "Ocorreu um erro na automação."}), 500

    response_data = {'status': 'unknown'}

    if arquivo_salvo_msg:
        response_data['status'] = 'success_file_saved'
        response_data['mensagem_arquivo'] = arquivo_salvo_msg
        response_data['certidao_id'] = certidao_id
        response_data['tipo_certidao'] = certidao.tipo.value

        if data_encontrada:
            print(
                f"[DEBUG] Data de validade encontrada: {data_encontrada.strftime('%d/%m/%Y')}")
            response_data['nova_data'] = data_encontrada.strftime('%Y-%m-%d')
            response_data['data_formatada'] = data_encontrada.strftime(
                '%d/%m/%Y')
        else:
            data_calc = None
            if tipo_certidao_chave == 'TRABALHISTA':
                data_calc = date.today() + timedelta(days=180)
            elif tipo_certidao_chave == 'ESTADUAL':
                estado = certidao.empresa.estado.strip().upper()
                if estado == "RS":
                    data_calc = date.today() + timedelta(days=59)
                elif estado == "SP":
                    data_calc = date.today() + timedelta(days=180)
                elif estado == "MT":
                    data_calc = date.today() + timedelta(days=59)
                else:
                    data_calc = None
            elif tipo_certidao_chave == 'MUNICIPAL':
                cidade = certidao.empresa.cidade.strip().upper()
                if cidade in ['IMBÉ', 'IMBE']:
                    data_calc = date.today() + timedelta(days=90)
                elif cidade in ['TRAMANDAÍ', 'TRAMANDAI', 'TRAMANDAI/RS']:
                    data_calc = date.today() + timedelta(days=30)
                elif cidade == "CIDREIRA":
                    data_calc = date.today() + timedelta(days=30)
                elif cidade == "SAPUCAIA DO SUL":
                    data_calc = date.today() + timedelta(days=120)
                elif cidade in ['GRAVATAI', 'GRAVATAÍ']:
                    data_calc = date.today() + timedelta(days=90)
                elif cidade == "NOVO HAMBURGO":
                    data_calc = date.today() + timedelta(days=60)
                elif cidade in ['OSORIO', 'OSÓRIO']:
                    data_calc = date.today() + timedelta(days=90)
                elif cidade == 'CANOAS':
                    data_calc = date.today() + timedelta(days=90)
                elif cidade == 'SORRISO':
                    data_calc = date.today() + timedelta(days=60)
                elif cidade in ['XANGRI-LA', 'XANGRI-LÁ', 'XANGRILA']:
                    data_calc = date.today() + timedelta(days=30)
                elif cidade in ['CAPAO DA CANOA', 'CAPÃO DA CANOA']:
                    data_calc = date.today() + timedelta(days=30)
                else:
                    data_calc = None

            if data_calc:
                print(
                    f"[DEBUG] Data de validade calculada: {data_calc.strftime('%d/%m/%Y')}")
                response_data['nova_data'] = data_calc.strftime('%Y-%m-%d')
                response_data['data_formatada'] = data_calc.strftime(
                    '%d/%m/%Y')
            else:
                response_data['status'] = 'success_file_saved_no_date'

    else:
        response_data['status'] = 'window_closed_no_file'
        response_data['certidao_id'] = certidao_id
        response_data['tipo_certidao'] = certidao.tipo.value

    return jsonify(response_data)


@bp.route('/certidao/salvar_data_confirmada', methods=['POST'])
def salvar_data_confirmada():
    dados = request.get_json()
    certidao_id = dados.get('certidao_id')
    nova_validade_str = dados.get('nova_validade')

    try:
        certidao = Certidao.query.get(certidao_id)
        nova_data = datetime.strptime(nova_validade_str, '%Y-%m-%d').date()

        certidao.data_validade = nova_data
        certidao.status_especial = None

        hoje = date.today()
        diferenca = (nova_data - hoje).days

        nova_classe = 'status-verde'
        if diferenca < 0:
            nova_classe = 'status-vermelho'
        elif diferenca <= 7:
            nova_classe = 'status-amarelo'

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Data confirmada e atualizada com sucesso!',
            'nova_data_formatada': nova_data.strftime('%d/%m/%Y'),
            'nova_classe': nova_classe
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/certidao/monitorar_download_federal/<int:certidao_id>')
def monitorar_download_federal(certidao_id):
    certidao = Certidao.query.get_or_404(certidao_id)

    print(
        f"--- INICIANDO MONITORAMENTO DE DOWNLOAD (FEDERAL) - ID: {certidao_id} ---")

    file_manager.criar_chave_interrupcao()

    time.sleep(2)

    file_manager.remover_chave_interrupcao()

    tempo_limite = 180
    tempo_inicio = time.time()
    chave_interrupcao = file_manager.obter_caminho_chave_interrupcao()

    termos_proibidos = [
        'consulta regularidade',
        'crf',
        'cndt',
        'sitafe'
    ]

    while (time.time() - tempo_inicio) < tempo_limite:
        if os.path.exists(chave_interrupcao):
            print(
                f"MONITORAMENTO FEDERAL (ID {certidao_id}) INTERROMPIDO POR NOVA REQUISIÇÃO.")
            file_manager.remover_chave_interrupcao()
            return jsonify({'status': 'interrupted', 'mensagem': 'Monitoramento interrompido.'})

        novo_arquivo = file_manager.verificar_novo_arquivo(
            tempo_inicio, termos_ignorar=termos_proibidos)

        if novo_arquivo:
            print(f"Arquivo Federal detectado: {novo_arquivo}")

            sucesso, msg = file_manager.mover_e_renomear(
                novo_arquivo,
                certidao.empresa.nome,
                certidao.tipo.value
            )

            if sucesso:
                return jsonify({
                    'status': 'success',
                    'mensagem': f"Arquivo salvo no servidor: {msg}"
                })
            else:
                return jsonify({
                    'status': 'error',
                    'mensagem': f"Erro ao mover: {msg}"
                })

        time.sleep(1)

    # limpeza final por segurança
    file_manager.remover_chave_interrupcao()
    return jsonify({'status': 'timeout', 'mensagem': 'Tempo esgotado sem download.'})


@bp.route('/certidao/marcar_pendente_json/<int:certidao_id>', methods=['POST'])
def marcar_pendente_json(certidao_id):
    try:
        certidao = Certidao.query.get_or_404(certidao_id)
        certidao.status_especial = StatusEspecial.PENDENTE
        certidao.data_validade = None

        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/certidao/atualizar_json/<int:certidao_id>', methods=['POST'])
def atualizar_validade_json(certidao_id):
    data = request.get_json()
    nova_data_str = data.get('nova_validade')

    try:
        certidao = Certidao.query.get_or_404(certidao_id)

        if nova_data_str:
            nova_data = datetime.strptime(nova_data_str, '%Y-%m-%d').date()
            certidao.data_validade = nova_data
            certidao.status_especial = None

            hoje = date.today()
            diferenca = (nova_data - hoje).days

            nova_classe = 'status-verde'
            if diferenca < 0:
                nova_classe = 'status-vermelho'
            elif diferenca <= 7:
                nova_classe = 'status-amarelo'

            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': f'Validade de {certidao.empresa.nome} atualizada com sucesso!',
                'nova_data_formatada': nova_data.strftime('%d/%m/%Y'),
                'nova_classe': nova_classe
            })
        else:
            return jsonify({'status': 'error', 'message': 'Data inválida.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
