from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import HostConfig
from mac_mini_core.models import HostOS, WorkloadKind
from mac_mini_core.scanners.launchd import LaunchdScanner, parse_launchctl_output
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult

FIXTURES = Path(__file__).parent / "fixtures" / "launchd"


def _host() -> HostConfig:
    return HostConfig(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id",
        os=HostOS.DARWIN,
    )


def test_parse_launchctl_output() -> None:
    stdout = (FIXTURES / "list.txt").read_text()
    snaps = parse_launchctl_output("mac-mini", stdout)
    assert len(snaps) == 3
    assert snaps[0].workload_id == "launchd:mac-mini:com.gregorypeacock.dashboard-api"
    assert snaps[0].kind == WorkloadKind.LAUNCHD
    assert snaps[0].status == "running"
    assert snaps[2].name == "com.custom.myapp"


def test_excludes_com_apple() -> None:
    stdout = (FIXTURES / "list.txt").read_text()
    snaps = parse_launchctl_output("mac-mini", stdout)
    names = [s.name for s in snaps]
    assert not any(n.startswith("com.apple.") for n in names)


def test_loaded_status_for_no_pid() -> None:
    stdout = "PID\tStatus\tLabel\n-\t0\tcom.custom.idle\n"
    snaps = parse_launchctl_output("mac-mini", stdout)
    assert len(snaps) == 1
    assert snaps[0].status == "loaded"


def test_parse_empty() -> None:
    stdout = (FIXTURES / "list_empty.txt").read_text()
    snaps = parse_launchctl_output("mac-mini", stdout)
    assert snaps == []


def test_parse_skips_short_lines() -> None:
    stdout = "PID\tStatus\tLabel\nbadline\n"
    snaps = parse_launchctl_output("mac-mini", stdout)
    assert snaps == []


def test_scanner_discover() -> None:
    stdout = (FIXTURES / "list.txt").read_text()
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.LAUNCHCTL_LIST, ()): SshResult(
                stdout=stdout, stderr="", exit_code=0
            ),
        }
    )
    scanner = LaunchdScanner()
    snaps = scanner.discover(_host(), executor)
    assert len(snaps) == 3
    assert executor.history[0].template is CommandTemplate.LAUNCHCTL_LIST
