from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mac_mini_core.config import HostConfig
from mac_mini_core.deploy.preflight import (
    build_remote_command,
    failure_hint,
    host_target,
    run_remote,
    ssh_base,
)
from mac_mini_core.models import HostOS


def _darwin_host(**overrides: object) -> HostConfig:
    defaults = {
        "id": "mac-mini",
        "display_name": "Mac Mini",
        "tailscale_host": "mac-mini",
        "ssh_user": "greg",
        "ssh_key_path": "~/.ssh/id_ed25519",
        "os": HostOS.DARWIN,
    }
    defaults.update(overrides)
    return HostConfig(**defaults)  # type: ignore[arg-type]


def _linux_host() -> HostConfig:
    return HostConfig(
        id="vultr-1",
        display_name="Vultr",
        tailscale_host="vultr-1",
        ssh_user="root",
        ssh_key_path="~/.ssh/id_ed25519",
        os=HostOS.LINUX,
    )


def test_ssh_base_uses_explicit_key_when_no_alias() -> None:
    host = _darwin_host()
    assert ssh_base(host) == [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-i",
        str(Path("~/.ssh/id_ed25519").expanduser()),
        "greg@mac-mini",
    ]


def test_ssh_base_uses_config_alias() -> None:
    host = _darwin_host(ssh_host="mac-mini")
    assert ssh_base(host) == ["ssh", "-o", "BatchMode=yes", "mac-mini"]


def test_build_remote_command_wraps_darwin_docker_check() -> None:
    remote = build_remote_command(_darwin_host(), install_docker=False)
    assert "/opt/homebrew/bin" in remote
    assert "docker ps --format" in remote


def test_build_remote_command_includes_install_script_when_requested() -> None:
    remote = build_remote_command(_darwin_host(), install_docker=True)
    assert "colima start" in remote
    assert "docker ps --format" in remote


def test_build_remote_command_wraps_linux_docker_check() -> None:
    remote = build_remote_command(_linux_host(), install_docker=False)
    assert "/snap/bin" in remote
    assert "colima" not in remote


def test_run_remote_returns_success_from_runner() -> None:
    completed = MagicMock(spec=subprocess.CompletedProcess)
    completed.returncode = 0
    completed.stdout = "ok"
    completed.stderr = ""
    result = run_remote(_darwin_host(), install_docker=False, runner=completed)
    assert result.ok is True
    assert result.detail == "ok"


def test_run_remote_returns_failure_detail() -> None:
    completed = MagicMock(spec=subprocess.CompletedProcess)
    completed.returncode = 1
    completed.stdout = ""
    completed.stderr = "permission denied"
    result = run_remote(_linux_host(), install_docker=False, runner=completed)
    assert result.ok is False
    assert result.detail == "permission denied"


def test_host_target_prefers_ssh_host_alias() -> None:
    assert host_target(_darwin_host(ssh_host="mac-mini")) == "mac-mini"
    assert host_target(_darwin_host()) == "greg@mac-mini"


def test_failure_hint_for_darwin_and_linux() -> None:
    darwin_hint = failure_hint(_darwin_host(), install_docker=False)
    assert darwin_hint is not None
    assert "colima" in darwin_hint.lower()
    assert failure_hint(_darwin_host(), install_docker=True) is None
    linux_hint = failure_hint(_linux_host(), install_docker=False)
    assert linux_hint is not None
    assert "docker group" in linux_hint.lower()


def test_run_remote_invokes_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        captured.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = "ok"
        result.stderr = ""
        return result

    monkeypatch.setattr("mac_mini_core.deploy.preflight.subprocess.run", fake_run)
    result = run_remote(_darwin_host(), install_docker=False)
    assert result.ok is True
    assert captured[0][0] == "ssh"
    assert "/opt/homebrew/bin" in captured[0][-1]


def test_preflight_script_exits_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import importlib

    preflight_fleet = importlib.import_module("scripts.preflight_fleet")
    importlib.reload(preflight_fleet)

    from mac_mini_core.config import AppConfig
    from mac_mini_core.deploy.preflight import RemoteResult

    config_path = tmp_path / "config.yaml"
    config_path.write_text("hosts: []\n", encoding="utf-8")

    monkeypatch.setattr(
        preflight_fleet,
        "load_config",
        lambda path: AppConfig(hosts=[_darwin_host()]),
    )
    monkeypatch.setattr(
        preflight_fleet,
        "run_remote",
        lambda host, install_docker=False: RemoteResult(ok=True, detail=""),
    )
    monkeypatch.setattr(sys, "argv", ["preflight_fleet.py", "--config", str(config_path)])

    assert preflight_fleet.main() == 0
    out = capsys.readouterr().out
    assert "OK   mac-mini" in out
    assert "Fleet preflight passed (1 host(s))." in out


def test_preflight_script_exits_one_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import importlib

    preflight_fleet = importlib.import_module("scripts.preflight_fleet")
    importlib.reload(preflight_fleet)

    from mac_mini_core.config import AppConfig
    from mac_mini_core.deploy.preflight import RemoteResult

    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr(
        preflight_fleet,
        "load_config",
        lambda path: AppConfig(hosts=[_linux_host()]),
    )
    monkeypatch.setattr(
        preflight_fleet,
        "run_remote",
        lambda host, install_docker=False: RemoteResult(
            ok=False,
            detail="docker: not found",
        ),
    )
    monkeypatch.setattr(sys, "argv", ["preflight_fleet.py", "--config", str(config_path)])

    assert preflight_fleet.main() == 1
    out = capsys.readouterr().out
    assert "FAIL vultr-1" in out
    assert "docker group" in out
