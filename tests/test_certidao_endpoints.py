"""Caracterizacao dos endpoints de validade/pendencia de certidao.

Trava o contrato de /certidao/atualizar(_json), /salvar_data_confirmada e
/marcar_pendente(_json) antes/depois de extrair certidao_service (M1) e o
helper de classe de status (M2). Sem Selenium.
Rodar: python tests/test_certidao_endpoints.py
"""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('QUIET_WERKZEUG_LOGS', 'true')
_fd, _DBPATH = tempfile.mkstemp(suffix='.db')
os.close(_fd)
os.environ['DATABASE_URL'] = 'sqlite:///' + _DBPATH.replace(os.sep, '/')

from app import create_app, db
from app.models import Empresa, Certidao, TipoCertidao, StatusEspecial


def setup():
    app = create_app()
    with app.app_context():
        db.create_all()
        e = Empresa(nome='Empresa Teste', cnpj='11.111.111/1111-11',
                    estado='RS', cidade='Tramandai')
        db.session.add(e)
        db.session.commit()
        c = Certidao(tipo=TipoCertidao.TRABALHISTA, empresa=e)
        db.session.add(c)
        db.session.commit()
        cid = c.id
    return app, cid


def _fmt(d):
    return d.isoformat()


def test_atualizar_json_cores(client, cid):
    casos = [
        (date.today() + timedelta(days=365), 'status-verde'),
        (date.today() - timedelta(days=10), 'status-vermelho'),
        (date.today() + timedelta(days=3), 'status-amarelo'),
    ]
    for d, esperado in casos:
        r = client.post(f'/certidao/atualizar_json/{cid}', json={'nova_validade': _fmt(d)})
        assert r.status_code == 200, (esperado, r.status_code)
        j = r.get_json()
        assert j['status'] == 'success', j
        assert j['nova_classe'] == esperado, (d, j['nova_classe'], esperado)
        assert j['nova_data_formatada'] == d.strftime('%d/%m/%Y')
    print('ok atualizar_json_cores')


def test_atualizar_json_sem_data(client, cid):
    r = client.post(f'/certidao/atualizar_json/{cid}', json={})
    assert r.status_code == 400, r.status_code
    assert r.get_json()['status'] == 'error'
    print('ok atualizar_json_sem_data')


def test_salvar_data_confirmada(client, cid):
    d = date.today() + timedelta(days=365)
    r = client.post('/certidao/salvar_data_confirmada',
                    json={'certidao_id': cid, 'nova_validade': _fmt(d)})
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j['status'] == 'success'
    assert j['nova_classe'] == 'status-verde', j['nova_classe']
    assert j['message'] == 'Data confirmada e atualizada com sucesso!'
    print('ok salvar_data_confirmada')


def test_marcar_pendente_json(app, client, cid):
    r = client.post(f'/certidao/marcar_pendente_json/{cid}', json={})
    assert r.status_code == 200, r.status_code
    assert r.get_json()['status'] == 'success'
    with app.app_context():
        c = Certidao.query.get(cid)
        assert c.status_especial == StatusEspecial.PENDENTE
        assert c.data_validade is None
    print('ok marcar_pendente_json')


def test_form_endpoints_redirect(client, cid):
    r = client.post(f'/certidao/atualizar/{cid}',
                    data={'nova_validade': _fmt(date.today() + timedelta(days=30))})
    assert r.status_code == 302, ('atualizar form', r.status_code)
    r = client.post(f'/certidao/marcar_pendente/{cid}', data={})
    assert r.status_code == 302, ('pendente form', r.status_code)
    print('ok form_endpoints_redirect')


def main():
    app, cid = setup()
    client = app.test_client()
    try:
        test_atualizar_json_cores(client, cid)
        test_atualizar_json_sem_data(client, cid)
        test_salvar_data_confirmada(client, cid)
        test_marcar_pendente_json(app, client, cid)
        test_form_endpoints_redirect(client, cid)
        print('\nTodos os testes de endpoints de certidao passaram.')
    finally:
        try:
            os.remove(_DBPATH)
        except OSError:
            pass


if __name__ == '__main__':
    main()
