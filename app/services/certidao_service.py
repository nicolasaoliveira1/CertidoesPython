"""Operacoes de dominio sobre Certidao reutilizadas pelas rotas.

Centraliza o par mutacao + commit/rollback que estava duplicado nos
endpoints de atualizacao de validade e de marcacao como pendente.
"""
from app import db
from app.models import StatusEspecial


def aplicar_validade(certidao, nova_data):
    """Define a validade e limpa o status especial.

    Retorna (ok, erro): ok=True em sucesso; em falha de commit, faz rollback
    e devolve (False, mensagem).
    """
    certidao.data_validade = nova_data
    certidao.status_especial = None
    try:
        db.session.commit()
        return True, None
    except Exception as exc:
        db.session.rollback()
        return False, str(exc)


def marcar_pendente(certidao):
    """Marca a certidao como pendente e limpa a validade.

    Retorna (ok, erro), com a mesma semantica de aplicar_validade.
    """
    certidao.status_especial = StatusEspecial.PENDENTE
    certidao.data_validade = None
    try:
        db.session.commit()
        return True, None
    except Exception as exc:
        db.session.rollback()
        return False, str(exc)
