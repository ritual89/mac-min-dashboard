from __future__ import annotations

import pytest

from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.errors import SshExecutionError
from mac_mini_core.ssh.executor import FakeSshExecutor, RetryingExecutor, RetryPolicy, SshResult


# AC-2.4: fake executor records commands
def test_ac_2_4_fake_executor_records_commands() -> None:
    fake = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="[]", stderr="", exit_code=0),
        }
    )
    result = fake.execute(CommandTemplate.DOCKER_PS)
    assert result.stdout == "[]"
    assert len(fake.history) == 1
    assert fake.history[0].template is CommandTemplate.DOCKER_PS
    assert "docker ps" in fake.history[0].rendered


def test_retry_succeeds_on_first_attempt() -> None:
    fake = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="ok", stderr="", exit_code=0),
        }
    )
    retrying = RetryingExecutor(fake)
    result = retrying.execute(CommandTemplate.DOCKER_PS)
    assert result.stdout == "ok"
    assert len(fake.history) == 1


# AC-2.5: retry succeeds on third attempt
def test_ac_2_5_retry_succeeds_on_third_attempt() -> None:
    fake = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="ok", stderr="", exit_code=0),
        },
        failures_before_success={
            (CommandTemplate.DOCKER_PS, ()): 2,
        },
    )
    retrying = RetryingExecutor(fake, policy=RetryPolicy(max_attempts=3))
    result = retrying.execute(CommandTemplate.DOCKER_PS)
    assert result.stdout == "ok"
    assert len(fake.history) == 3


# AC-2.6: all retries exhausted raises
def test_retry_single_attempt_fails_immediately() -> None:
    fake = FakeSshExecutor(
        failures_before_success={
            (CommandTemplate.DOCKER_PS, ()): 99,
        }
    )
    retrying = RetryingExecutor(fake, policy=RetryPolicy(max_attempts=1))
    with pytest.raises(SshExecutionError, match="failed after 1 attempts"):
        retrying.execute(CommandTemplate.DOCKER_PS)


def test_ac_2_6_all_retries_exhausted_raises() -> None:
    fake = FakeSshExecutor(
        failures_before_success={
            (CommandTemplate.DOCKER_PS, ()): 99,
        }
    )
    retrying = RetryingExecutor(fake, policy=RetryPolicy(max_attempts=3))
    with pytest.raises(SshExecutionError, match="failed after 3 attempts"):
        retrying.execute(CommandTemplate.DOCKER_PS)
    assert len(fake.history) == 3
