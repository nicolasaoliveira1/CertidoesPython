"""Pacote de automação.

Reúne a configuração de sites/validades e (incrementalmente, via refatoração
C1) a lógica antes concentrada em routes.py: leitura/classificação de PDF e,
nas próximas fatias, driver, steps e emissão por tipo de certidão.

Reexporta SITES_CERTIDOES e VALIDADES_CERTIDOES para manter o import público
`from app.automation import SITES_CERTIDOES, VALIDADES_CERTIDOES`.
"""
from app.automation.sites import SITES_CERTIDOES, VALIDADES_CERTIDOES

__all__ = ['SITES_CERTIDOES', 'VALIDADES_CERTIDOES']
