import json
import logging
from datetime import datetime, timezone

from app.services.correlation import CorrelationContext


LOGGER_NAME = 'certidoes'


def configure_logging(level='INFO'):
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(event, level='INFO', **fields):
    logger = logging.getLogger(LOGGER_NAME)
    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': event,
        'level': level,
        'request_id': CorrelationContext.get_request_id(),
        'execution_id': CorrelationContext.get_execution_id(),
    }
    payload.update(fields)

    text = json.dumps(payload, ensure_ascii=False, default=str)
    lvl = str(level or 'INFO').upper()
    if lvl == 'ERROR':
        logger.error(text)
    elif lvl == 'WARNING':
        logger.warning(text)
    else:
        logger.info(text)
