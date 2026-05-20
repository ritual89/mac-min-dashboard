from __future__ import annotations

from collections.abc import Iterator

import pytest

from mac_mini_core.store import WorkloadStore

_opened: list[WorkloadStore] = []
_original_open = WorkloadStore.open.__func__  # type: ignore[attr-defined]


@classmethod
def _tracking_open(cls, path: str) -> WorkloadStore:
    store = _original_open(cls, path)
    _opened.append(store)
    return store


@pytest.fixture(autouse=True)
def _close_workload_stores_after_test() -> Iterator[None]:
    WorkloadStore.open = _tracking_open  # type: ignore[method-assign]
    yield
    while _opened:
        _opened.pop().close()
    WorkloadStore.open = classmethod(_original_open)  # type: ignore[method-assign]
