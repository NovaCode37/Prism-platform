import os
import time
from typing import Dict, Optional

import requests

RETRY_STATUS_CODES = (502, 503, 504)
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5


def get_proxies() -> Optional[Dict[str, str]]:
    proxy = os.getenv("MODULE_PROXY", "").strip()
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def get_with_retry(url: str, **kwargs) -> requests.Response:
    """GET `url`, retrying only transient failures, up to RETRY_ATTEMPTS times.

    `502`, `503`, `504` and timeouts are retried with exponential backoff. Any
    other status is returned immediately: a `200` and a `404` are answers, not
    failures. When the retries are used up, the last response is returned as-is
    so the caller still reports the failure, and a timeout that outlives them is
    raised so the caller keeps its own timeout handling.

    `timeout` in `kwargs` stays the per-attempt timeout, so a call that retries
    never waits longer for a single attempt than it did before.
    """
    last_response = None
    last_error = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, **kwargs)
        except requests.Timeout as error:
            last_response, last_error = None, error
        else:
            if response.status_code not in RETRY_STATUS_CODES:
                return response
            last_response, last_error = response, None

        if attempt < RETRY_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    if last_response is not None:
        return last_response

    raise last_error
