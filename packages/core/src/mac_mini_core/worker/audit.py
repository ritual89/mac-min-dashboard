from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from mac_mini_core.config import AppConfig
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.store import WorkloadStore

if TYPE_CHECKING:
    from mac_mini_core.config import HostConfig
    from mac_mini_core.ssh.executor import SshExecutor


ExecutorFactory = Callable[["HostConfig"], "SshExecutor"]


class AuditPass:
    def __init__(self, scanner: DockerScanner | None = None) -> None:
        self._scanner = scanner or DockerScanner()

    def run(
        self,
        config: AppConfig,
        store: WorkloadStore,
        executor_factory: ExecutorFactory,
    ) -> int:
        total = 0
        promote = config.promote
        for host in config.hosts:
            store.ensure_host(host)
            executor = executor_factory(host)
            snapshots = self._scanner.discover(host, executor)
            for snapshot in snapshots:
                store.upsert_snapshot(
                    snapshot,
                    project_roots=promote.project_roots,
                    allowlist=promote.allowlist,
                    port_denylist=promote.port_denylist,
                )
                total += 1
        return total
