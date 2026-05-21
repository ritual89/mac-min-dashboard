from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS, WorkloadKind, WorkloadSnapshot
from mac_mini_core.store import WorkloadStore


def _store(tmp_path: Path) -> WorkloadStore:
    return WorkloadStore.open(str(tmp_path / "fleet.db"))


def _seed_docker(store: WorkloadStore) -> None:
    """Insert a docker workload that auto-promotes (monitored=True)."""
    snap = WorkloadSnapshot(
        workload_id="docker:mac-mini:nginx",
        host_id="mac-mini",
        kind=WorkloadKind.DOCKER,
        name="nginx",
        status="running",
    )
    store.upsert_snapshot(snap)


def _seed_launchd(store: WorkloadStore) -> None:
    """Insert a launchd workload that does NOT auto-promote."""
    snap = WorkloadSnapshot(
        workload_id="launchd:mac-mini:com.custom.svc",
        host_id="mac-mini",
        kind=WorkloadKind.LAUNCHD,
        name="com.custom.svc",
        status="running",
    )
    store.upsert_snapshot(
        snap,
        project_roots=[],
        allowlist=[],
        port_denylist=[],
    )


_DEFAULT_RULES = PromoteRulesConfig(
    project_roots=["~/dev"],
    allowlist=[],
    port_denylist=[],
)


# AC-14.1
def test_ac_14_1_pin_promotes_discovered_workload(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_launchd(store)
    assert not store.get_monitored("launchd:mac-mini:com.custom.svc")

    store.pin_workload("launchd:mac-mini:com.custom.svc")

    row = store.get_workload("launchd:mac-mini:com.custom.svc")
    assert row is not None
    assert row.pinned is True
    assert row.monitored is True


# AC-14.2
def test_ac_14_2_unpin_docker_stays_monitored(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_docker(store)
    store.pin_workload("docker:mac-mini:nginx")

    store.unpin_workload("docker:mac-mini:nginx", _DEFAULT_RULES)

    row = store.get_workload("docker:mac-mini:nginx")
    assert row is not None
    assert row.pinned is False
    assert row.monitored is True


# AC-14.3
def test_ac_14_3_unpin_non_promotable_loses_monitored(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_launchd(store)
    store.pin_workload("launchd:mac-mini:com.custom.svc")
    assert store.get_monitored("launchd:mac-mini:com.custom.svc")

    store.unpin_workload("launchd:mac-mini:com.custom.svc", _DEFAULT_RULES)

    row = store.get_workload("launchd:mac-mini:com.custom.svc")
    assert row is not None
    assert row.pinned is False
    assert row.monitored is False


# AC-14.4
def test_ac_14_4_pin_unknown_returns_false(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.pin_workload("docker:missing:svc") is False


# AC-14.5
def test_ac_14_5_unpin_unknown_returns_false(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.unpin_workload("docker:missing:svc", _DEFAULT_RULES) is False


# AC-14.6
def test_ac_14_6_pin_already_pinned_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_docker(store)
    store.pin_workload("docker:mac-mini:nginx")
    assert store.pin_workload("docker:mac-mini:nginx") is True
    row = store.get_workload("docker:mac-mini:nginx")
    assert row is not None
    assert row.pinned is True
