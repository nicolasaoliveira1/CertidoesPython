from flask import Blueprint, render_template
from app.models import Empresa
#esqueleto do routes para rodar a criação do banco, rotas serão definidas aqui posteriormente

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    empresas = Empresa.query.order_by(Empresa.nome).all()
    
    return render_template('dashboard.html', empresas=empresas)
