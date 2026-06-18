"""Diagnostico em memoria: buffer de eventos recentes + deteccao de padroes
recorrentes (mesmo erro N vezes no mesmo alvo => provavel quebra de seletor
ou portal fora do ar).

Alimentado por um logging.Handler que le o payload ja anexado por log_event,
evitando acoplar o execution_logger a este modulo."""
import logging
import threading
from collections import deque

_MAX_EVENTOS = 200
_LIMIAR_RECORRENCIA = 3  # falhas iguais seguidas para abrir um alerta

_lock = threading.Lock()
_eventos = deque(maxlen=_MAX_EVENTOS)
_recorrencia = {}  # (error_type, alvo) -> contagem
_alertas = {}      # (error_type, alvo) -> alerta ativo

_PREFIXOS = (
    ('fgts', 'FGTS'), ('rs_', 'RS'), ('estadual', 'RS'), ('altcha', 'RS'),
    ('municipal', 'MUNI'), ('federal', 'FED'), ('http', 'HTTP'),
)


def _alvo(payload):
    if payload.get('municipio'):
        return str(payload['municipio'])
    ev = str(payload.get('event') or '').lower()
    for prefixo, nome in _PREFIXOS:
        if ev.startswith(prefixo):
            return nome
    return ev or '-'


def _hipotese(error_type):
    if error_type in ('SELECTOR', 'PORTAL', 'TIMEOUT'):
        return 'Portal pode ter mudado ou caido — revise o mapeamento/seletores.'
    if error_type == 'NETWORK_PATH':
        return 'Acesso a rede falhando em sequencia — verifique o drive de rede (Z:).'
    if error_type == 'CAPTCHA':
        return 'Captcha falhando repetidamente — verifique a chave/saldo do 2captcha.'
    return 'Falhas repetidas do mesmo tipo — investigue pelo req_id no log.'


def registrar(payload):
    """Registra um evento estruturado (o mesmo dict montado por log_event)."""
    nivel = str(payload.get('level') or 'INFO').upper()
    alvo = _alvo(payload)
    with _lock:
        _eventos.append(payload)
        if nivel == 'ERROR' and payload.get('error_type'):
            chave = (payload['error_type'], alvo)
            n = _recorrencia.get(chave, 0) + 1
            _recorrencia[chave] = n
            if n >= _LIMIAR_RECORRENCIA:
                _alertas[chave] = {
                    'error_type': payload['error_type'],
                    'alvo': alvo,
                    'ocorrencias': n,
                    'ultimo': payload.get('timestamp'),
                    'request_id': payload.get('request_id'),
                    'hipotese': _hipotese(payload['error_type']),
                }
        else:
            # qualquer atividade nao-erro no mesmo alvo zera contadores e alerta
            for chave in [k for k in _recorrencia if k[1] == alvo]:
                _recorrencia.pop(chave, None)
                _alertas.pop(chave, None)


def eventos_recentes(limite=50, nivel=None):
    """Eventos mais recentes primeiro, opcionalmente filtrados por nivel."""
    with _lock:
        itens = list(_eventos)
    if nivel:
        alvo_nivel = nivel.upper()
        itens = [e for e in itens if str(e.get('level') or 'INFO').upper() == alvo_nivel]
    return list(reversed(itens[-limite:]))


def alertas_ativos():
    with _lock:
        return list(_alertas.values())


def limpar():
    with _lock:
        _eventos.clear()
        _recorrencia.clear()
        _alertas.clear()


class DiagnosticsHandler(logging.Handler):
    """Observa o logger estruturado e alimenta o diagnostico em memoria."""

    def emit(self, record):
        payload = getattr(record, 'payload', None)
        if isinstance(payload, dict):
            registrar(payload)


def attach_handler(logger_name='certidoes'):
    logger = logging.getLogger(logger_name)
    if not any(isinstance(h, DiagnosticsHandler) for h in logger.handlers):
        logger.addHandler(DiagnosticsHandler())
