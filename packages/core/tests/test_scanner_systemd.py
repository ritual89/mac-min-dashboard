from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import HostConfig
from mac_mini_core.models import HostOS, WorkloadKind
from mac_mini_core.scanners.systemd import SystemdScanner, parse_systemctl_output
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult

FIXTURES = Path(__file__).parent / "fixtures" / "systemd"


def _host() -> HostConfig:
    return HostConfig(
        id="linux-box",
        display_name="Linux Box",
        tailscale_host="linux-box",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id",
        os=HostOS.LINUX,
    )


def test_parse_running_units() -> None:
    stdout = (FIXTURES / "list_units.txt").read_text()
    snaps = parse_systemctl_output("linux-box", stdout)
    assert len(snaps) == 3
    assert snaps[0].workload_id == "systemd:linux-box:nginx.service"
    assert snaps[0].kind == WorkloadKind.SYSTEMD
    assert snaps[0].status == "active/running"
    assert snaps[1].name == "docker.service"


def test_parse_empty_output() -> None:
    stdout = (FIXTURES / "list_units_empty.txt").read_text()
    snaps = parse_systemctl_output("linux-box", stdout)
    assert snaps == []


def test_parse_skips_short_lines() -> None:
    stdout = "UNIT LOAD\nnginx.service loaded active running A web server\nshort\n"
    snaps = parse_systemctl_output("linux-box", stdout)
    assert len(snaps) == 1


def test_parse_skips_non_loaded() -> None:
    stdout = "nginx.service not-found inactive dead A web server\n"
    snaps = parse_systemctl_output("linux-box", stdout)
    assert len(snaps) == 0


def test_scanner_discover() -> None:
    stdout = (FIXTURES / "list_units.txt").read_text()
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.SYSTEMCTL_LIST_UNITS, ()): SshResult(
                stdout=stdout, stderr="", exit_code=0
            ),
        }
    )
    scanner = SystemdScanner()
    snaps = scanner.discover(_host(), executor)
    assert len(snaps) == 3
    assert executor.history[0].template is CommandTemplate.SYSTEMCTL_LIST_UNITS
