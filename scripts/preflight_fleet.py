#!/usr/bin/env python3
"""Verify SSH and Docker on every host in config before hub deploy."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from mac_mini_core.config import load_config
from mac_mini_core.deploy.preflight import (
    failure_hint,
    host_target,
    run_remote,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


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
        result = run_remote(host, install_docker=args.install_docker)
        target = host_target(host)
        if result.ok:
            print(f"OK   {host.id} ({target})")
            continue
        failed = True
        print(f"FAIL {host.id} ({target})")
        if result.detail:
            for line in result.detail.splitlines()[:5]:
                print(f"     {line}")
        hint = failure_hint(host, install_docker=args.install_docker)
        if hint:
            print(f"     {hint}")

    if failed:
        return 1
    print(f"Fleet preflight passed ({len(config.hosts)} host(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
