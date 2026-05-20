from __future__ import annotations

import pytest

from mac_mini_core.config import PromoteRulesConfig
from mac_mini_core.models import WorkloadKind
from mac_mini_core.promote import WorkloadPromoteInput, should_promote


def _rules() -> PromoteRulesConfig:
    return PromoteRulesConfig(
        project_roots=["~/dev", "~/projects"],
        allowlist=["hermes", "dashboard-for-life"],
        port_denylist=[8080],
    )


# AC-5.1
def test_ac_5_1_docker_workload_promoted() -> None:
    assert should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.DOCKER, name="web"),
        _rules(),
    )


# AC-5.2
def test_ac_5_2_compose_under_project_root_promoted() -> None:
    assert should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.COMPOSE,
            name="api",
            project_path="~/dev/myproject",
        ),
        _rules(),
    )


# AC-5.3
def test_ac_5_3_high_port_listener_promoted() -> None:
    assert should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="node", listen_port=3000),
        _rules(),
    )


# AC-5.4
def test_ac_5_4_allowlist_name_promoted() -> None:
    assert should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="hermes"),
        _rules(),
    )


# AC-5.5
def test_ac_5_5_apple_launchd_not_promoted() -> None:
    assert not should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.LAUNCHD, name="com.apple.SomeService"),
        _rules(),
    )


# AC-5.6
def test_ac_5_6_system_path_not_promoted() -> None:
    assert not should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.PROCESS,
            name="app",
            project_path="/usr/local/bin/app",
        ),
        _rules(),
    )


# AC-5.7
def test_ac_5_7_pinned_always_monitored() -> None:
    assert should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.LAUNCHD,
            name="com.apple.SomeService",
            pinned=True,
        ),
        _rules(),
    )


# AC-5.8
def test_ac_5_8_unpinned_non_matching_not_promoted() -> None:
    assert not should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="random-daemon"),
        _rules(),
    )


# EC-5.1
def test_ec_5_1_port_1024_not_promoted() -> None:
    assert not should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="svc", listen_port=1024),
        _rules(),
    )


def test_port_on_denylist_not_promoted() -> None:
    assert not should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="svc", listen_port=8080),
        _rules(),
    )


def test_process_exact_project_root_promoted() -> None:
    assert should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.PROCESS,
            name="worker",
            project_path="~/dev",
        ),
        PromoteRulesConfig(project_roots=["~/dev"], allowlist=[], port_denylist=[]),
    )
    assert should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.PROCESS,
            name="worker",
            project_path="~/projects/myapp",
        ),
        PromoteRulesConfig(project_roots=["~/projects/"], allowlist=[], port_denylist=[]),
    )


def test_project_path_no_matching_root_falls_through() -> None:
    assert not should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.PROCESS,
            name="worker",
            project_path="/opt/other",
        ),
        PromoteRulesConfig(project_roots=["~/dev"], allowlist=[], port_denylist=[]),
    )


def test_project_path_matches_second_root() -> None:
    assert should_promote(
        WorkloadPromoteInput(
            kind=WorkloadKind.PROCESS,
            name="worker",
            project_path="~/projects/app",
        ),
        PromoteRulesConfig(project_roots=["~/dev", "~/projects"], allowlist=[], port_denylist=[]),
    )


@pytest.mark.parametrize(
    "path",
    ["/usr", "/usr/local/bin", "/System/Library", "/bin/sh", "/sbin/mount"],
)
def test_system_path_prefixes_not_promoted(path: str) -> None:
    assert not should_promote(
        WorkloadPromoteInput(kind=WorkloadKind.PROCESS, name="app", project_path=path),
        _rules(),
    )
