"""Límite de intentos en memoria (F1).

Suficiente para un proceso; en F2/F4a se sustituye por Redis para que valga
entre workers y réplicas. No se usa para datos de negocio, solo para frenar
fuerza bruta.
"""

import time
from collections import defaultdict, deque
from threading import Lock

_LOCK = Lock()
_HITS: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, *, limit: int = 5, window_s: int = 60) -> bool:
    now = time.monotonic()
    with _LOCK:
        hits = _HITS[key]
        while hits and now - hits[0] > window_s:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def reset_rate_limit(key: str) -> None:
    with _LOCK:
        _HITS.pop(key, None)
