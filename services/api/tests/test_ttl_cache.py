from app.services.ttl_cache import TTLCache


def test_cache_hit_and_miss_only_computes_once():
    cache = TTLCache(ttl_seconds=30)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return {"value": calls}

    assert cache.get_or_set(("items", None), load) == {"value": 1}
    assert cache.get_or_set(("items", None), load) == {"value": 1}
    assert calls == 1


def test_cache_expires_at_ttl_boundary():
    now = 10.0
    cache = TTLCache(ttl_seconds=30, clock=lambda: now)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return calls

    assert cache.get_or_set("key", load) == 1
    now += 29.999
    assert cache.get_or_set("key", load) == 1
    now += 0.001
    assert cache.get_or_set("key", load) == 2
    assert calls == 2


def test_invalidation_forces_a_miss():
    cache = TTLCache(ttl_seconds=30)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return calls

    assert cache.get_or_set("alerts", load) == 1
    cache.invalidate("alerts")
    assert cache.get_or_set("alerts", load) == 2


def test_cache_keys_isolate_filters_and_read_kinds():
    cache = TTLCache(ttl_seconds=30)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return calls

    assert cache.get_or_set(("items", "los-angeles"), load) == 1
    assert cache.get_or_set(("items", "zaragoza"), load) == 2
    assert cache.get_or_set(("items", "los-angeles"), load) == 1
    assert cache.get_or_set(("alerts", "los-angeles"), load) == 3
    assert calls == 3


def test_cache_returns_deep_copies():
    cache = TTLCache(ttl_seconds=30)
    result = cache.get_or_set("list", lambda: [{"count": 1}])
    result[0]["count"] = 99
    assert cache.get_or_set("list", lambda: []) == [{"count": 1}]
