import enum
from app import db
from datetime import date


class TipoCertidao(enum.Enum):
    FEDERAL = "Federal"
    FGTS = "FGTS"
    ESTADUAL = "Estadual"
    MUNICIPAL = "Municipal"
    TRABALHISTA = "Trabalhista"


class StatusEspecial(enum.Enum):
    PENDENTE = "Pendente"


class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    cidade = db.Column(db.String(50), nullable=False)
    inscricao_mobiliaria = db.Column(db.String(6), nullable=True)

    certidoes = db.relationship(
        'Certidao', backref='empresa', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Empresa {self.nome}>'


class Certidao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum(TipoCertidao), nullable=False)

    data_validade = db.Column(db.Date, nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey(
        'empresa.id'), nullable=False)
    status_especial = db.Column(db.Enum(StatusEspecial), nullable=True)

    def __repr__(self):
        return f'<Certidao {self.tipo.value} - {self.empresa.nome}>'

    @property
    def status(self):
        if self.status_especial == StatusEspecial.PENDENTE:
            return 'vermelho'

        if self.data_validade is None:
            return 'cinza'
        hoje = date.today()
        diferenca_dias = (self.data_validade - hoje).days
        if diferenca_dias < 0:
            return 'vermelho'
        elif diferenca_dias <= 7:
            return 'amarelo'
        else:
            return 'verde'


class Municipio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    url_certidao = db.Column(db.String(300), nullable=False)

    cnpj_field_id = db.Column(db.String(100), nullable=True)
    by = db.Column(db.String(20), nullable=True)

    inscricao_field_id = db.Column(db.String(100), nullable=True)
    inscricao_field_by = db.Column(db.String(20), nullable=True)

    pre_fill_click_id = db.Column(db.String(100), nullable=True)
    pre_fill_click_by = db.Column(db.String(20), nullable=True)

    shadow_host_selector = db.Column(db.String(100), nullable=True)
    inner_input_selector = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Municipio {self.nome}>'
