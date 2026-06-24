"""Testes do caminho de rede configuravel (config no banco > env > default)."""
from app import db, file_manager
from app.models import ConfiguracaoSistema


def test_get_caminho_rede_cai_para_env_sem_config(app, ids):
    # sem linha de ConfiguracaoSistema -> usa o fallback (env CAMINHO_REDE)
    with app.app_context():
        assert ConfiguracaoSistema.query.get(1) is None
        assert file_manager.get_caminho_rede() == file_manager.CAMINHO_REDE


def test_get_caminho_rede_usa_config_do_banco(app, ids):
    with app.app_context():
        db.session.add(ConfiguracaoSistema(id=1, a_vencer_dias=7, caminho_rede=r'X:\PASTAS'))
        db.session.commit()
        assert file_manager.get_caminho_rede() == r'X:\PASTAS'
        assert file_manager.get_caminho_sem_movimento().startswith(r'X:\PASTAS')


def test_get_caminho_rede_ignora_config_em_branco(app, ids):
    with app.app_context():
        db.session.add(ConfiguracaoSistema(id=1, a_vencer_dias=7, caminho_rede='   '))
        db.session.commit()
        # string vazia/espacos no banco -> cai para o fallback
        assert file_manager.get_caminho_rede() == file_manager.CAMINHO_REDE


def test_configuracoes_salva_caminho_rede(client, app, ids):
    client.post('/configuracoes', data={
        'a_vencer_dias': '7',
        'caminho_rede': r'Y:\REDE\EMPRESAS',
    })
    with app.app_context():
        cfg = ConfiguracaoSistema.query.get(1)
        assert cfg.caminho_rede == r'Y:\REDE\EMPRESAS'


def test_configuracoes_caminho_rede_em_branco_volta_para_none(client, app, ids):
    client.post('/configuracoes', data={'a_vencer_dias': '7', 'caminho_rede': '  '})
    with app.app_context():
        cfg = ConfiguracaoSistema.query.get(1)
        assert cfg.caminho_rede is None
