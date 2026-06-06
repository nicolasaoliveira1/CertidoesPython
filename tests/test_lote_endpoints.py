"""Caracterizacao das rotas de lote (FGTS / Estadual RS / Municipal).

Trava o contrato HTTP (paths, status code, campo `status` e tokens das
mensagens) antes/depois de extrair o registrador de rotas (C3). Exercita
apenas caminhos seguros: status, info e erros 400 de `iniciar` — nunca
dispara um worker/Selenium.
Rodar: python tests/test_lote_endpoints.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('QUIET_WERKZEUG_LOGS', 'true')
# fixa a flag p/ exercitar deterministicamente a precondicao do lote RS
os.environ.setdefault('RS_ALTCHA_AUTOSOLVE_ENABLED', 'false')
_fd, _DBPATH = tempfile.mkstemp(suffix='.db')
os.close(_fd)
os.environ['DATABASE_URL'] = 'sqlite:///' + _DBPATH.replace(os.sep, '/')

from app import create_app, db
from app.models import Empresa, Certidao, TipoCertidao

PREFIXOS = {'fgts': '/fgts', 'rs': '/estadual-rs', 'municipal': '/municipal'}


def setup():
    app = create_app()
    ids = {}
    with app.app_context():
        db.create_all()
        e = Empresa(nome='Empresa Teste', cnpj='11.111.111/1111-11',
                    estado='RS', cidade='Tramandai')
        db.session.add(e)
        db.session.commit()
        for t in TipoCertidao:
            db.session.add(Certidao(tipo=t, empresa=e))
        db.session.commit()
        ids['fgts'] = Certidao.query.filter_by(tipo=TipoCertidao.FGTS).first().id
        ids['rs'] = Certidao.query.filter_by(tipo=TipoCertidao.ESTADUAL).first().id
        ids['municipal'] = Certidao.query.filter_by(tipo=TipoCertidao.MUNICIPAL).first().id
    return app, ids


def test_status_idle(client):
    for pref in PREFIXOS.values():
        r = client.get(f'{pref}/lote/status')
        assert r.status_code == 200, (pref, r.status_code)
        j = r.get_json()
        assert j['status'] == 'idle', (pref, j['status'])
        assert j['total'] == 0
    print('ok status_idle')


def test_info(client, ids):
    chaves = {'ids', 'total', 'scope', 'vencidas', 'a_vencer', 'pendentes'}
    for k, pref in PREFIXOS.items():
        r = client.get(f'{pref}/lote/info/{ids[k]}')
        assert r.status_code == 200, (pref, r.status_code)
        j = r.get_json()
        assert j['status'] == 'ok', (pref, j)
        assert chaves <= set(j.keys()), (pref, set(j.keys()))
    print('ok info')


def test_iniciar_sem_certidao(client):
    for pref in PREFIXOS.values():
        r = client.post(f'{pref}/lote/iniciar', json={})
        assert r.status_code == 400, (pref, r.status_code)
        assert r.get_json()['status'] == 'error', pref
    print('ok iniciar_sem_certidao')


def test_iniciar_vazio_ou_precondicao(client, ids):
    # FGTS/Municipal: certidoes sem data -> lote vazio (400, sem worker)
    r = client.post('/fgts/lote/iniciar', json={'certidao_id': ids['fgts']})
    assert r.status_code == 400, r.status_code
    m = r.get_json()['message']
    assert 'FGTS' in m and 'vencer' in m, m

    r = client.post('/municipal/lote/iniciar', json={'certidao_id': ids['municipal']})
    assert r.status_code == 400, r.status_code
    assert 'Municipal' in r.get_json()['message'], r.get_json()['message']

    # Estadual RS: flag desativada -> precondicao barra antes do worker
    r = client.post('/estadual-rs/lote/iniciar', json={'certidao_id': ids['rs']})
    assert r.status_code == 400, r.status_code
    assert 'RS_ALTCHA_AUTOSOLVE_ENABLED' in r.get_json()['message'], r.get_json()['message']
    print('ok iniciar_vazio_ou_precondicao')


def main():
    app, ids = setup()
    client = app.test_client()
    try:
        test_status_idle(client)
        test_info(client, ids)
        test_iniciar_sem_certidao(client)
        test_iniciar_vazio_ou_precondicao(client, ids)
        print('\nTodos os testes de rotas de lote passaram.')
    finally:
        try:
            os.remove(_DBPATH)
        except OSError:
            pass


if __name__ == '__main__':
    main()
