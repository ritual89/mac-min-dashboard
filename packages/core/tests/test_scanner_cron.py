from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import HostConfig
from mac_mini_core.models import HostOS, WorkloadKind
from mac_mini_core.scanners.cron import CronScanner, parse_crontab_output
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult

FIXTURES = Path(__file__).parent / "fixtures" / "cron"


def _host() -> HostConfig:
    return HostConfig(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id",
        os=HostOS.DARWIN,
    )


def test_parse_crontab() -> None:
    stdout = (FIXTURES / "crontab.txt").read_text()
    snaps = parse_crontab_output("mac-mini", stdout)
    assert len(snaps) == 2
    assert snaps[0].kind == WorkloadKind.CRON
    assert snaps[0].status == "scheduled"
    assert "cron:mac-mini:" in snaps[0].workload_id


def test_stable_ids_across_runs() -> None:
    stdout = (FIXTURES / "crontab.txt").read_text()
    snaps1 = parse_crontab_output("mac-mini", stdout)
    snaps2 = parse_crontab_output("mac-mini", stdout)
    assert [s.workload_id for s in snaps1] == [s.workload_id for s in snaps2]


def test_parse_empty() -> None:
    stdout = (FIXTURES / "crontab_empty.txt").read_text()
    snaps = parse_crontab_output("mac-mini", stdout)
    assert snaps == []


def test_skips_comment_lines() -> None:
    stdout = "# this is a comment\n0 * * * * /usr/bin/job\n"
    snaps = parse_crontab_output("mac-mini", stdout)
    assert len(snaps) == 1


def test_scanner_discover() -> None:
    stdout = (FIXTURES / "crontab.txt").read_text()
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.CRONTAB_LIST, ()): SshResult(
                stdout=stdout, stderr="", exit_code=0
            ),
        }
    )
    scanner = CronScanner()
    snaps = scanner.discover(_host(), executor)
    assert len(snaps) == 2
    assert executor.history[0].template is CommandTemplate.CRONTAB_LIST
