from __future__ import annotations

from pathlib import Path

import pytest

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_worker.scheduler import WorkerScheduler

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "core"
    / "tests"
    / "fixtures"
    / "docker"
)


def _config() -> AppConfig:
    return AppConfig(
        default_poll_interval_sec=30,
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.DARWIN,
            )
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )


def _factory(stdout: str) -> FakeSshExecutor:
    return FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )


def _scheduler(
    store: WorkloadStore,
    *,
    clock: list[float],
    sleeper: list[float],
    audit_interval_sec: float = 300.0,
) -> WorkerScheduler:
    def now() -> float:
        return clock[0]

    def sleep(seconds: float) -> None:
        sleeper.append(seconds)
        clock[0] += seconds

    ps_out = (FIXTURES / "ps_standalone.jsonl").read_text()
    executor = _factory(ps_out)

    return WorkerScheduler(
        config=_config(),
        store=store,
        executor_factory=lambda _host: executor,
        audit_interval_sec=audit_interval_sec,
        clock=now,
        sleeper=sleep,
    )


# AC-11.1
def test_ac_11_1_first_tick_runs_audit_and_poll(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper)

    result = scheduler.tick()

    assert result.ran_audit is True
    assert result.poll_updated >= 0
    assert store.count_workloads() >= 1
    store.close()


# AC-11.2
def test_ac_11_2_second_tick_within_audit_interval_skips_audit(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper, audit_interval_sec=300.0)

    first = scheduler.tick()
    second = scheduler.tick()

    assert first.ran_audit is True
    assert second.ran_audit is False
    store.close()


# AC-11.3
def test_ac_11_3_tick_after_audit_interval_runs_audit_again(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper, audit_interval_sec=60.0)

    scheduler.tick()
    clock[0] = 61.0
    third = scheduler.tick()

    assert third.ran_audit is True
    store.close()


# AC-11.4
def test_ac_11_4_run_forever_respects_max_ticks(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper)

    ticks = scheduler.run_forever(max_ticks=2)

    assert ticks == 2
    assert len(sleeper) == 1
    assert sleeper[0] == 30.0
    store.close()


def test_poll_interval_override(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper)
    scheduler.poll_interval_sec = 15

    scheduler.run_forever(max_ticks=2)

    assert sleeper == [15.0]
    store.close()


def test_run_forever_without_max_ticks_sleeps_between_polls(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []

    def stop_after_one_sleep(seconds: float) -> None:
        sleeper.append(seconds)
        msg = "stop"
        raise RuntimeError(msg)

    ps_out = (FIXTURES / "ps_standalone.jsonl").read_text()
    executor = _factory(ps_out)
    scheduler = WorkerScheduler(
        config=_config(),
        store=store,
        executor_factory=lambda _host: executor,
        clock=lambda: clock[0],
        sleeper=stop_after_one_sleep,
    )

    with pytest.raises(RuntimeError, match="stop"):
        scheduler.run_forever(max_ticks=None)

    assert sleeper == [30.0]
    store.close()


def test_run_forever_zero_ticks(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    clock = [0.0]
    sleeper: list[float] = []
    scheduler = _scheduler(store, clock=clock, sleeper=sleeper)

    assert scheduler.run_forever(max_ticks=0) == 0
    assert sleeper == []
    store.close()
