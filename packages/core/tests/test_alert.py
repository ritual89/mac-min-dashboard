from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mac_mini_core.alert import DEBOUNCE_SECONDS, should_alert


# AC-9.1
def test_ac_9_1_orange_transition_with_notify_on() -> None:
    result = should_alert("green", "orange", notify_orange=True)
    assert result.should_send is True


# AC-9.2
def test_ac_9_2_orange_transition_with_notify_off() -> None:
    result = should_alert("green", "orange", notify_orange=False)
    assert result.should_send is False
    assert "disabled" in result.reason


# AC-9.3
def test_ac_9_3_debounce_within_15_minutes() -> None:
    now = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC)
    last_alert = now - timedelta(seconds=60)
    result = should_alert(
        "green", "orange",
        last_alert_time=last_alert,
        now=now,
    )
    assert result.should_send is False
    assert "debounced" in result.reason


# AC-9.4
def test_ac_9_4_red_bypasses_debounce() -> None:
    now = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC)
    last_alert = now - timedelta(seconds=60)
    result = should_alert(
        "orange", "red",
        last_alert_time=last_alert,
        now=now,
    )
    assert result.should_send is True
    assert "red" in result.reason


def test_no_transition_no_alert() -> None:
    result = should_alert("green", "green")
    assert result.should_send is False
    assert "no transition" in result.reason


def test_recovery_to_green_no_alert() -> None:
    result = should_alert("red", "green")
    assert result.should_send is False
    assert "recovered" in result.reason


def test_red_notify_off_no_alert() -> None:
    result = should_alert("green", "red", notify_red=False)
    assert result.should_send is False
    assert "disabled" in result.reason


def test_debounce_expired_sends() -> None:
    now = datetime(2026, 1, 1, 12, 30, 0, tzinfo=UTC)
    last_alert = now - timedelta(seconds=DEBOUNCE_SECONDS + 1)
    result = should_alert(
        "green", "orange",
        last_alert_time=last_alert,
        now=now,
    )
    assert result.should_send is True


def test_orange_no_prior_alert_sends() -> None:
    result = should_alert("green", "orange", last_alert_time=None)
    assert result.should_send is True
