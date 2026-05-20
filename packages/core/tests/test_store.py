from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.store import WorkloadStore


def test_get_state_unknown_when_missing(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        status, severity, reason = store.get_state("docker:missing:svc")
        assert status == "unknown"
        assert severity == "green"
        assert reason is None
    finally:
        store.close()


def test_list_hosts_empty_database(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        assert store.list_hosts() == []
    finally:
        store.close()


def test_get_workload_returns_none(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        assert store.get_workload("nope") is None
    finally:
        store.close()


def test_get_host_returns_none_when_missing(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        assert store.get_host("missing") is None
    finally:
        store.close()


def test_ensure_host_updates_row(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        host = HostConfig(
            id="h1",
            display_name="Host One",
            tailscale_host="h1.ts",
            ssh_user="u",
            ssh_key_path="~/.ssh/id",
            os=HostOS.LINUX,
        )
        store.ensure_host(host)
        hosts = store.list_hosts()
        assert len(hosts) == 1
        assert hosts[0].display_name == "Host One"
    finally:
        store.close()
