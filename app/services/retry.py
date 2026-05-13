import random
import time


def retry_call(fn, *, max_attempts=3, base_delay=0.5, jitter=0.2, retry_if=None, on_retry=None):
    try:
        max_attempts = int(max_attempts)
    except (TypeError, ValueError):
        max_attempts = 1

    try:
        base_delay = float(base_delay)
    except (TypeError, ValueError):
        base_delay = 0.0

    try:
        jitter = float(jitter)
    except (TypeError, ValueError):
        jitter = 0.0

    max_attempts = max(1, max_attempts)
    base_delay = max(0.0, base_delay)
    jitter = max(0.0, jitter)

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            can_retry = attempt < max_attempts and (retry_if(exc) if retry_if else True)
            if not can_retry:
                raise

            delay = base_delay * (2 ** (attempt - 1))
            delay = delay + random.uniform(0, jitter)
            if on_retry:
                on_retry(attempt, delay, exc)
            time.sleep(delay)

    if last_error:
        raise last_error
