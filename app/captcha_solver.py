import json

from twocaptcha import TwoCaptcha


class AltchaSolverError(Exception):
    pass


class AltchaSolverConfigError(AltchaSolverError):
    pass


class AltchaSolverRuntimeError(AltchaSolverError):
    pass


def _parse_int(value, default_value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


def _extract_code(result):
    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        for key in ('token', 'code', 'text'):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        solution = result.get('solution')
        if isinstance(solution, dict):
            for key in ('token', 'code', 'text'):
                value = solution.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if isinstance(solution, str) and solution.strip():
            return solution.strip()

    return ''


def solve_altcha(config, page_url, challenge_json=None, challenge_url=None):
    api_key = (config.get('CAPTCHA_2_API_KEY') or '').strip()
    if not api_key:
        raise AltchaSolverConfigError('CAPTCHA_2_API_KEY não configurada.')

    if not challenge_json and not challenge_url:
        raise AltchaSolverConfigError('Challenge ALTCHA não disponível para envio ao 2captcha.')

    solver = TwoCaptcha(
        apiKey=api_key,
        server=(config.get('CAPTCHA_2_SERVER') or '2captcha.com').strip() or '2captcha.com',
        defaultTimeout=_parse_int(config.get('CAPTCHA_2_DEFAULT_TIMEOUT'), 180),
        pollingInterval=_parse_int(config.get('CAPTCHA_2_POLLING_INTERVAL'), 10),
    )

    payload = {
        'pageurl': page_url,
    }

    if challenge_json:
        if isinstance(challenge_json, (dict, list)):
            payload['challenge_json'] = json.dumps(challenge_json, separators=(',', ':'))
        else:
            payload['challenge_json'] = str(challenge_json)
    else:
        payload['challenge_url'] = str(challenge_url)

    try:
        result = solver.altcha(**payload)
    except Exception as exc:
        raise AltchaSolverRuntimeError(f'Falha ao resolver ALTCHA no 2captcha: {exc}') from exc

    code = _extract_code(result)
    if not code:
        raise AltchaSolverRuntimeError(f'Resposta ALTCHA sem token reutilizável: {result}')

    return {
        'code': code,
        'raw': result,
    }
