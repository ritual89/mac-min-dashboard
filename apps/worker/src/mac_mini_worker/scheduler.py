from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from mac_mini_core.config import AppConfig
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass, ExecutorFactory
from mac_mini_core.worker.poll import PollPass

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class TickResult:
    ran_audit: bool
    poll_updated: int


@dataclass
class WorkerScheduler:
    config: AppConfig
    store: WorkloadStore
    executor_factory: ExecutorFactory
    audit_interval_sec: float = 300.0
    poll_interval_sec: float | None = None
    audit_pass: AuditPass = field(default_factory=AuditPass)
    poll_pass: PollPass = field(default_factory=PollPass)
    clock: Clock = field(default=time.monotonic)
    sleeper: Sleeper = field(default=time.sleep)

    def __post_init__(self) -> None:
        self._last_audit_at = self.clock() - self.audit_interval_sec

    def _poll_interval(self) -> float:
        if self.poll_interval_sec is not None:
            return self.poll_interval_sec
        return float(self.config.default_poll_interval_sec)

    def tick(self) -> TickResult:
        now = self.clock()
        ran_audit = False
        if now - self._last_audit_at >= self.audit_interval_sec:
            self.audit_pass.run(self.config, self.store, self.executor_factory)
            self._last_audit_at = now
            ran_audit = True

        poll_updated = self.poll_pass.run(
            self.config,
            self.store,
            self.executor_factory,
        )
        return TickResult(ran_audit=ran_audit, poll_updated=poll_updated)

    def run_forever(self, *, max_ticks: int | None = None) -> int:
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            self.tick()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            self.sleeper(self._poll_interval())
        return ticks
