from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig
from mac_mini_core.ssh.commands import CommandTemplate, render_command
from mac_mini_core.ssh.executor import RetryingExecutor, SshExecutor, SshResult
from mac_mini_core.worker.audit import ExecutorFactory


@dataclass
class SubprocessSshExecutor:
    host: HostConfig
    timeout_sec: int

    def execute(self, template: CommandTemplate, **params: object) -> SshResult:
        remote_cmd = render_command(template, **params)
        key_path = str(Path(self.host.ssh_key_path).expanduser())
        target = f"{self.host.ssh_user}@{self.host.tailscale_host}"
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-i",
            key_path,
            target,
            remote_cmd,
        ]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_sec,
            check=False,
        )
        return SshResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
        )


def create_executor_factory(config: AppConfig) -> ExecutorFactory:
    def factory(host: HostConfig) -> SshExecutor:
        inner = SubprocessSshExecutor(host=host, timeout_sec=config.ssh_timeout_sec)
        return RetryingExecutor(inner=inner)

    return factory
