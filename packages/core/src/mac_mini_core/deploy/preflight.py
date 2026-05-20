from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from mac_mini_core.config import HostConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.shell import wrap_remote_command

DOCKER_CHECK = (
    "command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' >/dev/null 2>&1"
)
DARWIN_INSTALL_DOCKER = r"""
set -e
if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
  exit 0
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew required on macOS host to install Colima + Docker CLI" >&2
  exit 1
fi
brew list colima &>/dev/null 2>&1 || brew install colima docker
if ! colima status &>/dev/null 2>&1; then
  colima start
fi
docker ps --format '{{.Names}}' >/dev/null
"""


def ssh_base(host: HostConfig) -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes"]
    if host.ssh_host:
        cmd.append(host.ssh_host)
    else:
        key = str(Path(host.ssh_key_path).expanduser())
        cmd.extend(["-i", key, f"{host.ssh_user}@{host.tailscale_host}"])
    return cmd


def build_remote_command(host: HostConfig, *, install_docker: bool) -> str:
    if install_docker and host.os is HostOS.DARWIN:
        body = f"{DARWIN_INSTALL_DOCKER}\n{DOCKER_CHECK}"
    else:
        body = DOCKER_CHECK
    return wrap_remote_command(body, host.os)


@dataclass(frozen=True)
class RemoteResult:
    ok: bool
    detail: str


def run_remote(
    host: HostConfig,
    *,
    install_docker: bool,
    runner: subprocess.CompletedProcess[str] | None = None,
) -> RemoteResult:
    remote = build_remote_command(host, install_docker=install_docker)
    cmd = [*ssh_base(host), remote]
    if runner is None:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    else:
        completed = runner
    detail = (completed.stderr or completed.stdout or "").strip()
    return RemoteResult(ok=completed.returncode == 0, detail=detail)


def host_target(host: HostConfig) -> str:
    return host.ssh_host or f"{host.ssh_user}@{host.tailscale_host}"


def failure_hint(host: HostConfig, *, install_docker: bool) -> str | None:
    if host.os is HostOS.DARWIN and not install_docker:
        return (
            "Fix: on the Mac host, install Docker (e.g. brew install colima docker && colima start)"
            " or re-run: uv run python scripts/preflight_fleet.py --install-docker"
        )
    if host.os is HostOS.LINUX:
        return "Fix: install docker.io / docker-ce and add the SSH user to the docker group"
    return None
