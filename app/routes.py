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
from app.models import Empresa, Certidao, TipoCertidao, StatusEspecial, Municipio
from datetime import date, datetime, timedelta
from sqlalchemy import or_
import time

bp = Blueprint('main', __name__)

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
            conditions.append(Certidao.data_validade > (hoje + timedelta(days=7)))
        
        if 'a_vencer' in status_filtros:
            conditions.append(Certidao.data_validade.between(hoje, hoje + timedelta(days=7)))
        
        if 'vencidas' in status_filtros:
            conditions.append(
                (Certidao.data_validade < hoje) & (Certidao.status_especial == None)
            )
        
        if 'pendentes' in status_filtros:
            conditions.append(Certidao.status_especial == StatusEspecial.PENDENTE)
        
        if conditions:
            query = query.filter(or_(*conditions))
        else:
            query = query.filter(Empresa.id == -1) 

    empresas = query.order_by(Empresa.id).all()
    
    urls_municipais_db = {m.nome: m.url_certidao for m in Municipio.query.all()}
    
    return render_template(
        'dashboard.html', 
        empresas=empresas, 
        status_filtros=status_filtros, 
        hoje=hoje, 
        sites_urls=SITES_CERTIDOES,
        urls_municipais=urls_municipais_db
    )

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

@bp.route('/certidao/baixar/<int:certidao_id>')
def baixar_certidao(certidao_id):
    certidao = Certidao.query.get_or_404(certidao_id)
    tipo_certidao_chave = certidao.tipo.name

    if tipo_certidao_chave == 'FEDERAL':
        return redirect("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")
    
    info_site = {} 

    if tipo_certidao_chave != 'MUNICIPAL':
        info_site = SITES_CERTIDOES.get(tipo_certidao_chave, {})
    else:
        cidade_empresa = certidao.empresa.cidade
        regra_municipio = Municipio.query.filter_by(nome=cidade_empresa).first()
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
        else:
            # Retornamos um JSON de erro para o JS tratar
            return jsonify({'status': 'error', 'message': 'Regra municipal não encontrada'})
    
    cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
    inscricao_limpa = certidao.empresa.inscricao_mobiliaria or ''

    driver = None 
    data_encontrada = None

    try:
        print(f"--- INICIANDO AUTOMAÇÃO ({tipo_certidao_chave}) ---")
        
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
        print(f"1. Acessando a URL: {info_site.get('url')}")
        driver.get(info_site.get('url'))

        wait = WebDriverWait(driver, 20)
        
        # --- Preenchimento Padrão ---
        if info_site.get('pre_fill_click_id'):
            click_by_map = {'id': By.ID, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            click_by = click_by_map.get(info_site['pre_fill_click_by'])
            if click_by:
                elemento_inicial = wait.until(EC.element_to_be_clickable((click_by, info_site['pre_fill_click_id'])))
                elemento_inicial.click()
                time.sleep(2)

        if info_site.get('cnpj_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('by'))
            if field_by:
                campo1 = wait.until(EC.element_to_be_clickable((field_by, info_site['cnpj_field_id'])))
                campo1.click()
                dado_a_preencher = inscricao_limpa if info_site.get('cnpj_field_id') == 'inscricao' else cnpj_limpo
                campo1.send_keys(dado_a_preencher)

        if info_site.get('inscricao_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('inscricao_field_by'))
            if field_by:
                campo2 = wait.until(EC.element_to_be_clickable((field_by, info_site['inscricao_field_id'])))
                campo2.click()
                campo2.send_keys(inscricao_limpa)


        # ==================================================================
        # LÓGICA DE DATAS (FGTS, TRABALHISTA, ESTADUAL, MUNICIPAL)
        #
        #
        if tipo_certidao_chave == 'FGTS':
            print("--- FGTS: Monitorando tela para captura de data... ---")
            wait_long = WebDriverWait(driver, 120)
            try:
                elemento_validade = wait_long.until(
                    EC.presence_of_element_located((By.XPATH, "//p[contains(., 'Validade:')]"))
                )
                texto_completo = elemento_validade.text 
                
                if " a " in texto_completo:
                    # Pega tudo depois do " a " e corta
                    resto_do_texto = texto_completo.split(" a ")[-1].strip()
                    parte_data = resto_do_texto[:10]
                    
                    data_encontrada = datetime.strptime(parte_data, '%d/%m/%Y').date()
                    print(f"DATA FGTS ENCONTRADA: {data_encontrada}")
                    
                    driver.execute_script("alert('Data capturada! Pode fechar a janela.');")
            except TimeoutException:
                print("FGTS: Tempo esgotado sem encontrar a data.")

        elif tipo_certidao_chave == 'TRABALHISTA':
            print("--- TRABALHISTA: Calculando validade (Hoje + 180 dias)... ---")
            data_encontrada = date.today() + timedelta(days=180)

        elif tipo_certidao_chave == 'ESTADUAL':
            print("--- ESTADUAL (RS): Calculando validade (Hoje + 59 dias)... ---")
            data_encontrada = date.today() + timedelta(days=59)

        elif tipo_certidao_chave == 'MUNICIPAL':
            cidade = certidao.empresa.cidade.strip().upper() # Padroniza para Maiúsculas
            print(f"--- MUNICIPAL ({cidade}): Verificando regra de validade... ---")
            
            if cidade in ['IMBÉ', 'IMBE']:
                print("Regra Imbé: Hoje + 90 dias")
                data_encontrada = date.today() + timedelta(days=90)
            
            elif cidade in ['TRAMANDAÍ', 'TRAMANDAI', 'TRAMANDAI/RS']:
                print("Regra Tramandaí: Hoje + 30 dias")
                data_encontrada = date.today() + timedelta(days=30)
            
            else:
                print(f"AVISO: Nenhuma regra de validade definida para o município: {cidade}")

        # ==================================================================

        print("--- AGUARDANDO USUÁRIO FECHAR A JANELA ---")
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
        return jsonify({"status": "error", "message": "Ocorreu um erro na automação."}), 500

    # --- RETORNO FRONTEND ---
    if data_encontrada:
        return jsonify({
            'status': 'success',
            'certidao_id': certidao_id,
            'nova_data': data_encontrada.strftime('%Y-%m-%d'), # Formato para o banco
            'data_formatada': data_encontrada.strftime('%d/%m/%Y'), # Formato para exibir no modal
            'tipo_certidao': certidao.tipo.value # Exibir tipo validade no modal
        })
    else:
        return jsonify({'status': 'success_no_date'})

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
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
