from __future__ import annotations

import json

from mac_mini_core.alert import should_alert
from mac_mini_core.config import AppConfig
from mac_mini_core.models import WorkloadKind
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.severity import SeverityInput, evaluate_severity
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor
from mac_mini_core.store import WorkloadStore
from mac_mini_core.telegram import TelegramSender
from mac_mini_core.worker.audit import ExecutorFactory


def _fetch_log_tail(
    executor: SshExecutor, name: str, n: int = 50
) -> str | None:
    try:
        result = executor.execute(CommandTemplate.DOCKER_LOGS, name=name, n=n)
        if result.exit_code == 0:
            return result.stdout
    except Exception:
        pass
    return None


def _fetch_restart_count(executor: SshExecutor, name: str) -> int:
    try:
        result = executor.execute(CommandTemplate.DOCKER_INSPECT, name=name)
        if result.exit_code == 0:
            data = json.loads(result.stdout)
            if isinstance(data, list) and data:
                state = data[0].get("RestartCount", 0)
                return int(state)
    except Exception:
        pass
    return 0


class PollPass:
    def __init__(
        self,
        scanner: DockerScanner | None = None,
        *,
        notifier: TelegramSender | None = None,
        dashboard_url: str | None = None,
    ) -> None:
        self._scanner = scanner or DockerScanner()
        self._notifier = notifier
        self._dashboard_url = dashboard_url

    def run(
        self,
        config: AppConfig,
        store: WorkloadStore,
        executor_factory: ExecutorFactory,
    ) -> int:
        settings = store.get_settings() if self._notifier else {}
        updated = 0
        for host in config.hosts:
            executor = executor_factory(host)
            snapshots = {
                s.workload_id: s
                for s in self._scanner.discover(host, executor)
            }
            for workload_id in store.list_monitored_ids(host.id):
                old_severity = store.get_state(workload_id)[1]

                row = store.get_workload(workload_id)
                log_tail: str | None = None
                restart_count = 0
                if row and row.kind in (
                    WorkloadKind.DOCKER.value,
                    WorkloadKind.COMPOSE.value,
                ):
                    log_tail = _fetch_log_tail(executor, row.name)
                    restart_count = _fetch_restart_count(executor, row.name)

                snapshot = snapshots.get(workload_id)
                store.apply_poll_update(
                    workload_id,
                    snapshot,
                    restart_loop_threshold=config.restart_loop_threshold_1h,
                    log_tail=log_tail,
                    restart_count=restart_count,
                )
                new_severity = store.get_state(workload_id)[1]

                if self._notifier and old_severity != new_severity:
                    last_alert = store.last_alert_time(workload_id)
                    decision = should_alert(
                        old_severity,
                        new_severity,
                        notify_orange=settings.get("notify_orange", True),
                        notify_red=settings.get("notify_red", True),
                        last_alert_time=last_alert,
                    )
                    if decision.should_send:
                        reason = store.get_state(workload_id)[2]
                        name = row.name if row else workload_id
                        self._notifier.send_alert(
                            host.id,
                            name,
                            new_severity,
                            reason,
                            self._dashboard_url,
                        )
                        store.record_alert(workload_id, new_severity)

                updated += 1
        return updated
