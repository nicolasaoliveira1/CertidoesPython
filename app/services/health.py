import os
import time


def _timed_check(check_fn):
    start = time.time()
    try:
        ok, detail = check_fn()
    except Exception as exc:
        ok, detail = False, str(exc)
    latency_ms = int((time.time() - start) * 1000)
    return {'ok': ok, 'detail': detail, 'latency_ms': latency_ms}


def _check_db():
    from app import db

    db.session.execute(db.text('SELECT 1'))
    return True, 'ok'


def _check_network_path():
    from app import file_manager

    path = file_manager.CAMINHO_REDE
    exists = os.path.exists(path)
    return exists, path


def _check_chrome_profile(config):
    profile_dir = config.get('CHROME_PROFILE_DIR')
    if not profile_dir:
        return False, 'CHROME_PROFILE_DIR nao configurado'
    exists = os.path.isdir(profile_dir)
    return exists, profile_dir


def _check_solver_config(config):
    key = (config.get('CAPTCHA_2_API_KEY') or '').strip()
    return bool(key), 'ok' if key else 'CAPTCHA_2_API_KEY ausente'


def run_health_checks(config):
    return {
        'db': _timed_check(_check_db),
        'network_path': _timed_check(_check_network_path),
        'chrome_profile': _timed_check(lambda: _check_chrome_profile(config)),
        'solver': _timed_check(lambda: _check_solver_config(config)),
    }
