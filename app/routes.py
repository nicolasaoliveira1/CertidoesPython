from flask import render_template, Blueprint, request, redirect, url_for, flash
from app import db
from app.models import Empresa, Certidao, TipoCertidao
#esqueleto do routes para rodar a criação do banco, rotas serão definidas aqui posteriormente

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    empresas = Empresa.query.order_by(Empresa.nome).all()
    
    return render_template('dashboard.html', empresas=empresas)

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
