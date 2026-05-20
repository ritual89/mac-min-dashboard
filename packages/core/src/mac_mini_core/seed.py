from __future__ import annotations

import os
from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig, load_config
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass, ExecutorFactory

DEFAULT_FIXTURE_BY_HOST: dict[str, str] = {
    "mac-mini": "ps_standalone.jsonl",
    "vultr-1": "ps_compose.jsonl",
}


def default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "docker"


def demo_config() -> AppConfig:
    return AppConfig(
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini Hub",
                tailscale_host="mac-mini",
                ssh_user="demo",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.DARWIN,
            )
        ],
        promote=PromoteRulesConfig(allowlist=["nginx"], port_denylist=[]),
    )


def build_fixture_executor_factory(
    hosts: list[HostConfig],
    fixtures_dir: Path,
    fixture_by_host: dict[str, str] | None = None,
) -> ExecutorFactory:
    mapping = fixture_by_host or DEFAULT_FIXTURE_BY_HOST
    executors: dict[str, FakeSshExecutor] = {}
    for host in hosts:
        fixture_name = mapping.get(host.id, "ps_standalone.jsonl")
        stdout = (fixtures_dir / fixture_name).read_text()
        executors[host.id] = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(
                    stdout=stdout,
                    stderr="",
                    exit_code=0,
                ),
            }
        )

    def factory(host: HostConfig) -> FakeSshExecutor:
        return executors[host.id]

    return factory


def seed_database(
    store: WorkloadStore,
    config: AppConfig,
    fixtures_dir: Path | None = None,
    *,
    fixture_by_host: dict[str, str] | None = None,
) -> int:
    directory = fixtures_dir or default_fixtures_dir()
    factory = build_fixture_executor_factory(config.hosts, directory, fixture_by_host)
    return AuditPass().run(config, store, factory)


def seed_database_file(
    db_path: str | Path,
    config: AppConfig,
    fixtures_dir: Path | None = None,
    *,
    fixture_by_host: dict[str, str] | None = None,
) -> int:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    store = WorkloadStore.open(str(path))
    try:
        return seed_database(
            store,
            config,
            fixtures_dir,
            fixture_by_host=fixture_by_host,
        )
    finally:
        store.close()


def _load_seed_config() -> AppConfig:
    config_path = os.environ.get("DASHBOARD_CONFIG_PATH")
    if config_path:
        return load_config(Path(config_path))
    return demo_config()


def main() -> None:
    db_path = os.environ.get("DASHBOARD_DB_PATH", "./data/fleet.db")
    count = seed_database_file(db_path, _load_seed_config())
    print(f"Seeded {count} workload(s) into {db_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
