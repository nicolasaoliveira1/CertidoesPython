from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_object(config_class)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # garante que nenhum resquício de execução anterior bloqueie o monitor federal
    _limpar_chave_interrupcao_federal()
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    from app import routes, models
    app.register_blueprint(routes.bp)
    
    return app


def _limpar_chave_interrupcao_federal():
    # remove o arquivo de monitoramento federal do disco caso haja crash
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stop_federal_monitor.txt')
    if os.path.exists(caminho):
        try:
            os.remove(caminho)
            print("[startup] Arquivo stop_federal_monitor.txt removido (resquício de execução anterior).")
        except OSError as e:
            print(f"[startup] Aviso: não foi possível remover stop_federal_monitor.txt: {e}")
