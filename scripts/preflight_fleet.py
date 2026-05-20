#!/usr/bin/env python3
"""Verify SSH and Docker on every host in config before hub deploy."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from mac_mini_core.config import HostConfig, load_config
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.shell import wrap_remote_command

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DOCKER_CHECK = "command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' >/dev/null 2>&1"
_DARWIN_INSTALL_DOCKER = r"""
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


def _ssh_base(host: HostConfig) -> list[str]:
    cmd = ["ssh", "-o", "BatchMode=yes"]
    if host.ssh_host:
        cmd.append(host.ssh_host)
    else:
        key = str(Path(host.ssh_key_path).expanduser())
        cmd.extend(["-i", key, f"{host.ssh_user}@{host.tailscale_host}"])
    return cmd


def _run_remote(host: HostConfig, *, install_docker: bool) -> tuple[bool, str]:
    if install_docker and host.os is HostOS.DARWIN:
        remote = wrap_remote_command(f"{_DARWIN_INSTALL_DOCKER}\n{_DOCKER_CHECK}", host.os)
    else:
        remote = wrap_remote_command(_DOCKER_CHECK, host.os)
    cmd = [*_ssh_base(host), remote]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    detail = (completed.stderr or completed.stdout or "").strip()
    return completed.returncode == 0, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=os.environ.get("DASHBOARD_CONFIG_PATH", "config/config.yaml"),
        type=Path,
    )
    parser.add_argument(
        "--install-docker",
        action="store_true",
        help="On macOS hosts missing Docker, install Colima + docker via Homebrew over SSH",
    )
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else _REPO_ROOT / args.config
    config = load_config(config_path)

    failed = False
    for host in config.hosts:
        ok, detail = _run_remote(host, install_docker=args.install_docker)
        target = host.ssh_host or f"{host.ssh_user}@{host.tailscale_host}"
        if ok:
            print(f"OK   {host.id} ({target})")
            continue
        failed = True
        print(f"FAIL {host.id} ({target})")
        if detail:
            for line in detail.splitlines()[:5]:
                print(f"     {line}")
        if host.os is HostOS.DARWIN and not args.install_docker:
            print(
                "     Fix: on the Mac host, install Docker (e.g. brew install colima docker && colima start)"
                " or re-run: uv run python scripts/preflight_fleet.py --install-docker"
            )
        elif host.os is HostOS.LINUX:
            print("     Fix: install docker.io / docker-ce and add the SSH user to the docker group")

    if failed:
        return 1
    print(f"Fleet preflight passed ({len(config.hosts)} host(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
