from __future__ import annotations

from pathlib import Path

import pytest

from mac_mini_core.config import HostConfig
from mac_mini_core.models import HostOS, WorkloadKind
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult

FIXTURES = Path(__file__).parent / "fixtures" / "docker"


def _host() -> HostConfig:
    return HostConfig(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id_ed25519",
        os=HostOS.DARWIN,
    )


def _executor_with_fixture(filename: str) -> FakeSshExecutor:
    stdout = (FIXTURES / filename).read_text()
    return FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )


# AC-3.1
def test_ac_3_1_standalone_container_discovered() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_standalone.jsonl"))
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.workload_id == "docker:mac-mini:nginx"
    assert snap.kind is WorkloadKind.DOCKER
    assert snap.name == "nginx"
    assert snap.host_id == "mac-mini"
    assert snap.status == "running"


# AC-3.2
def test_ac_3_2_compose_container_discovered() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_compose.jsonl"))
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.workload_id == "compose:mac-mini:myapp:api"
    assert snap.kind is WorkloadKind.COMPOSE
    assert snap.compose_project == "myapp"
    assert snap.compose_service == "api"


# AC-3.3
def test_ac_3_3_discover_is_idempotent() -> None:
    scanner = DockerScanner()
    executor = _executor_with_fixture("ps_standalone.jsonl")
    first = scanner.discover(_host(), executor)
    second = scanner.discover(_host(), executor)
    assert first == second


# AC-3.4
def test_ac_3_4_empty_output_returns_empty_list() -> None:
    scanner = DockerScanner()
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="", stderr="", exit_code=0),
        }
    )
    assert scanner.discover(_host(), executor) == []


# AC-3.5
def test_ac_3_5_uses_docker_ps_command_only() -> None:
    scanner = DockerScanner()
    executor = _executor_with_fixture("ps_standalone.jsonl")
    scanner.discover(_host(), executor)
    assert len(executor.history) == 1
    assert executor.history[0].template is CommandTemplate.DOCKER_PS


# AC-3.6
def test_ac_3_6_parses_healthy_from_status() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_standalone.jsonl"))
    assert snapshots[0].docker_health == "healthy"


# AC-3.7
def test_ac_3_7_exited_state_mapped() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_exited.jsonl"))
    assert snapshots[0].status == "exited"


# AC-3.8
def test_ac_3_8_duplicate_workload_id_deduped() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_duplicate.jsonl"))
    assert len(snapshots) == 1
    assert snapshots[0].status == "exited"


def test_ac_3_6_unhealthy_status_parsed() -> None:
    stdout = (
        '{"ID":"x","Names":"/sick","Image":"s:1","State":"running",'
        '"Status":"Up 1 second (unhealthy)","Labels":""}\n'
    )
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )
    snapshots = DockerScanner().discover(_host(), executor)
    assert snapshots[0].docker_health == "unhealthy"


def test_ec_3_1_malformed_lines_skipped() -> None:
    scanner = DockerScanner()
    snapshots = scanner.discover(_host(), _executor_with_fixture("ps_malformed.jsonl"))
    assert len(snapshots) == 2
    names = {s.name for s in snapshots}
    assert names == {"good", "good2"}


def test_ec_3_2_compose_project_without_service_is_docker_kind() -> None:
    stdout = (
        '{"ID":"x","Names":"/solo","Image":"s:1","State":"running",'
        '"Status":"Up","Labels":"com.docker.compose.project=onlyproject"}\n'
    )
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )
    snapshots = DockerScanner().discover(_host(), executor)
    assert snapshots[0].kind is WorkloadKind.DOCKER
    assert snapshots[0].workload_id == "docker:mac-mini:solo"


def test_parse_labels_ignores_parts_without_equals() -> None:
    from mac_mini_core.scanners.docker import parse_docker_ps_output

    stdout = (
        '{"ID":"x","Names":"/svc","Image":"s:1","State":"running",'
        '"Status":"Up","Labels":"badlabel,com.docker.compose.project=p,com.docker.compose.service=s"}\n'
    )
    snapshots = parse_docker_ps_output("host-1", stdout)
    assert snapshots[0].compose_project == "p"


def test_parse_skips_row_without_name() -> None:
    from mac_mini_core.scanners.docker import parse_docker_ps_output

    stdout = '{"ID":"x","Names":"","Image":"i","State":"running","Status":"Up","Labels":""}\n'
    assert parse_docker_ps_output("host-1", stdout) == []


def test_parse_skips_non_dict_json() -> None:
    from mac_mini_core.scanners.docker import parse_docker_ps_output

    stdout = (
        '[1, 2]\n'
        '{"ID":"x","Names":"/ok","Image":"i","State":"running","Status":"Up","Labels":""}\n'
    )
    snapshots = parse_docker_ps_output("host-1", stdout)
    assert len(snapshots) == 1
    assert snapshots[0].name == "ok"


def test_parse_skips_blank_lines() -> None:
    from mac_mini_core.scanners.docker import parse_docker_ps_output

    stdout = (
        "\n\n"
        '{"ID":"x","Names":"/ok","Image":"","State":"running","Status":"Up","Labels":""}\n'
    )
    snapshots = parse_docker_ps_output("host-1", stdout)
    assert len(snapshots) == 1
    assert snapshots[0].image is None
    assert snapshots[0].docker_health is None


def test_ssh_nonzero_exit_raises() -> None:
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="", stderr="error", exit_code=1),
        }
    )
    with pytest.raises(RuntimeError, match="docker ps failed"):
        DockerScanner().discover(_host(), executor)
