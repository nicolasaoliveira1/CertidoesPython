import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY não configurada no .env")
    #--- BANCO DE DADOS ANTIGO (SQLite) ---#
    #(Comentado para não usar mais)#
    # --- NOVO BANCO DE DADOS (MySQL) ---
    # Estrutura: mysql+pymysql://USUARIO:SENHA@IP_DO_SERVIDOR/NOME_DO_BANCO
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')

        
    SQLALCHEMY_TRACK_MODIFICATIONS = False