from __future__ import annotations

from pathlib import Path

import pytest

from deploy.plist_render import render_launchd_plist, render_plist_file

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHD_DIR = REPO_ROOT / "deploy" / "launchd"

VALUES = {
    "REPO_ROOT": "/opt/mac-mini-dashboard",
    "PYTHON": "/opt/mac-mini-dashboard/.venv/bin/python",
    "WORKER_BIN": "/opt/mac-mini-dashboard/.venv/bin/mac-mini-worker",
    "LOG_DIR": "/Users/greg/Library/Logs/mac-mini-dashboard",
}


# AC-13.1
def test_ac_13_1_api_plist_runs_api_module() -> None:
    plist = render_plist_file(
        LAUNCHD_DIR / "com.macmin.dashboard.api.plist",
        VALUES,
    )
    assert plist["Label"] == "com.macmin.dashboard.api"
    args = plist["ProgramArguments"]
    assert args[-1] == "mac_mini_api.main"
    assert plist["EnvironmentVariables"]["DASHBOARD_PORT"] == "8081"


# AC-13.2
def test_ac_13_2_worker_plist_runs_worker_binary() -> None:
    plist = render_plist_file(
        LAUNCHD_DIR / "com.macmin.dashboard.worker.plist",
        VALUES,
    )
    assert plist["Label"] == "com.macmin.dashboard.worker"
    assert plist["ProgramArguments"] == [VALUES["WORKER_BIN"]]


# AC-13.3
def test_ac_13_3_both_plists_use_repo_working_directory() -> None:
    for name in ("com.macmin.dashboard.api.plist", "com.macmin.dashboard.worker.plist"):
        plist = render_plist_file(LAUNCHD_DIR / name, VALUES)
        assert plist["WorkingDirectory"] == VALUES["REPO_ROOT"]
        assert plist["KeepAlive"] is True
        assert plist["RunAtLoad"] is True


# AC-13.4
def test_ac_13_4_unknown_placeholder_raises() -> None:
    with pytest.raises(ValueError, match="unknown placeholders"):
        render_launchd_plist("{{REPO_ROOT}} {{NOT_A_REAL_KEY}}", {"REPO_ROOT": "/x"})


def test_unsubstituted_placeholder_raises() -> None:
    with pytest.raises(ValueError, match="unsubstituted"):
        render_launchd_plist("{{REPO_ROOT}}", {"REPO_ROOT": "{{PYTHON}}"})
