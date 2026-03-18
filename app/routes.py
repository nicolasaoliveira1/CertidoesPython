import os
import json
import time
import string
import random
import base64
import re
from threading import Thread, Lock
from datetime import date, datetime, timedelta

try:
    import winreg
except ImportError:
    winreg = None

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for, send_file, current_app)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from selenium import webdriver
from selenium.common.exceptions import (InvalidSessionIdException,
                                        NoAlertPresentException,
                                        NoSuchWindowException,
                                        TimeoutException,
                                        WebDriverException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.keys import Keys
from sqlalchemy import or_
from webdriver_manager.chrome import ChromeDriverManager
import pdfplumber

from app import db, file_manager
from app.automation import SITES_CERTIDOES, VALIDADES_CERTIDOES
from app.models import (Certidao, Empresa, Municipio, StatusEspecial,
                        SubtipoCertidao, TipoCertidao)

bp = Blueprint('main', __name__)

FGTS_BATCH_LOCK = Lock()
RS_CERT_POLICY_LOCK = Lock()
RS_CERT_POLICY_ACTIVE_COUNT = 0

FGTS_BATCH_STATE = {
    'status': 'idle',
    'ids': [],
    'index': 0,
    'total': 0,
    'vencidas': 0,
    'a_vencer': 0,
    'falhas': 0,
    'current_id': None,
    'message': None,
    'stop_requested': False,
    'stop_action': None,
    'driver': None,
    'last_completed': None,
    'started_at': None,
    'finished_at': None,
    'success': 0,
}


def _reset_fgts_batch_state():
    FGTS_BATCH_STATE.update({
        'status': 'idle',
        'ids': [],
        'index': 0,
        'total': 0,
        'vencidas': 0,
        'a_vencer': 0,
        'falhas': 0,
        'current_id': None,
        'message': None,
        'stop_requested': False,
        'stop_action': None,
        'driver': None,
        'last_completed': None,
        'started_at': None,
        'finished_at': None,
        'success': 0,
    })


def _fgts_stop_requested():
    return FGTS_BATCH_STATE.get('stop_requested')


def _fgts_stop_action():
    return FGTS_BATCH_STATE.get('stop_action')


def _fgts_status_por_data(nova_data):
    if not nova_data:
        return 'status-cinza'

    hoje = date.today()
    diferenca = (nova_data - hoje).days
    if diferenca < 0:
        return 'status-vermelho'
    if diferenca <= 7:
        return 'status-amarelo'
    return 'status-verde'


def _fgts_quit_driver_async(driver):
    if not driver:
        return

    def _close():
        try:
            driver.quit()
        except Exception:
            pass

    Thread(target=_close, daemon=True).start()


def _get_chrome_profile_settings():
    profile_dir = None
    profile_name = None

    try:
        profile_dir = current_app.config.get('CHROME_PROFILE_DIR')
        profile_name = current_app.config.get('CHROME_PROFILE_NAME')
    except RuntimeError:
        profile_dir = os.environ.get('CHROME_PROFILE_DIR')
        profile_name = os.environ.get('CHROME_PROFILE_NAME')

    if not profile_dir:
        profile_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'chrome-profile')
        )
    if not profile_name:
        profile_name = 'Certidoes'

    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir, profile_name


def _get_config_value(name, default=None):
    try:
        return current_app.config.get(name, default)
    except RuntimeError:
        return os.environ.get(name, default)


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on', 'sim'}


def _montar_politica_autoselect_rs():
    if not _to_bool(_get_config_value('RS_CERT_AUTOSELECT_ENABLED', True), True):
        return None

    pattern = (_get_config_value('RS_CERT_AUTOSELECT_PATTERN', 'https://www.sefaz.rs.gov.br') or '').strip()
    issuer_cn = (_get_config_value('RS_CERT_AUTOSELECT_ISSUER_CN', '') or '').strip()
    subject_cn = (_get_config_value('RS_CERT_AUTOSELECT_SUBJECT_CN', '') or '').strip()

    if not pattern:
        return None

    filtro = {}
    if issuer_cn:
        filtro['ISSUER'] = {'CN': issuer_cn}
    if subject_cn:
        filtro['SUBJECT'] = {'CN': subject_cn}

    if not filtro:
        return None

    return {
        'pattern': pattern,
        'filter': filtro,
    }


def _sincronizar_politica_autoselect_rs(aplicar=True):
    if os.name != 'nt' or winreg is None:
        return

    indice = str(_get_config_value('RS_CERT_AUTOSELECT_POLICY_INDEX', '1') or '1').strip() or '1'
    politica = _montar_politica_autoselect_rs() if aplicar else None
    chave_registro = r"Software\Policies\Google\Chrome\AutoSelectCertificateForUrls"

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, chave_registro) as chave:
            if politica is None:
                try:
                    winreg.DeleteValue(chave, indice)
                    print(f"[RS] Política AutoSelectCertificate removida (índice {indice}).")
                except FileNotFoundError:
                    pass
                return

            valor = json.dumps(politica, ensure_ascii=False, separators=(',', ':'))
            winreg.SetValueEx(chave, indice, 0, winreg.REG_SZ, valor)
            print(f"[RS] Política AutoSelectCertificate aplicada (índice {indice}).")
    except OSError as exc:
        print(f"[RS] Não foi possível sincronizar a política AutoSelectCertificate: {exc}")


def _ativar_politica_autoselect_rs_temporaria():
    global RS_CERT_POLICY_ACTIVE_COUNT

    if not _montar_politica_autoselect_rs():
        return False

    with RS_CERT_POLICY_LOCK:
        RS_CERT_POLICY_ACTIVE_COUNT += 1
        if RS_CERT_POLICY_ACTIVE_COUNT == 1:
            _sincronizar_politica_autoselect_rs(aplicar=True)
    return True


def _desativar_politica_autoselect_rs_temporaria():
    global RS_CERT_POLICY_ACTIVE_COUNT

    with RS_CERT_POLICY_LOCK:
        if RS_CERT_POLICY_ACTIVE_COUNT <= 0:
            RS_CERT_POLICY_ACTIVE_COUNT = 0
            _sincronizar_politica_autoselect_rs(aplicar=False)
            return

        RS_CERT_POLICY_ACTIVE_COUNT -= 1
        if RS_CERT_POLICY_ACTIVE_COUNT == 0:
            _sincronizar_politica_autoselect_rs(aplicar=False)


def _build_chrome_options(anonimo=True, usar_perfil=False):
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    if anonimo:
        chrome_options.add_argument("--incognito")

    if usar_perfil:
        profile_dir, profile_name = _get_chrome_profile_settings()
        if profile_dir:
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        if profile_name:
            chrome_options.add_argument(f"--profile-directory={profile_name}")

    return chrome_options


def _criar_driver_chrome(anonimo=True, usar_perfil=False):
    chrome_options = _build_chrome_options(anonimo=anonimo, usar_perfil=usar_perfil)
    return webdriver.Chrome(service=ChromeService(
        ChromeDriverManager().install()), options=chrome_options)


def _preparar_pagina_fgts(driver, url, cnpj_field_id):
    if not driver or not url or not cnpj_field_id:
        return False

    try:
        driver.set_page_load_timeout(30)
    except Exception:
        pass

    try:
        driver.delete_all_cookies()
    except Exception:
        pass

    try:
        driver.get("about:blank")
    except Exception:
        pass

    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass

    deadline = time.time() + 20
    while time.time() < deadline:
        if _fgts_stop_requested():
            return False
        try:
            WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.ID, cnpj_field_id))
            )
            return True
        except TimeoutException:
            continue

    return True


def _calc_fgts_targets(start_certidao_id):
    hoje = date.today()
    limite = hoje + timedelta(days=7)

    certidoes = (Certidao.query
                 .filter(Certidao.tipo == TipoCertidao.FGTS)
                 .filter(Certidao.data_validade != None)
                 .filter(Certidao.data_validade <= limite)
                 .order_by(Certidao.id)
                 .all())

    ids = [c.id for c in certidoes if c.data_validade]
    vencidas = sum(1 for c in certidoes if c.data_validade and c.data_validade < hoje)
    a_vencer = sum(1 for c in certidoes if c.data_validade and hoje <= c.data_validade <= limite)

    if start_certidao_id in ids:
        ids.remove(start_certidao_id)
        ids.insert(0, start_certidao_id)

    return {
        'ids': ids,
        'total': len(ids),
        'vencidas': vencidas,
        'a_vencer': a_vencer,
    }


def _emitir_fgts_certidao(certidao_id, driver=None):
    if _fgts_stop_requested():
        return False, False, 'Lote interrompido.'

    certidao = Certidao.query.get(certidao_id)
    if not certidao:
        return False, False, 'Certidão não encontrada.'

    info_site = SITES_CERTIDOES.get('FGTS', {})
    if not info_site.get('url'):
        return False, True, 'Configuração FGTS ausente.'

    local_driver = driver
    criado_localmente = False
    try:
        if _fgts_stop_requested():
            return False, False, 'Lote interrompido.'

        if local_driver is None:
            local_driver = _criar_driver_chrome()
            criado_localmente = True

        FGTS_BATCH_STATE['driver'] = local_driver

        pagina_ok = _preparar_pagina_fgts(
            local_driver,
            info_site.get('url'),
            info_site.get('cnpj_field_id')
        )

        if not pagina_ok:
            return False, True, 'Erro ao carregar página FGTS.'

        wait = WebDriverWait(local_driver, 20)

        field_by = By.ID
        campo_cnpj = wait.until(EC.element_to_be_clickable(
            (field_by, info_site.get('cnpj_field_id'))))
        if _fgts_stop_requested():
            return False, False, 'Lote interrompido.'
        campo_cnpj.click()
        cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj or ''))
        campo_cnpj.send_keys(cnpj_limpo)

        contexto = {
            'arquivo_salvo_msg': None,
            'pular_monitoramento': False,
            'data_encontrada': None
        }

        _automatizar_fgts(contexto, local_driver, wait, certidao)

        if _fgts_stop_requested():
            return False, False, 'Lote interrompido.'

        if contexto.get('arquivo_salvo_msg'):
            nova_data = calcular_validade_padrao(certidao, contexto.get('data_encontrada'))
            if nova_data:
                try:
                    certidao.data_validade = nova_data
                    certidao.status_especial = None
                    db.session.commit()
                except Exception as e_db:
                    db.session.rollback()
                    print(f"[FGTS] Aviso: não foi possível salvar validade no banco: {e_db}")

            with FGTS_BATCH_LOCK:
                FGTS_BATCH_STATE['last_completed'] = {
                    'certidao_id': certidao.id,
                    'data_formatada': nova_data.strftime('%d/%m/%Y') if nova_data else None,
                    'nova_classe': _fgts_status_por_data(nova_data)
                }
            return True, False, None
        return False, False, 'Falha ao gerar PDF FGTS.'
    except Exception as exc:
        return False, True, f'Erro grave no FGTS: {exc}'
    finally:
        if criado_localmente:
            FGTS_BATCH_STATE['driver'] = None
        if criado_localmente and local_driver:
            try:
                local_driver.quit()
            except Exception:
                pass


def _fgts_batch_worker(app):
    with app.app_context():
        driver = None
        print("[FGTS-LOTE] Worker iniciado.")
        while True:
            with FGTS_BATCH_LOCK:
                if FGTS_BATCH_STATE['stop_requested']:
                    if FGTS_BATCH_STATE.get('stop_action') == 'stop':
                        FGTS_BATCH_STATE['status'] = 'stopped'
                        print("[FGTS-LOTE] Interrompido por parada solicitada.")
                    else:
                        FGTS_BATCH_STATE['status'] = 'paused'
                        print("[FGTS-LOTE] Pausado por solicitação.")
                    break

                if FGTS_BATCH_STATE['index'] >= FGTS_BATCH_STATE['total']:
                    FGTS_BATCH_STATE['status'] = 'completed'
                    FGTS_BATCH_STATE['current_id'] = None
                    FGTS_BATCH_STATE['finished_at'] = datetime.utcnow()
                    print("[FGTS-LOTE] Finalizado com sucesso.")
                    break

                certidao_id = FGTS_BATCH_STATE['ids'][FGTS_BATCH_STATE['index']]
                FGTS_BATCH_STATE['current_id'] = certidao_id
                print(f"[FGTS-LOTE] Iniciando emissão ID={certidao_id} ({FGTS_BATCH_STATE['index'] + 1}/{FGTS_BATCH_STATE['total']}).")

            if driver is None:
                driver = _criar_driver_chrome()

            sucesso, grave, mensagem = _emitir_fgts_certidao(certidao_id, driver=driver)

            if grave and mensagem == 'Erro ao carregar página FGTS.':
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = _criar_driver_chrome()
                print("[FGTS-LOTE] Recriando driver após falha de carregamento.")
                sucesso, grave, mensagem = _emitir_fgts_certidao(certidao_id, driver=driver)

            with FGTS_BATCH_LOCK:
                if FGTS_BATCH_STATE['stop_requested']:
                    if FGTS_BATCH_STATE.get('stop_action') == 'stop':
                        FGTS_BATCH_STATE['status'] = 'stopped'
                        print("[FGTS-LOTE] Interrompido durante execução.")
                    else:
                        FGTS_BATCH_STATE['status'] = 'paused'
                        print("[FGTS-LOTE] Pausado durante execução.")
                    break

                if grave:
                    FGTS_BATCH_STATE['status'] = 'error'
                    FGTS_BATCH_STATE['message'] = mensagem or 'Erro grave.'
                    print(f"[FGTS-LOTE] Erro grave: {FGTS_BATCH_STATE['message']}")
                    break

                if not sucesso:
                    FGTS_BATCH_STATE['falhas'] += 1
                    print(f"[FGTS-LOTE] Falha na emissão ID={certidao_id}.")
                else:
                    FGTS_BATCH_STATE['success'] += 1
                    print(f"[FGTS-LOTE] Emissão OK ID={certidao_id}.")

                FGTS_BATCH_STATE['index'] += 1

        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print("[FGTS-LOTE] Worker encerrado.")


@bp.route('/fgts/lote/info/<int:certidao_id>')
def fgts_lote_info(certidao_id):
    dados = _calc_fgts_targets(certidao_id)
    return jsonify({
        'status': 'ok',
        **dados
    })


@bp.route('/fgts/lote/iniciar', methods=['POST'])
def fgts_lote_iniciar():
    dados = request.get_json() or {}
    certidao_id = dados.get('certidao_id')

    if not certidao_id:
        return jsonify({'status': 'error', 'message': 'Certidão inválida.'}), 400

    with FGTS_BATCH_LOCK:
        if FGTS_BATCH_STATE['status'] in ['running', 'paused']:
            return jsonify({'status': 'error', 'message': 'Já existe um lote em andamento.'}), 400

        dados_lote = _calc_fgts_targets(certidao_id)
        if not dados_lote['ids']:
            return jsonify({'status': 'error', 'message': 'Nenhuma certidão FGTS vencida ou a vencer.'}), 400

        _reset_fgts_batch_state()
        FGTS_BATCH_STATE.update({
            'status': 'running',
            'ids': dados_lote['ids'],
            'total': dados_lote['total'],
            'vencidas': dados_lote['vencidas'],
            'a_vencer': dados_lote['a_vencer'],
            'started_at': datetime.utcnow(),
            'finished_at': None,
            'success': 0,
        })

        app = current_app._get_current_object()
        thread = Thread(target=_fgts_batch_worker, args=(app,), daemon=True)
        thread.start()
        print(f"[FGTS-LOTE] Lote iniciado. Total={dados_lote['total']}.")

    return jsonify({'status': 'ok'})


@bp.route('/fgts/lote/pausar', methods=['POST'])
def fgts_lote_pausar():
    with FGTS_BATCH_LOCK:
        FGTS_BATCH_STATE['stop_requested'] = True
        FGTS_BATCH_STATE['stop_action'] = 'pause'
        if FGTS_BATCH_STATE['status'] == 'running':
            FGTS_BATCH_STATE['status'] = 'paused'
        print("[FGTS-LOTE] Pausa solicitada.")
        driver = FGTS_BATCH_STATE.get('driver')

    _fgts_quit_driver_async(driver)

    return jsonify({'status': 'ok', 'message': 'Lote pausado.'})


@bp.route('/fgts/lote/parar', methods=['POST'])
def fgts_lote_parar():
    with FGTS_BATCH_LOCK:
        FGTS_BATCH_STATE['stop_requested'] = True
        FGTS_BATCH_STATE['stop_action'] = 'stop'
        FGTS_BATCH_STATE['status'] = 'stopped'
        FGTS_BATCH_STATE['finished_at'] = datetime.utcnow()
        print("[FGTS-LOTE] Parada solicitada.")
        driver = FGTS_BATCH_STATE.get('driver')

    _fgts_quit_driver_async(driver)

    return jsonify({'status': 'ok', 'message': 'Lote interrompido.'})


@bp.route('/fgts/lote/retomar', methods=['POST'])
def fgts_lote_retomar():
    with FGTS_BATCH_LOCK:
        if FGTS_BATCH_STATE['status'] != 'paused':
            return jsonify({'status': 'error', 'message': 'Lote não está pausado.'}), 400

        FGTS_BATCH_STATE['stop_requested'] = False
        FGTS_BATCH_STATE['status'] = 'running'
        print("[FGTS-LOTE] Retomada solicitada.")

        app = current_app._get_current_object()
        thread = Thread(target=_fgts_batch_worker, args=(app,), daemon=True)
        thread.start()

    return jsonify({'status': 'ok'})


@bp.route('/fgts/lote/status')
def fgts_lote_status():
    with FGTS_BATCH_LOCK:
        return jsonify({
            'status': FGTS_BATCH_STATE['status'],
            'total': FGTS_BATCH_STATE['total'],
            'index': FGTS_BATCH_STATE['index'],
            'falhas': FGTS_BATCH_STATE['falhas'],
            'current_id': FGTS_BATCH_STATE['current_id'],
            'vencidas': FGTS_BATCH_STATE['vencidas'],
            'a_vencer': FGTS_BATCH_STATE['a_vencer'],
            'message': FGTS_BATCH_STATE['message'],
            'last_completed': FGTS_BATCH_STATE.get('last_completed'),
            'success': FGTS_BATCH_STATE.get('success', 0),
            'started_at': FGTS_BATCH_STATE['started_at'].isoformat() if FGTS_BATCH_STATE.get('started_at') else None,
            'finished_at': FGTS_BATCH_STATE['finished_at'].isoformat() if FGTS_BATCH_STATE.get('finished_at') else None,
        })


@bp.route('/fgts/emitir_unico', methods=['POST'])
def fgts_emitir_unico():
    dados = request.get_json() or {}
    certidao_id = dados.get('certidao_id')

    if not certidao_id:
        return jsonify({'status': 'error', 'message': 'Certidão inválida.'}), 400

    with FGTS_BATCH_LOCK:
        if FGTS_BATCH_STATE['status'] == 'running':
            return jsonify({'status': 'error', 'message': 'Lote em andamento. Pare o lote para emitir individual.'}), 400

    sucesso, grave, mensagem = _emitir_fgts_certidao(certidao_id)

    if grave:
        return jsonify({'status': 'error', 'message': mensagem or 'Erro grave no FGTS.'}), 500

    if not sucesso:
        return jsonify({'status': 'error', 'message': mensagem or 'Falha ao emitir certidão FGTS.'}), 400

    certidao = Certidao.query.get(certidao_id)
    data_formatada = certidao.data_validade.strftime('%d/%m/%Y') if certidao and certidao.data_validade else None

    return jsonify({
        'status': 'ok',
        'certidao_id': certidao_id,
        'data_formatada': data_formatada,
        'nova_classe': _fgts_status_por_data(certidao.data_validade if certidao else None)
    })


def _get_visualizar_serializer():
    secret = current_app.config.get('SECRET_KEY') or 'certidoes-secret'
    return URLSafeTimedSerializer(secret, salt='visualizar-certidao')


def _gerar_visualizar_token(certidao_id):
    return _get_visualizar_serializer().dumps({'cid': certidao_id})


def _carregar_visualizar_token(token, max_age=60 * 60 * 24):
    try:
        data = _get_visualizar_serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return data.get('cid') if isinstance(data, dict) else None


@bp.app_template_global()
def visualizar_token(certidao_id):
    return _gerar_visualizar_token(certidao_id)


def calcular_validade_padrao(certidao, data_encontrada=None):
    if data_encontrada is not None:
        return data_encontrada

    tipo_chave = certidao.tipo.name
    hoje = date.today()

    if tipo_chave == 'MUNICIPAL':
        return None

    if tipo_chave in ['TRABALHISTA', 'FGTS', 'FEDERAL']:
        cfg = VALIDADES_CERTIDOES.get(tipo_chave) or {}
        dias = cfg.get('validade_dias_padrao')
        if dias:
            return hoje + timedelta(days=dias)
        return None

    if tipo_chave == 'ESTADUAL':
        estado = (certidao.empresa.estado or '').strip().upper()
        estadual_cfg = VALIDADES_CERTIDOES.get('ESTADUAL', {})
        uf_cfg = estadual_cfg.get(estado) or {}
        dias = uf_cfg.get('validade_dias_padrao')
        if dias:
            return hoje + timedelta(days=dias)
        return None

    return None


def _extrair_validade_pdf_federal(caminho_pdf):
    if not caminho_pdf:
        return None

    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        print(f"[FEDERAL] Erro ao ler PDF: {exc}")
        return None

    match = re.search(r"Válida\s+até\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y").date()
    except ValueError:
        return None

def _login_certificado_rs(driver, login_url, cert_url, timeout=120):
    driver.get(login_url)

    try:
        ok_btn = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='Action'][value='OK']"))
        )
        ok_btn.click()
    except Exception:
        pass

    time.sleep(2)
    driver.get(cert_url)


def _erro_indica_navegador_fechado(exc):
    tipos_fechamento = (
        InvalidSessionIdException,
        NoSuchWindowException,
        WebDriverException,
        ConnectionResetError,
    )
    marcadores = (
        'connection aborted',
        'connectionreseterror',
        'chrome not reachable',
        'disconnected',
        'invalid session id',
        'no such window',
        'target window already closed',
        'web view not found',
    )

    atual = exc
    for _ in range(6):
        if atual is None:
            break

        if isinstance(atual, tipos_fechamento):
            return True

        texto = f"{type(atual).__name__}: {atual}".lower()
        if any(marcador in texto for marcador in marcadores):
            return True

        atual = getattr(atual, '__cause__', None) or getattr(atual, '__context__', None)

    return False


@bp.route('/')
def dashboard():
    status_filtros = request.args.getlist('status')
    tipo_filtros = request.args.getlist('tipo')
    estado_filtro = request.args.get('estado', '')

    query = db.session.query(Empresa).distinct()

    hoje = date.today()
    join_certidao_feito = False

    if not status_filtros:
        status_filtros = ['todas']

    if 'todas' in status_filtros or not status_filtros:
        status_filtros = ['todas']
    else:
        query = query.join(Certidao)
        join_certidao_feito = True

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

    if not tipo_filtros or 'todas' in tipo_filtros:
        tipo_filtros = ['todas']
    else:
        tipos_enum = []
        mapa_tipo = {
            'federal': TipoCertidao.FEDERAL,
            'fgts': TipoCertidao.FGTS,
            'estadual': TipoCertidao.ESTADUAL,
            'municipal': TipoCertidao.MUNICIPAL,
            'trabalhista': TipoCertidao.TRABALHISTA,
        }
        for t in tipo_filtros:
            enum_val = mapa_tipo.get(t)
            if enum_val:
                tipos_enum.append(enum_val)
        if tipos_enum:
            if not join_certidao_feito:
                query = query.join(Certidao)
                join_certidao_feito = True
            query = query.filter(Certidao.tipo.in_(tipos_enum))
        else:
            query = query.filter(Empresa.id == -1)

    if estado_filtro:
        query = query.filter(Empresa.estado == estado_filtro)

    empresas = query.order_by(Empresa.id).all()

    estados_disponiveis = [
        row[0] for row in
        db.session.query(Empresa.estado).distinct().order_by(Empresa.estado).all()
    ]

    municipios = Municipio.query.all()

    urls_municipais = {}
    for m in municipios:
        if not m.url_certidao:
            continue
        nome = (m.nome or '').strip()
        url = m.url_certidao
        
        urls_municipais[nome] = url
        nome_sem = file_manager.remover_acentos(nome)
        urls_municipais[nome_sem] = url
        
    return render_template(
        'dashboard.html',
        empresas=empresas,
        status_filtros=status_filtros,
        tipo_filtros=tipo_filtros,
        estado_filtro=estado_filtro,
        estados_disponiveis=estados_disponiveis,
        hoje=hoje,
        sites_urls=SITES_CERTIDOES,
        urls_municipais=urls_municipais
    )


@bp.route('/empresa/nova', endpoint='nova_empresa')
def pagina_nova_empresa():
    return render_template('nova_empresa.html')


@bp.route('/relatorios')
def relatorios():
    hoje = date.today()
    empresas_total = Empresa.query.count()
    certidoes = Certidao.query.all()

    total_certidoes = len(certidoes)
    pendentes = 0
    vencidas = 0
    a_vencer = 0

    for certidao in certidoes:
        if certidao.status_especial == StatusEspecial.PENDENTE:
            pendentes += 1
            continue

        if not certidao.data_validade:
            continue

        dias_restantes = (certidao.data_validade - hoje).days
        if dias_restantes < 0:
            vencidas += 1
        elif dias_restantes <= 7:
            a_vencer += 1

    return render_template(
        'relatorios.html',
        empresas_total=empresas_total,
        total_certidoes=total_certidoes,
        pendentes=pendentes,
        vencidas=vencidas,
        a_vencer=a_vencer,
    )


@bp.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')


@bp.route('/empresa/adicionar', methods=['POST'])
def adicionar_empresa():
    # dados formulário
    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
    estado = request.form.get('estado')
    cidade = request.form.get('cidade')
    inscricao = request.form.get('inscricao_mobiliaria')
    origem = request.form.get('origem')

    def _redirect_apos_cadastro():
        if origem == 'nova_empresa':
            return redirect(url_for('main.nova_empresa'))
        return redirect(url_for('main.dashboard'))

    if not cnpj or len(cnpj) < 18:
        flash('CNPJ incompleto, preencha todos os dígitos.', 'warning')
        return _redirect_apos_cadastro()

    # validacao
    empresa_existente = Empresa.query.filter_by(cnpj=cnpj).first()
    if empresa_existente:
        flash(f'Empresa com CNPJ {cnpj} já está cadastrada.', 'warning')
        return _redirect_apos_cadastro()

    # Cria objeto empresa
    empresa_nova = Empresa(
        nome=nome,
        cnpj=cnpj,
        estado=estado,
        cidade=cidade,
        # Garante que seja nulo se vazio
        inscricao_mobiliaria=inscricao if inscricao else None
    )
    db.session.add(empresa_nova)

    cidade_norm = file_manager.remover_acentos(cidade or '').upper()
    is_imbe = cidade_norm == 'IMBE'

    for tipo in TipoCertidao:
        if tipo == TipoCertidao.MUNICIPAL:
            if is_imbe:
                db.session.add(Certidao(
                    tipo=tipo,
                    subtipo=SubtipoCertidao.GERAL,
                    empresa=empresa_nova,
                    data_validade=None
                ))
                db.session.add(Certidao(
                    tipo=tipo,
                    subtipo=SubtipoCertidao.MOBILIARIO,
                    empresa=empresa_nova,
                    data_validade=None
                ))
            else:
                db.session.add(Certidao(
                    tipo=tipo,
                    empresa=empresa_nova,
                    data_validade=None
                ))
            continue

        db.session.add(Certidao(
            tipo=tipo,
            empresa=empresa_nova,
            data_validade=None
        ))

    # Salva no banco
    try:
        db.session.commit()
        flash(f'Empresa "{nome}" cadastrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar empresa: {e}', 'danger')

    return _redirect_apos_cadastro()


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

def _automatizar_fgts(contexto, driver, wait, certidao):
    def _parar_se_solicitado():
        if _fgts_stop_requested():
            try:
                driver.quit()
            except Exception:
                pass
            return True
        return False

    def _aguardar_clickable(locator, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _parar_se_solicitado():
                return None
            try:
                return WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable(locator)
                )
            except TimeoutException:
                continue
        return None

    try:
        btn_consultar = _aguardar_clickable((By.ID, "mainForm:btnConsultar"))
        if not btn_consultar:
            return
        print("clicando em Consultar")
        if _parar_se_solicitado():
            return
        btn_consultar.click()
        time.sleep(1)

        btn_certificado = _aguardar_clickable((By.ID, "mainForm:j_id51"))
        if not btn_certificado:
            return
        print("clicando em Certificado")
        if _parar_se_solicitado():
            return
        btn_certificado.click()
        time.sleep(1)

        # tentar localizar data de validade na página
        if not contexto.get('data_encontrada'):
            try:
                elemento = driver.find_element(
                    By.XPATH, "//p[contains(., 'Validade:')]")
                texto = elemento.text
                if " a " in texto:
                    parte_data = texto.split(" a ")[-1].strip()[:10]
                    data_val = datetime.strptime(
                        parte_data, '%d/%m/%Y').date()
                    contexto['data_encontrada'] = data_val
            except Exception as e:
                if _fgts_stop_requested():
                    return
                print(f"erro ao encontrar data fgts: {e}")

        btn_visualizar = _aguardar_clickable((By.ID, "mainForm:btnVisualizar"))
        if not btn_visualizar:
            return
        print("clicando em Visualizar")
        if _parar_se_solicitado():
            return
        btn_visualizar.click()
        time.sleep(1)

        # gerar pdf automaticamente com CDP
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
            if _parar_se_solicitado():
                return
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
                contexto['arquivo_salvo_msg'] = f"Arquivo salvo em: {msg}"
                contexto['pular_monitoramento'] = True
                print(contexto['arquivo_salvo_msg'])
                try:
                    certidao.caminho_arquivo = msg
                    db.session.commit()
                except Exception as e_db:
                    db.session.rollback()
                    print(f"[FGTS] Aviso: não foi possível salvar caminho no banco: {e_db}")
        except Exception as e_pdf:
            print(f"[FGTS] Erro ao gerar PDF automaticamente: {e_pdf}")
    except Exception as e:
        if _fgts_stop_requested():
            return
        print(f"erro automação emissao FGTS: {e}")


def _carregar_config_municipio(regra_municipio):
    if not regra_municipio:
        return None
    raw = regra_municipio.config_automacao
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError) as exc:
        print(f"[MUNICIPAL] Config inválida para {regra_municipio.nome}: {exc}")
        return None


def _executar_steps_municipio(driver, wait, steps, cnpj_limpo, inscricao_limpa):
    if not steps:
        return

    by_map = {
        'id': By.ID,
        'name': By.NAME,
        'css_selector': By.CSS_SELECTOR,
        'xpath': By.XPATH,
        'class_name': By.CLASS_NAME
    }

    for step in steps:
        tipo = (step or {}).get('tipo')
        if not tipo:
            continue

        if tipo == 'sleep':
            time.sleep(float(step.get('seconds', 1)))
            continue

        if tipo == 'refresh':
            driver.refresh()
            time.sleep(float(step.get('sleep', 1)))
            continue

        if tipo == 'wait_for':
            by = by_map.get(step.get('by'))
            locator = step.get('locator')
            if not by or not locator:
                continue
            timeout = step.get('timeout', 10)
            state = step.get('state', 'clickable')
            cond = EC.element_to_be_clickable if state == 'clickable' else EC.presence_of_element_located
            WebDriverWait(driver, timeout).until(cond((by, locator)))
            continue

        if tipo in ['click', 'click_js', 'select', 'fill']:
            by = by_map.get(step.get('by'))
            locator = step.get('locator')
            if not by or not locator:
                continue

            elemento = wait.until(EC.element_to_be_clickable((by, locator)))

            if tipo == 'click':
                elemento.click()
                time.sleep(float(step.get('sleep', 0.5)))
                continue

            if tipo == 'click_js':
                driver.execute_script("arguments[0].click();", elemento)
                time.sleep(float(step.get('sleep', 0.5)))
                continue

            if tipo == 'select':
                select_obj = Select(elemento)
                value = step.get('value')
                text = step.get('text')
                contains = step.get('text_contains')
                if value is not None:
                    select_obj.select_by_value(value)
                elif text:
                    select_obj.select_by_visible_text(text)
                elif contains:
                    for opt in select_obj.options:
                        if contains.upper() in opt.text.upper():
                            select_obj.select_by_visible_text(opt.text)
                            break
                time.sleep(float(step.get('sleep', 0.5)))
                continue

            if tipo == 'fill':
                value = step.get('value')
                if value == 'cnpj':
                    value = cnpj_limpo
                elif value == 'inscricao':
                    value = inscricao_limpa
                if value is None:
                    continue
                elemento.clear()
                elemento.click()
                elemento.send_keys(value)
                time.sleep(float(step.get('sleep', 0.5)))
                continue


# baixar certidao com automacao salvamento ||||
# VVVV

@bp.route('/certidao/baixar/<int:certidao_id>')
def baixar_certidao(certidao_id):
    file_manager.criar_chave_interrupcao()
    certidao = Certidao.query.get_or_404(certidao_id)
    tipo_certidao_chave = certidao.tipo.name

    by_map = {
        'id': By.ID,
        'css_selector': By.CSS_SELECTOR,
        'xpath': By.XPATH,
        'name': By.NAME
    }

    def _get_by(key):
        return by_map.get(key)

    def _calcular_validade_sem_data(tipo_chave, regra):
        if tipo_chave == 'MUNICIPAL':
            if regra and regra.validade_dias:
                return date.today() + timedelta(days=regra.validade_dias)
            return None
        return calcular_validade_padrao(certidao, None)

    def _aplicar_variantes_imbe(info_site_cfg, config_cfg, tipo_escolhido):
        if tipo_escolhido != 'geral':
            return
        cfg_geral = (((config_cfg or {}).get('imbe_variantes') or {}).get('geral') or {})
        info_site_cfg['url'] = cfg_geral.get(
            'url',
            'https://grp.imbe.rs.gov.br/grp/acessoexterno/programaAcessoExterno.faces?codigo=684509'
        )
        info_site_cfg['cnpj_field_id'] = cfg_geral.get('cnpj_field_id', 'form:cnpjD')
        info_site_cfg['by'] = cfg_geral.get('by', 'name')
        info_site_cfg['pre_fill_click_id'] = cfg_geral.get(
            'pre_fill_click_id',
            info_site_cfg.get('pre_fill_click_id')
        )
        info_site_cfg['pre_fill_click_by'] = cfg_geral.get(
            'pre_fill_click_by',
            info_site_cfg.get('pre_fill_click_by')
        )
        info_site_cfg['inscricao_field_id'] = None
        info_site_cfg['inscricao_field_by'] = None

    def _nome_certidao_imbe(nome_padrao, tipo_escolhido):
        if tipo_escolhido == 'geral':
            return 'CERTIDAO MUNICIPAL'
        if tipo_escolhido == 'mobiliario':
            return 'CERTIDAO MOBILIARIO'
        return nome_padrao

    def _resolve_imbe_tipo(cert_subtipo):
        if cert_subtipo == SubtipoCertidao.GERAL:
            return 'geral'
        if cert_subtipo == SubtipoCertidao.MOBILIARIO:
            return 'mobiliario'
        return ''

    regra_municipio = None
    config_municipal = None
    usar_config_municipal = False
    imbe_tipo = (request.args.get('imbe_tipo') or '').strip().lower()

    if not imbe_tipo and certidao.subtipo:
        imbe_tipo = _resolve_imbe_tipo(certidao.subtipo)

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
        cidade_norm = file_manager.remover_acentos(cidade_empresa).upper()
        
        for m in Municipio.query.all():
            nome_norm = file_manager.remover_acentos(m.nome or '').upper()
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
            if regra_municipio.usar_slow_typing:
                info_site['slow_typing'] = True

            if regra_municipio.automacao_ativa is False:
                return jsonify({
                    "status": "manual_required",
                    "message": "Automação desativada para este município. Use o botão 'Abrir Site'."
                })

            config_municipal = _carregar_config_municipio(regra_municipio)
            usar_config_municipal = bool(config_municipal)

            cidade_regra_norm = file_manager.remover_acentos(regra_municipio.nome or '').upper()
            if cidade_regra_norm == 'IMBE':
                if imbe_tipo not in ['mobiliario', 'geral']:
                    return jsonify({
                        'status': 'manual_required',
                        'message': 'Para Imbé, selecione no modal: Certidão Municipal Mobiliário ou Geral.'
                    })

                _aplicar_variantes_imbe(info_site, config_municipal, imbe_tipo)

            if usar_config_municipal and config_municipal.get('skip_cnpj_fill'):
                info_site['cnpj_field_id'] = None
            
        else:
            return jsonify({'status': 'error', 'message': 'Regra municipal não encontrada'})

    if tipo_certidao_chave == 'MUNICIPAL' and not usar_config_municipal:
        return jsonify({
            'status': 'error',
            'message': 'Municipio sem automacao. Configure para prosseguir.'
        })

    cnpj_limpo = ''.join(filter(str.isdigit, certidao.empresa.cnpj))
    inscricao_limpa = certidao.empresa.inscricao_mobiliaria or ''

    nome_certidao_arquivo = certidao.tipo.value
    if tipo_certidao_chave == 'MUNICIPAL' and regra_municipio:
        cidade_regra_norm = file_manager.remover_acentos(regra_municipio.nome or '').upper()
        if cidade_regra_norm == 'IMBE':
            nome_certidao_arquivo = _nome_certidao_imbe(nome_certidao_arquivo, imbe_tipo)

    driver = None
    data_encontrada = None
    arquivo_salvo_msg = None
    pular_monitoramento = False
    rs_autoselect_temporario_ativo = False

    # contexto compartilhado com helpers de steps
    contexto = {
        'arquivo_salvo_msg': None,
        'pular_monitoramento': False,
        'data_encontrada': None
    }

    tempo_inicio = time.time()
    estado_emp = (certidao.empresa.estado or '').strip().upper()
    usar_rs_autoselect = (
        tipo_certidao_chave == 'ESTADUAL'
        and estado_emp == 'RS'
        and bool(info_site.get('login_cert_url'))
    )

    try:
        print(f"--- INICIANDO AUTOMAÇÃO ({tipo_certidao_chave}) ---")

        if usar_rs_autoselect:
            rs_autoselect_temporario_ativo = _ativar_politica_autoselect_rs_temporaria()

        driver = _criar_driver_chrome(
            anonimo=not usar_rs_autoselect,
            usar_perfil=usar_rs_autoselect
        )
        
        wait = WebDriverWait(driver, 20)

        if tipo_certidao_chave == 'ESTADUAL' and estado_emp == 'RS' and info_site.get('login_cert_url'):
            print("1. Acessando login com certificado (RS)")
            _login_certificado_rs(
                driver,
                info_site.get('login_cert_url'),
                info_site.get('url')
            )
            print('pronto')
        else:
            print(f"1. Acessando a URL: {info_site.get('url')}")
            driver.get(info_site.get('url'))
        
        if tipo_certidao_chave == 'MUNICIPAL':
            if usar_config_municipal:
                steps_before = config_municipal.get('before_cnpj', []) if config_municipal else []
                _executar_steps_municipio(
                    driver,
                    wait,
                    steps_before,
                    cnpj_limpo,
                    inscricao_limpa
                )


        def executar_acao_aux(nome_acao):
            # 1 pre click inicial
            if nome_acao == 'pre_fill':
                if not info_site.get('pre_fill_click_id'):
                    return
                click_by = _get_by(info_site.get('pre_fill_click_by'))
                if not click_by:
                    return
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

            # 2 select de tipo
            elif nome_acao == 'select_tipo':
                if not info_site.get('tipo_select_id'):
                    return
                select_by = _get_by(info_site.get('tipo_select_by', 'id')) or By.ID
                try:
                    select_el = wait.until(
                        EC.element_to_be_clickable(
                            (select_by, info_site['tipo_select_id']))
                    )
                    select_obj = Select(select_el)

                    value = info_site.get('tipo_select_value')
                    if value is not None:
                        select_obj.select_by_value(value)
                    else:
                        text = info_site.get('tipo_select_text')
                        if text:
                            select_obj.select_by_visible_text(text)

                    time.sleep(1)
                    print("Select de tipo configurado com sucesso.")
                except Exception as e:
                    print(f"Aviso: não foi possível configurar select de tipo: {e}")

            #3 ação específica para FGTS: emitir e salvar PDF
            elif nome_acao == 'fgts_emitir_pdf':
                try:
                    _automatizar_fgts(contexto, driver, wait, certidao)
                except Exception as e:
                    print(f"[FGTS] Erro na ação fgts_emitir_pdf: {e}")

        # ordem das ações antes do cnpj
        steps_before_cnpj = info_site.get('steps_before_cnpj')
        if steps_before_cnpj is None:
            # padrão atual: pre_fill depois select_tipo
            steps_before_cnpj = ['pre_fill', 'select_tipo']

        for step in steps_before_cnpj:
            executar_acao_aux(step)

        if info_site.get('cnpj_field_id'):
            field_by = _get_by(info_site.get('by'))
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

                    if tipo_certidao_chave == 'TRABALHISTA':
                        campo1.send_keys(Keys.TAB)
                except:
                    pass

        if tipo_certidao_chave == 'MUNICIPAL' and usar_config_municipal:
            steps_after = config_municipal.get('after_cnpj', []) if config_municipal else []
            _executar_steps_municipio(
                driver,
                wait,
                steps_after,
                cnpj_limpo,
                inscricao_limpa
            )

        # ordem das ações depois do cnpj
        steps_after_cnpj = info_site.get('steps_after_cnpj')
        if steps_after_cnpj is None:
            steps_after_cnpj = []
        for step in steps_after_cnpj:
            executar_acao_aux(step)

        # sincroniza variaves ja usadas
        if contexto.get('pular_monitoramento'):
            pular_monitoramento = True
        if contexto.get('arquivo_salvo_msg'):
            arquivo_salvo_msg = contexto['arquivo_salvo_msg']
        if contexto.get('data_encontrada'):
            data_encontrada = contexto['data_encontrada']

        if info_site.get('inscricao_field_id'):
            field_by = _get_by(info_site.get('inscricao_field_by'))
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
                            nome_certidao_arquivo
                        )

                        if sucesso:
                            arquivo_salvo_msg = f"Arquivo salvo em: {msg}"
                            print(arquivo_salvo_msg)
                            try:
                                certidao.caminho_arquivo = msg
                                db.session.commit()
                            except Exception as e_db:
                                db.session.rollback()
                                print(f"Aviso: não foi possível salvar caminho no banco: {e_db}")
                            try:
                                try:
                                    janelas_abertas = list(driver.window_handles)
                                except Exception:
                                    janelas_abertas = []

                                def _is_blank(url):
                                    url = (url or '').lower()
                                    return url == 'about:blank' or url == ''

                                if len(janelas_abertas) > 1:
                                    ultima = janelas_abertas[-1]
                                    try:
                                        driver.switch_to.window(ultima)
                                        driver.close()
                                    except Exception:
                                        pass

                                time.sleep(1)
                                try:
                                    driver.quit()
                                except Exception as e_quit:
                                    print(f"Aviso: erro ao fechar Chrome: {e_quit}")

                                break
                            except Exception as e:
                                print(f"Erro ao fechar Chrome: {e}")
                        else:
                            print(f"Erro ao salvar: {msg}")

                time.sleep(1)
        else:
            print("--- FGTS: monitoramento pulado (PDF gerado via CDP) ---")
            if driver:
                try:
                    time.sleep(1)
                    driver.quit()
                except Exception as e_quit:
                    print(f"Aviso: erro ao fechar Chrome no fluxo FGTS/CDP: {e_quit}")

    except Exception as e:
        print(f"!!!!!!!!!! ERRO NO SELENIUM !!!!!!!!!!\n{e}")
        if _erro_indica_navegador_fechado(e):
            print("Chrome fechado durante a automação; retornando fluxo pendente.")
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            return jsonify({
                'status': 'window_closed_no_file',
                'certidao_id': certidao_id,
                'tipo_certidao': nome_certidao_arquivo
            })
        if driver:
            try:
                driver.quit()
            except:
                pass
        return jsonify({"status": "error", "message": "Ocorreu um erro na automação."}), 500
    finally:
        if rs_autoselect_temporario_ativo:
            _desativar_politica_autoselect_rs_temporaria()

    response_data = {'status': 'unknown'}

    if arquivo_salvo_msg:
        response_data['status'] = 'success_file_saved'
        response_data['mensagem_arquivo'] = arquivo_salvo_msg
        response_data['certidao_id'] = certidao_id
        response_data['tipo_certidao'] = nome_certidao_arquivo
        response_data['visualizar_token'] = _gerar_visualizar_token(certidao_id)

        if data_encontrada:
            print(
                f"[DEBUG] Data de validade encontrada: {data_encontrada.strftime('%d/%m/%Y')}")
            response_data['nova_data'] = data_encontrada.strftime('%Y-%m-%d')
            response_data['data_formatada'] = data_encontrada.strftime(
                '%d/%m/%Y')
        else:
            data_calc = None

            data_calc = _calcular_validade_sem_data(tipo_certidao_chave, regra_municipio)

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
        response_data['tipo_certidao'] = nome_certidao_arquivo

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
                try:
                    certidao.caminho_arquivo = msg
                    db.session.commit()
                except Exception as e_db:
                    db.session.rollback()
                    print(f"[FEDERAL] Aviso: não foi possível salvar caminho no banco: {e_db}")
                validade_pdf = _extrair_validade_pdf_federal(msg)
                if validade_pdf:
                    return jsonify({
                        'status': 'success',
                        'mensagem': f"Arquivo salvo no servidor: {msg}",
                        'visualizar_token': _gerar_visualizar_token(certidao_id),
                        'data_validade': validade_pdf.strftime('%Y-%m-%d'),
                        'data_validade_formatada': validade_pdf.strftime('%d/%m/%Y')
                    })
                return jsonify({
                    'status': 'success',
                    'mensagem': f"Arquivo salvo no servidor: {msg}",
                    'visualizar_token': _gerar_visualizar_token(certidao_id)
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


@bp.route('/certidao/visualizar/<token>')
def visualizar_certidao(token):
    certidao_id = _carregar_visualizar_token(token)
    if not certidao_id:
        return 'Token inválido ou expirado.', 404

    certidao = Certidao.query.get_or_404(certidao_id)
    caminho = certidao.caminho_arquivo

    if not caminho or not os.path.exists(caminho):
        caminho = file_manager.localizar_certidao_existente(
            certidao.empresa.nome,
            certidao.tipo.value,
            certidao.subtipo.value if certidao.subtipo else None
        )
        if caminho:
            certidao.caminho_arquivo = caminho
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    if not caminho or not os.path.exists(caminho):
        return 'Arquivo não encontrado para esta certidão.', 404

    return send_file(
        caminho,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=os.path.basename(caminho)
    )


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
