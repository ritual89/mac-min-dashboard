from __future__ import annotations

from mac_mini_core.config import AppConfig
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.severity import SeverityInput, evaluate_severity
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import ExecutorFactory


class PollPass:
    def __init__(self, scanner: DockerScanner | None = None) -> None:
        self._scanner = scanner or DockerScanner()

    def run(
        self,
        config: AppConfig,
        store: WorkloadStore,
        executor_factory: ExecutorFactory,
    ) -> int:
        updated = 0
        for host in config.hosts:
            executor = executor_factory(host)
            snapshots = {
                s.workload_id: s
                for s in self._scanner.discover(host, executor)
            }
            for workload_id in store.list_monitored_ids(host.id):
                snapshot = snapshots.get(workload_id)
                store.apply_poll_update(
                    workload_id,
                    snapshot,
                    restart_loop_threshold=config.restart_loop_threshold_1h,
                )
                updated += 1
        return updated
