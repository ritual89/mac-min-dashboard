from __future__ import annotations

import pytest

from mac_mini_core.models import WorkloadKind
from mac_mini_core.workload_id import build_workload_id


def test_docker_workload_id_stable() -> None:
    wid = build_workload_id(WorkloadKind.DOCKER, "mac-mini", "nginx")
    assert wid == "docker:mac-mini:nginx"


def test_colons_in_parts_sanitized() -> None:
    wid = build_workload_id(WorkloadKind.COMPOSE, "vultr-1", "proj:svc")
    assert wid == "compose:vultr-1:proj_svc"


def test_missing_host_id_rejected() -> None:
    with pytest.raises(ValueError, match="host_id"):
        build_workload_id(WorkloadKind.DOCKER, "", "nginx")


def test_missing_parts_rejected() -> None:
    with pytest.raises(ValueError, match="identifying part"):
        build_workload_id(WorkloadKind.DOCKER, "mac-mini")
