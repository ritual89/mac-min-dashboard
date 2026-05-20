from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import Request

from mac_mini_core.config import AppConfig
from mac_mini_core.store import WorkloadStore

if TYPE_CHECKING:
    from mac_mini_core.config import HostConfig
    from mac_mini_core.ssh.executor import SshExecutor

ExecutorFactory = Callable[["HostConfig"], "SshExecutor"]


def get_store(request: Request) -> WorkloadStore:
    store = request.app.state.store
    if store is None:
        msg = "store not configured"
        raise RuntimeError(msg)
    return store


def get_config(request: Request) -> AppConfig | None:
    return request.app.state.config


def get_executor_factory(request: Request) -> ExecutorFactory | None:
    return request.app.state.executor_factory
