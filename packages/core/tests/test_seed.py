from __future__ import annotations

from pathlib import Path

import pytest

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.seed import (
    build_fixture_executor_factory,
    default_fixtures_dir,
    demo_config,
    seed_database,
    seed_database_file,
)
from mac_mini_core.store import WorkloadStore

FIXTURES = Path(__file__).parent / "fixtures" / "docker"


def _config(*host_ids: str) -> AppConfig:
    return AppConfig(
        hosts=[
            HostConfig(
                id=host_id,
                display_name=host_id,
                tailscale_host=host_id,
                ssh_user="greg",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.LINUX,
            )
            for host_id in host_ids
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )


# AC-12.1
def test_ac_12_1_seed_creates_monitored_workload(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        count = seed_database(
            store,
            _config("mac-mini"),
            FIXTURES,
            fixture_by_host={"mac-mini": "ps_standalone.jsonl"},
        )
        assert count >= 1
        rows = store.list_workloads(monitored=True)
        assert any(row.name == "nginx" for row in rows)
    finally:
        store.close()


# AC-12.2
def test_ac_12_2_seed_is_idempotent(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        config = _config("mac-mini")
        mapping = {"mac-mini": "ps_standalone.jsonl"}
        seed_database(store, config, FIXTURES, fixture_by_host=mapping)
        first = store.count_workloads()
        seed_database(store, config, FIXTURES, fixture_by_host=mapping)
        assert store.count_workloads() == first
    finally:
        store.close()


# AC-12.3
def test_ac_12_3_per_host_fixture_map(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = _config("mac-mini", "vultr-1")
    mapping = {
        "mac-mini": "ps_standalone.jsonl",
        "vultr-1": "ps_compose.jsonl",
    }
    factory = build_fixture_executor_factory(config.hosts, FIXTURES, mapping)

    mini_exec = factory(config.hosts[0])
    vultr_exec = factory(config.hosts[1])
    assert mini_exec is not vultr_exec

    seed_database(store, config, FIXTURES, fixture_by_host=mapping)
    names = {row.name for row in store.list_workloads()}
    assert "nginx" in names
    store.close()


# AC-12.4
def test_ac_12_4_seed_database_file_creates_db(tmp_path: Path) -> None:
    db_path = tmp_path / "fleet.db"
    count = seed_database_file(db_path, _config("mac-mini"), FIXTURES)
    assert count >= 1
    assert db_path.is_file()
    store = WorkloadStore.open(str(db_path))
    try:
        assert store.count_workloads() >= 1
    finally:
        store.close()


def test_default_fixtures_dir_exists() -> None:
    assert default_fixtures_dir().is_dir()
    assert (default_fixtures_dir() / "ps_standalone.jsonl").is_file()


def test_demo_config_has_one_host() -> None:
    config = demo_config()
    assert len(config.hosts) == 1
    assert config.hosts[0].id == "mac-mini"


def test_seed_database_file_creates_parent_dir(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "fleet.db"
    count = seed_database_file(db_path, _config("mac-mini"), FIXTURES)
    assert count >= 1
    assert db_path.is_file()


def test_load_seed_config_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mac_mini_core.seed import _load_seed_config

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "hosts:\n"
        "  - id: edge\n"
        "    display_name: Edge\n"
        "    tailscale_host: edge\n"
        "    ssh_user: greg\n"
        "    ssh_key_path: ~/.ssh/id_ed25519\n"
        "    os: linux\n"
        "promote:\n"
        "  allowlist: []\n"
        "  port_denylist: []\n",
    )
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    config = _load_seed_config()
    assert config.hosts[0].id == "edge"


def test_load_seed_config_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from mac_mini_core.seed import _load_seed_config

    monkeypatch.delenv("DASHBOARD_CONFIG_PATH", raising=False)
    config = _load_seed_config()
    assert config.hosts[0].id == "mac-mini"


def test_main_prints_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from mac_mini_core.seed import main

    db_path = tmp_path / "fleet.db"
    monkeypatch.delenv("DASHBOARD_CONFIG_PATH", raising=False)
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))
    main()
    out = capsys.readouterr().out
    assert "Seeded" in out
    assert str(db_path) in out
    assert db_path.is_file()
