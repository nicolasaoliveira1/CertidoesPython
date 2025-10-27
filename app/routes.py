from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from app.automation import SITES_CERTIDOES
from flask import render_template, Blueprint, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Empresa, Certidao, TipoCertidao, StatusEspecial
from datetime import date, datetime, timedelta
import time
#esqueleto do routes para rodar a criação do banco, rotas serão definidas aqui posteriormente

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    status_filtro = request.args.get('status', 'todas', type=str)
    query = db.session.query(Empresa).distinct()

    if status_filtro != 'todas':
        query = query.join(Certidao)

    hoje = date.today()
    
    if status_filtro == 'validas':
        query = query.filter(Certidao.data_validade > (hoje + timedelta(days=15)))
    elif status_filtro == 'a_vencer':
        query = query.filter(Certidao.data_validade.between(hoje, hoje + timedelta(days=15)))
    elif status_filtro == 'vencidas':
        query = query.filter(
            (Certidao.data_validade < hoje) & (Certidao.status_especial == None)
        )
    elif status_filtro == 'pendentes':
        query = query.filter(Certidao.status_especial == StatusEspecial.PENDENTE)
        
    empresas = query.order_by(Empresa.id).all()
    
    return render_template('dashboard.html', empresas=empresas, status_filtro=status_filtro)

@bp.route('/empresa/adicionar', methods=['POST'])
def adicionar_empresa():
    # dados formulário
    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
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
        cidade=cidade,
        inscricao_mobiliaria=inscricao if inscricao else None # Garante que seja nulo se vazio
    )
    db.session.add(nova_empresa)

    for tipo in TipoCertidao:
        nova_certidao = Certidao(tipo=tipo, empresa=nova_empresa, data_validade=None)
        db.session.add(nova_certidao)

    # Salva no banco
    try:
        db.session.commit()
        flash(f'Empresa "{nome}" cadastrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar empresa: {e}', 'danger')

    # Redirecionamento para dashboard
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
            flash(f"Validade da certidão {certidao.tipo.value} da empresa {certidao.empresa.nome} atualizada com sucesso!", 'success')
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
        flash(f'Certidão {certidao.tipo.value} da empresa {certidao.empresa.nome} marcada como Pendente.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao marcar como pendente: {e}', 'danger')
        
    return redirect(url_for('main.dashboard'))

# @bp.route('/certidao/abrir_site/<int:certidao_id>')
# def abrir_site_certidao(certidao_id):
#     certidao = Certidao.query.get_or_404(certidao_id)
#     tipo_certidao_chave = certidao.tipo.name
#     info_site = SITES_CERTIDOES.get(tipo_certidao_chave, {})

#     if not info_site or info_site.get('url') == '#':
#         flash(f'Automação para a certidão {certidao.tipo.value} ainda não implementada.', 'warning')
#         return redirect(url_for('main.dashboard'))

#     cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
#     driver = None 
#     try:
#         print("--- INICIANDO AUTOMAÇÃO ---")
#         chrome_options = Options()
#         chrome_options.add_argument("--incognito")
#         chrome_options.add_argument("--start-maximized")
        
#         driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
#         print(f"1. Acessando a URL: {info_site['url']}")
#         driver.get(info_site['url'])

#         # Uma espera generosa de 20 segundos para dar tempo à página de "desenhar" seus elementos.
#         wait = WebDriverWait(driver, 20)

#         # A lógica sequencial que já funciona para os outros sites, agora funcionará para a Federal.

#         if info_site.get('pre_fill_click_id'):
#             print("Procurando pelo botão de clique prévio...")
#             click_by_map = {'id': By.ID, 'css_selector': By.CSS_SELECTOR}
#             click_by = click_by_map.get(info_site['pre_fill_click_by'])
#             if click_by:
#                 botao_inicial = wait.until(EC.element_to_be_clickable((click_by, info_site['pre_fill_click_id'])))
#                 botao_inicial.click()
#                 print("SUCESSO! Botão clicado.")
#                 time.sleep(2)

#         if info_site.get('cnpj_field_id') and info_site.get('by'):
#             print("Procurando pelo campo do CNPJ...")
#             field_by_map = {'id': By.ID, 'name': By.NAME}
#             field_by = field_by_map.get(info_site.get('by'))
#             if field_by:
#                 # O WebDriverWait vai pacientemente esperar o <input name="niContribuinte"> aparecer.
#                 campo_cnpj = wait.until(EC.visibility_of_element_located((field_by, info_site['cnpj_field_id'])))
#                 campo_cnpj.send_keys(cnpj_limpo)
#                 print("SUCESSO! CNPJ preenchido.")
        
#         print("--- AUTOMAÇÃO CONCLUÍDA, AGUARDANDO USUÁRIO ---")
#         while True:
#             try:
#                 driver.window_handles
#                 time.sleep(1)
#             except:
#                 break
                
#     except Exception as e:
#         print(f"!!!!!!!!!! ERRO NO SELENIUM !!!!!!!!!!\n{e}")
#         if driver:
#             driver.quit()
#         return jsonify({"status": "error", "message": "Ocorreu um erro na automação. Verifique o terminal."}), 500

#     return ('', 204)

@bp.route('/certidao/abrir_site/<int:certidao_id>')
def abrir_site_certidao(certidao_id):
    certidao = Certidao.query.get_or_404(certidao_id)
    tipo_certidao_chave = certidao.tipo.name
    info_site = SITES_CERTIDOES.get(tipo_certidao_chave, {})

    if not info_site or info_site.get('url') == '#':
        flash(f'Automação para a certidão {certidao.tipo.value} ainda não implementada.', 'warning')
        return redirect(url_for('main.dashboard'))

    cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
    driver = None 
    try:
        print("--- INICIANDO AUTOMAÇÃO ---")
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
        print(f"1. Acessando a URL: {info_site['url']}")
        driver.get(info_site['url'])

        wait = WebDriverWait(driver, 20)

        if info_site.get('pre_fill_click_id'):
            print("Procurando pelo botão de clique prévio...")
            click_by_map = {'id': By.ID, 'css_selector': By.CSS_SELECTOR}
            click_by = click_by_map.get(info_site['pre_fill_click_by'])
            if click_by:
                botao_inicial = wait.until(EC.element_to_be_clickable((click_by, info_site['pre_fill_click_id'])))
                botao_inicial.click()
                print("SUCESSO! Botão clicado.")
                time.sleep(2)

        if info_site.get('cnpj_field_id') and info_site.get('by'):
            print("Procurando pelo campo do CNPJ...")
            # --- ADICIONANDO 'css_selector' AO MAPA ---
            field_by_map = {'id': By.ID, 'name': By.NAME, 'css_selector': By.CSS_SELECTOR}
            field_by = field_by_map.get(info_site.get('by'))
            if field_by:
                print("Aguardando o campo ficar totalmente interativo...")
                campo_cnpj = wait.until(EC.element_to_be_clickable((field_by, info_site['cnpj_field_id'])))
                
                # A ação humana que funciona
                campo_cnpj.click()
                campo_cnpj.send_keys(cnpj_limpo)

                print("SUCESSO! CNPJ preenchido.")
        
        print("--- AUTOMAÇÃO CONCLUÍDA, AGUARDANDO USUÁRIO ---")
        while True:
            try:
                driver.window_handles
                time.sleep(1)
            except:
                break
                
    except Exception as e:
        print(f"!!!!!!!!!! ERRO NO SELENIUM !!!!!!!!!!\n{e}")
        if driver:
            driver.quit()
        return jsonify({"status": "error", "message": "Ocorreu um erro na automação. Verifique o terminal."}), 500

    return ('', 204)