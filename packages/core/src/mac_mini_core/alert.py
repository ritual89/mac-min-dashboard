from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from mac_mini_core.models import Severity

DEBOUNCE_SECONDS = 900  # 15 minutes


@dataclass(frozen=True)
class AlertDecision:
    should_send: bool
    reason: str


def should_alert(
    old_severity: str,
    new_severity: str,
    *,
    notify_orange: bool = True,
    notify_red: bool = True,
    last_alert_time: datetime | None = None,
    now: datetime | None = None,
) -> AlertDecision:
    if old_severity == new_severity:
        return AlertDecision(should_send=False, reason="no transition")

    if new_severity == Severity.GREEN.value:
        return AlertDecision(should_send=False, reason="recovered to green")

    if new_severity == Severity.ORANGE.value and not notify_orange:
        return AlertDecision(should_send=False, reason="orange notifications disabled")

    if new_severity == Severity.RED.value and not notify_red:
        return AlertDecision(should_send=False, reason="red notifications disabled")

    if now is None:
        now = datetime.now(UTC)

    if new_severity == Severity.RED.value:
        return AlertDecision(should_send=True, reason="severity escalated to red")

    if last_alert_time is not None:
        elapsed = (now - last_alert_time).total_seconds()
        if elapsed < DEBOUNCE_SECONDS:
            return AlertDecision(
                should_send=False,
                reason=f"debounced ({int(elapsed)}s < {DEBOUNCE_SECONDS}s)",
            )

    return AlertDecision(should_send=True, reason="severity transition")
