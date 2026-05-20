from __future__ import annotations

import pytest

from mac_mini_core.models import Severity
from mac_mini_core.severity import SeverityInput, evaluate_severity


def _base(**overrides: object) -> SeverityInput:
    defaults = {
        "status": "running",
        "docker_health": "healthy",
        "log_tail": "",
        "http_probe_configured": False,
        "http_probe_ok": None,
        "expected_running": True,
        "restart_count_1h": 0,
        "restart_loop_threshold": 5,
    }
    defaults.update(overrides)
    return SeverityInput(**defaults)  # type: ignore[arg-type]


# AC-4.1
def test_ac_4_1_healthy_running_is_green() -> None:
    result = evaluate_severity(_base())
    assert result.severity is Severity.GREEN
    assert result.reason is None


# AC-4.2
def test_ac_4_2_unhealthy_docker_is_red() -> None:
    result = evaluate_severity(_base(docker_health="unhealthy"))
    assert result.severity is Severity.RED
    assert result.reason is not None
    assert "health" in result.reason


# AC-4.3
def test_ac_4_3_traceback_in_logs_is_red() -> None:
    result = evaluate_severity(_base(log_tail="Traceback (most recent call last):"))
    assert result.severity is Severity.RED
    assert "logs" in (result.reason or "")


# AC-4.4
def test_ac_4_4_panic_in_logs_is_red() -> None:
    result = evaluate_severity(_base(log_tail="panic: runtime error"))
    assert result.severity is Severity.RED


# AC-4.5
def test_ac_4_5_failed_http_probe_is_red() -> None:
    result = evaluate_severity(
        _base(http_probe_configured=True, http_probe_ok=False)
    )
    assert result.severity is Severity.RED
    assert "probe" in (result.reason or "")


# AC-4.6
def test_ac_4_6_exited_when_expected_running_is_orange() -> None:
    result = evaluate_severity(_base(status="exited"))
    assert result.severity is Severity.ORANGE
    assert "stopped" in (result.reason or "")


# AC-4.7
def test_ac_4_7_restart_loop_is_orange() -> None:
    result = evaluate_severity(_base(restart_count_1h=6))
    assert result.severity is Severity.ORANGE
    assert "restart loop" in (result.reason or "")


# AC-4.8
def test_ac_4_8_red_beats_orange() -> None:
    result = evaluate_severity(
        _base(status="exited", docker_health="unhealthy")
    )
    assert result.severity is Severity.RED


# AC-4.9
def test_ac_4_9_absent_probe_does_not_cause_red() -> None:
    result = evaluate_severity(_base(http_probe_configured=False, http_probe_ok=False))
    assert result.severity is Severity.GREEN


# EC-4.1
def test_ec_4_1_empty_log_tail_no_red() -> None:
    result = evaluate_severity(_base(log_tail=""))
    assert result.severity is Severity.GREEN
