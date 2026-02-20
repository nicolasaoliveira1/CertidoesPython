import enum
from app import db
from datetime import date


class TipoCertidao(enum.Enum):
    FEDERAL = "Federal"
    FGTS = "FGTS"
    ESTADUAL = "Estadual"
    MUNICIPAL = "Municipal"
    TRABALHISTA = "Trabalhista"


class SubtipoCertidao(enum.Enum):
    GERAL = "Geral"
    MOBILIARIO = "Mobiliário"


class StatusEspecial(enum.Enum):
    PENDENTE = "Pendente"


class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    estado = db.Column(db.String(2), nullable=False, default='RS')
    cidade = db.Column(db.String(50), nullable=False)
    inscricao_mobiliaria = db.Column(db.String(6), nullable=True)

    certidoes = db.relationship(
        'Certidao', backref='empresa', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Empresa {self.nome}>'


class Certidao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum(TipoCertidao), nullable=False)
    subtipo = db.Column(
        db.Enum(
            SubtipoCertidao,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            name='subtipocertidao'
        ),
        nullable=True
    )

    data_validade = db.Column(db.Date, nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey(
        'empresa.id'), nullable=False)
    status_especial = db.Column(db.Enum(StatusEspecial), nullable=True)

    def __repr__(self):
        if self.subtipo:
            return f'<Certidao {self.tipo.value} - {self.subtipo.value} - {self.empresa.nome}>'
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

    @property
    def ordem_exibicao(self):
        ordem_tipo = {
            TipoCertidao.FEDERAL: 1,
            TipoCertidao.FGTS: 2,
            TipoCertidao.ESTADUAL: 3,
            TipoCertidao.MUNICIPAL: 4,
            TipoCertidao.TRABALHISTA: 5,
        }
        subtipo_ordem = 0
        if self.tipo == TipoCertidao.MUNICIPAL and self.subtipo:
            if self.subtipo == SubtipoCertidao.GERAL:
                subtipo_ordem = 1
            elif self.subtipo == SubtipoCertidao.MOBILIARIO:
                subtipo_ordem = 2
        return (ordem_tipo.get(self.tipo, 99), subtipo_ordem, self.id or 0)


class Municipio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    url_certidao = db.Column(db.String(300), nullable=False)

    automacao_ativa = db.Column(db.Boolean, nullable=False, default=True)
    validade_dias = db.Column(db.Integer, nullable=True)
    usar_slow_typing = db.Column(db.Boolean, nullable=False, default=False)
    config_automacao = db.Column(db.Text, nullable=True)

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
