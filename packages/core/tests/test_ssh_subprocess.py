from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mac_mini_core.config import AppConfig, HostConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import RetryingExecutor, SshResult
from mac_mini_core.ssh.subprocess import SubprocessSshExecutor, create_executor_factory


def _host() -> HostConfig:
    return HostConfig(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id_ed25519",
        os=HostOS.DARWIN,
    )


def test_subprocess_ssh_uses_ssh_config_host_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        captured.append(cmd)
        result = MagicMock()
        result.stdout = "[]"
        result.stderr = ""
        result.returncode = 0
        return result

    monkeypatch.setattr("mac_mini_core.ssh.subprocess.subprocess.run", fake_run)

    host = HostConfig(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="ignored",
        ssh_key_path="~/.ssh/id_ed25519",
        os=HostOS.DARWIN,
        ssh_host="mac-mini",
    )
    executor = SubprocessSshExecutor(host=host, timeout_sec=30)
    executor.execute(CommandTemplate.DOCKER_PS)

    ssh_cmd = captured[0]
    assert ssh_cmd == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "mac-mini",
        ssh_cmd[-1],
    ]
    assert "docker ps --format" in ssh_cmd[-1]
    assert "/opt/homebrew/bin" in ssh_cmd[-1]
    assert "-i" not in ssh_cmd


def test_subprocess_ssh_invokes_allowlisted_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        captured.append(cmd)
        result = MagicMock()
        result.stdout = "[]"
        result.stderr = ""
        result.returncode = 0
        return result

    monkeypatch.setattr("mac_mini_core.ssh.subprocess.subprocess.run", fake_run)

    executor = SubprocessSshExecutor(host=_host(), timeout_sec=30)
    result = executor.execute(CommandTemplate.DOCKER_PS)

    assert result.stdout == "[]"
    assert len(captured) == 1
    ssh_cmd = captured[0]
    assert ssh_cmd[0] == "ssh"
    assert "greg@mac-mini" in ssh_cmd[-2]
    assert "docker ps --format" in ssh_cmd[-1]
    assert "/opt/homebrew/bin" in ssh_cmd[-1]


def test_create_executor_factory_wraps_retrying_executor() -> None:
    factory = create_executor_factory(AppConfig(hosts=[_host()]))
    executor = factory(_host())
    assert isinstance(executor, RetryingExecutor)
