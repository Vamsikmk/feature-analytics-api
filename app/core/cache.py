import hashlib
import json
import time
from typing import Any

from app.core.config import settings

_store: dict[str, tuple[Any, float]] = {}


def _make_key(params: dict) -> str:
    serialized = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def get(params: dict) -> Any | None:
    key = _make_key(params)
    entry = _store.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        del _store[key]
        return None
    return value


def set(params: dict, value: Any) -> None:
    key = _make_key(params)
    _store[key] = (value, time.monotonic() + settings.CACHE_TTL_SECONDS)


def invalidate_all() -> None:
    _store.clear()
