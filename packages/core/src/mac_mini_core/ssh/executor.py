from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from mac_mini_core.ssh.commands import CommandTemplate, render_command
from mac_mini_core.ssh.errors import SshExecutionError


@dataclass
class SshResult:
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class RecordedCommand:
    template: CommandTemplate
    params: dict[str, object]
    rendered: str


class SshExecutor(Protocol):
    def execute(self, template: CommandTemplate, **params: object) -> SshResult: ...


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_sec: float = 0.01


@dataclass
class RetryingExecutor:
    inner: SshExecutor
    policy: RetryPolicy = field(default_factory=RetryPolicy)
    retryable_exceptions: tuple[type[Exception], ...] = (TimeoutError, SshExecutionError)

    def execute(self, template: CommandTemplate, **params: object) -> SshResult:
        last_error: Exception | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return self.inner.execute(template, **params)
            except self.retryable_exceptions as exc:
                last_error = exc
        msg = f"ssh command failed after {self.policy.max_attempts} attempts"
        raise SshExecutionError(msg) from last_error


@dataclass
class FakeSshExecutor:
    responses: dict[tuple[CommandTemplate, tuple[tuple[str, object], ...]], SshResult] = field(
        default_factory=dict
    )
    default_result: SshResult = field(
        default_factory=lambda: SshResult(stdout="", stderr="", exit_code=0)
    )
    history: list[RecordedCommand] = field(default_factory=list)
    failures_before_success: dict[
        tuple[CommandTemplate, tuple[tuple[str, object], ...]], int
    ] = field(default_factory=dict)
    _attempt_counts: dict[tuple[CommandTemplate, tuple[tuple[str, object], ...]], int] = (
        field(default_factory=dict)
    )

    def execute(self, template: CommandTemplate, **params: object) -> SshResult:
        rendered = render_command(template, **params)
        self.history.append(
            RecordedCommand(template=template, params=dict(params), rendered=rendered)
        )
        key = (template, tuple(sorted(params.items())))
        failures = self.failures_before_success.get(key, 0)
        attempts = self._attempt_counts.get(key, 0) + 1
        self._attempt_counts[key] = attempts
        if attempts <= failures:
            raise TimeoutError("simulated timeout")
        return self.responses.get(key, self.default_result)
