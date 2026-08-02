import time

from services.cache import TTLCache


def test_returns_cached_value_within_ttl():
    cache: TTLCache[int] = TTLCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return 42

    assert cache.get_or_fetch(fetch) == 42
    assert cache.get_or_fetch(fetch) == 42
    assert len(calls) == 1


def test_refetches_after_ttl_expires():
    cache: TTLCache[int] = TTLCache(ttl_seconds=0)
    calls = []

    def fetch():
        calls.append(1)
        return len(calls)

    first = cache.get_or_fetch(fetch)
    time.sleep(0.01)
    second = cache.get_or_fetch(fetch)

    assert first == 1
    assert second == 2


def test_invalidate_forces_refetch():
    cache: TTLCache[int] = TTLCache(ttl_seconds=60)
    calls = []

    def fetch():
        calls.append(1)
        return len(calls)

    cache.get_or_fetch(fetch)
    cache.invalidate()
    cache.get_or_fetch(fetch)

    assert len(calls) == 2
