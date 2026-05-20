from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from mac_mini_api.app import create_app
from mac_mini_core.store import WorkloadStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_static_dir() -> Path | None:
    env = os.environ.get("DASHBOARD_STATIC_DIR")
    if env:
        path = Path(env)
        return path if path.is_dir() else None
    dist = _repo_root() / "apps" / "web" / "dist"
    return dist if dist.is_dir() else None


def _default_store() -> WorkloadStore:
    db_path = os.environ.get("DASHBOARD_DB_PATH", "./data/fleet.db")
    return WorkloadStore.open(db_path)


def create_production_app():
    return create_app(
        store=_default_store(),
        static_dir=_default_static_dir(),
    )


if __name__ == "__main__":  # pragma: no cover
    port = int(os.environ.get("DASHBOARD_PORT", "8081"))
    uvicorn.run(
        "mac_mini_api.main:create_production_app",
        factory=True,
        host="0.0.0.0",
        port=port,
    )
