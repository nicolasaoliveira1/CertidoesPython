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
from app import file_manager
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
                                       
## baixar certidao com automacao salvamento ||||
##                                          VVVV
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
            return jsonify({'status': 'error', 'message': 'Regra municipal não encontrada'})
    
    cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
    inscricao_limpa = certidao.empresa.inscricao_mobiliaria or ''

    driver = None 
    data_encontrada = None
    arquivo_salvo_msg = None
    
    tempo_inicio = time.time()

    try:
        print(f"--- INICIANDO AUTOMAÇÃO ({tipo_certidao_chave}) ---")
        
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
        driver.get(info_site.get('url'))
        wait = WebDriverWait(driver, 20)
        
        if info_site.get('pre_fill_click_id'):
            click_by_map = {'id': By.ID, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            click_by = click_by_map.get(info_site['pre_fill_click_by'])
            if click_by:
                try:
                    elemento_inicial = wait.until(EC.element_to_be_clickable((click_by, info_site['pre_fill_click_id'])))
                    elemento_inicial.click()
                    time.sleep(2)
                except: pass

        if info_site.get('cnpj_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('by'))
            if field_by:
                try:
                    campo1 = wait.until(EC.element_to_be_clickable((field_by, info_site['cnpj_field_id'])))
                    campo1.click()
                    dado_a_preencher = inscricao_limpa if info_site.get('cnpj_field_id') == 'inscricao' else cnpj_limpo
                    campo1.send_keys(dado_a_preencher)
                except: pass

        if info_site.get('inscricao_field_id'):
            field_by_map = {'id': By.ID, 'name': By.NAME, 'css_selector': By.CSS_SELECTOR, 'xpath': By.XPATH}
            field_by = field_by_map.get(info_site.get('inscricao_field_by'))
            if field_by:
                try:
                    campo2 = wait.until(EC.element_to_be_clickable((field_by, info_site['inscricao_field_id'])))
                    campo2.click()
                    campo2.send_keys(inscricao_limpa)
                except: pass


        print("--- AGUARDANDO DOWNLOAD OU FECHAMENTO ---")
        
        download_detectado = False
        
        while True:
            try:
                driver.window_handles
            except:
                print("Janela fechada pelo usuário.")
                break 
            
            if tipo_certidao_chave == 'FGTS' and not data_encontrada:
                try:
                    elemento = driver.find_element(By.XPATH, "//p[contains(., 'Validade:')]")
                    texto = elemento.text
                    if " a " in texto:
                        parte_data = texto.split(" a ")[-1].strip()[:10]
                        data_encontrada = datetime.strptime(parte_data, '%d/%m/%Y').date()
                        driver.execute_script("alert('Data lida! Agora faça o download do PDF.');")
                except:
                    pass 
            
            if not download_detectado:
                novo_arquivo = file_manager.verificar_novo_arquivo(tempo_inicio)
                
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
                            driver.execute_script(f"alert('PDF salvo no servidor com sucesso!');")
                        except: pass
                    else:
                        print(f"Erro ao salvar: {msg}")

            time.sleep(1)

    except Exception as e:
        print(f"!!!!!!!!!! ERRO NO SELENIUM !!!!!!!!!!\n{e}")
        if driver:
            try: driver.quit()
            except: pass
        return jsonify({"status": "error", "message": "Ocorreu um erro na automação."}), 500

    if not data_encontrada:
        if tipo_certidao_chave == 'TRABALHISTA':
            data_encontrada = date.today() + timedelta(days=180)
        elif tipo_certidao_chave == 'ESTADUAL':
            data_encontrada = date.today() + timedelta(days=59)
        elif tipo_certidao_chave == 'MUNICIPAL':
            cidade = certidao.empresa.cidade.strip().upper()
            if cidade in ['IMBÉ', 'IMBE']:
                data_encontrada = date.today() + timedelta(days=90)
            elif cidade in ['TRAMANDAÍ', 'TRAMANDAI', 'TRAMANDAI/RS']:
                data_encontrada = date.today() + timedelta(days=30)

    response_data = {'status': 'success'}
    
    if data_encontrada:
        response_data['certidao_id'] = certidao_id
        response_data['nova_data'] = data_encontrada.strftime('%Y-%m-%d')
        response_data['data_formatada'] = data_encontrada.strftime('%d/%m/%Y')
        response_data['tipo_certidao'] = certidao.tipo.value
    else:
        response_data['status'] = 'success_no_date'
        
    if arquivo_salvo_msg:
        response_data['mensagem_arquivo'] = arquivo_salvo_msg
        
    return jsonify(response_data)