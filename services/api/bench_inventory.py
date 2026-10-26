"""Measure uncached DB reads vs warm-cache reads on one local dataset."""

from __future__ import annotations

import json
import statistics
import time
from collections.abc import Sequence

from app.services.demo_inventory import (
    inventory_cache,
    list_inventory,
    list_inventory_alerts,
)

REPETITIONS = 200


def measure(callable_):
    """Collect uncached and cached latency for exactly the same call."""
    uncached = []
    cached = []
    for _ in range(REPETITIONS):
        inventory_cache.invalidate()
        started = time.perf_counter_ns()
        callable_()
        uncached.append((time.perf_counter_ns() - started) / 1_000_000)

    inventory_cache.invalidate()
    callable_()  # prime cache with the exact same query/dataset
    for _ in range(REPETITIONS):
        started = time.perf_counter_ns()
        callable_()
        cached.append((time.perf_counter_ns() - started) / 1_000_000)
    return {"uncached_db_read_ms": percentiles(uncached), "warm_cache_ms": percentiles(cached)}


def percentiles(samples: Sequence[float]) -> dict[str, float]:
    ordered = sorted(samples)
    return {
        "min_ms": round(min(ordered), 3),
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 3),
        "max_ms": round(max(ordered), 3),
    }


def main() -> None:
    measurements = {
        "GET /inventory/items": measure(list_inventory),
        "GET /inventory/alerts": measure(list_inventory_alerts),
    }

    print(json.dumps({
        "dataset": "fixed synthetic seed from seed_inventory.py",
        "repetitions_per_endpoint_and_phase": REPETITIONS,
        "methodology_note": "Service-call time, same process and dataset. Uncached phase clears only this process's TTL cache before each query; warm phase primes once then measures hits. Excludes HTTP transport/serialization.",
        "measurements": measurements,
    }, indent=2))


if __name__ == "__main__":
    main()
