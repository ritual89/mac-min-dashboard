from __future__ import annotations

from pathlib import Path

import pytest

from mac_mini_core.store import WorkloadStore

from mac_mini_worker import main as worker_main


def test_run_worker_once_uses_scheduler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: mac-mini\n"
        "    display_name: Mac Mini\n"
        "    tailscale_host: mac-mini\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: darwin\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    db_path = tmp_path / "fleet.db"

    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))

    calls: list[int] = []

    class FakeScheduler:
        def run_forever(self, *, max_ticks: int | None = None) -> int:
            calls.append(max_ticks or 0)
            return max_ticks or 1

    monkeypatch.setattr(worker_main, "build_scheduler", lambda: FakeScheduler())

    ticks = worker_main.run_worker(max_ticks=1)

    assert ticks == 1
    assert calls == [1]


def test_build_scheduler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: mac-mini\n"
        "    display_name: Mac Mini\n"
        "    tailscale_host: mac-mini\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: darwin\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))
    monkeypatch.setenv("DASHBOARD_AUDIT_INTERVAL_SEC", "120")

    scheduler = worker_main.build_scheduler()
    try:
        assert scheduler.audit_interval_sec == 120.0
        assert scheduler.config.hosts[0].id == "mac-mini"
    finally:
        scheduler.store.close()


def test_run_invokes_run_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int | None] = []

    def fake_run(*, max_ticks: int | None = None) -> int:
        called.append(max_ticks)
        return 1

    monkeypatch.setattr(worker_main, "run_worker", fake_run)
    worker_main.run()
    assert called == [None]


def test_run_worker_skips_close_without_store(monkeypatch: pytest.MonkeyPatch) -> None:
    class BareScheduler:
        def run_forever(self, *, max_ticks: int | None = None) -> int:
            return 1

    monkeypatch.setattr(worker_main, "build_scheduler", lambda: BareScheduler())
    assert worker_main.run_worker(max_ticks=1) == 1


def test_build_scheduler_with_telegram(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: mac-mini\n"
        "    display_name: Mac Mini\n"
        "    tailscale_host: mac-mini\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: darwin\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("DASHBOARD_URL", "http://dash:8081")

    scheduler = worker_main.build_scheduler()
    try:
        assert scheduler.poll_pass._notifier is not None
        assert scheduler.poll_pass._dashboard_url == "http://dash:8081"
    finally:
        scheduler.store.close()


def test_build_scheduler_without_telegram(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: mac-mini\n"
        "    display_name: Mac Mini\n"
        "    tailscale_host: mac-mini\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: darwin\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("DASHBOARD_URL", raising=False)

    scheduler = worker_main.build_scheduler()
    try:
        assert scheduler.poll_pass._notifier is None
        assert scheduler.poll_pass._dashboard_url is None
    finally:
        scheduler.store.close()


def test_run_worker_closes_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: mac-mini\n"
        "    display_name: Mac Mini\n"
        "    tailscale_host: mac-mini\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: darwin\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))

    assert worker_main.run_worker(max_ticks=0) == 0
    store = WorkloadStore.open(str(db_path))
    try:
        assert store.count_workloads() == 0
    finally:
        store.close()
