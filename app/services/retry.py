import random
import time


def retry_call(fn, *, max_attempts=3, base_delay=0.5, jitter=0.2, retry_if=None, on_retry=None):
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
