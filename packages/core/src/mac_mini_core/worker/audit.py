from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from mac_mini_core.config import AppConfig
from mac_mini_core.models import HostOS, WorkloadSnapshot
from mac_mini_core.scanners.cron import CronScanner
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.scanners.launchd import LaunchdScanner
from mac_mini_core.scanners.systemd import SystemdScanner
from mac_mini_core.store import WorkloadStore

if TYPE_CHECKING:
    from mac_mini_core.config import HostConfig
    from mac_mini_core.ssh.executor import SshExecutor


ExecutorFactory = Callable[["HostConfig"], "SshExecutor"]


class Scanner(Protocol):
    def discover(self, host: "HostConfig", executor: "SshExecutor") -> list[WorkloadSnapshot]: ...


def _default_scanners() -> dict[str, list[Scanner]]:
    docker = DockerScanner()
    return {
        "all": [docker, CronScanner()],
        "linux": [SystemdScanner()],
        "darwin": [LaunchdScanner()],
    }


class AuditPass:
    def __init__(
        self,
        scanner: DockerScanner | None = None,
        *,
        scanners: dict[str, list[Scanner]] | None = None,
    ) -> None:
        if scanners is not None:
            self._scanners = scanners
        elif scanner is not None:
            self._scanners: dict[str, list[Scanner]] = {"all": [scanner], "linux": [], "darwin": []}
        else:
            self._scanners = _default_scanners()

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
            host_scanners = list(self._scanners.get("all", []))
            host_scanners.extend(self._scanners.get(host.os.value, []))
            for scanner in host_scanners:
                snapshots = scanner.discover(host, executor)
                for snapshot in snapshots:
                    store.upsert_snapshot(
                        snapshot,
                        project_roots=promote.project_roots,
                        allowlist=promote.allowlist,
                        port_denylist=promote.port_denylist,
                    )
                    total += 1
        return total
