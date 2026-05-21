from __future__ import annotations

import os
from pathlib import Path

from mac_mini_core.config import load_config
from mac_mini_core.store import WorkloadStore
from mac_mini_core.telegram import TelegramNotifier, TelegramSender
from mac_mini_core.worker.poll import PollPass

from mac_mini_worker.scheduler import WorkerScheduler
from mac_mini_worker.ssh import create_executor_factory


def _config_path() -> Path:
    return Path(os.environ.get("DASHBOARD_CONFIG_PATH", "config/config.yaml"))


def _db_path() -> str:
    return os.environ.get("DASHBOARD_DB_PATH", "./data/fleet.db")


def _audit_interval_sec() -> float:
    return float(os.environ.get("DASHBOARD_AUDIT_INTERVAL_SEC", "300"))


def _build_notifier() -> TelegramSender | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if token and chat_id:
        return TelegramNotifier(bot_token=token, chat_id=chat_id)
    return None


def _dashboard_url() -> str | None:
    return os.environ.get("DASHBOARD_URL") or None


def build_scheduler() -> WorkerScheduler:
    config = load_config(_config_path())
    store = WorkloadStore.open(_db_path())
    notifier = _build_notifier()
    poll_pass = PollPass(
        notifier=notifier,
        dashboard_url=_dashboard_url(),
    )
    return WorkerScheduler(
        config=config,
        store=store,
        executor_factory=create_executor_factory(config),
        audit_interval_sec=_audit_interval_sec(),
        poll_pass=poll_pass,
    )


def run_worker(*, max_ticks: int | None = None) -> int:
    scheduler = build_scheduler()
    try:
        return scheduler.run_forever(max_ticks=max_ticks)
    finally:
        store = getattr(scheduler, "store", None)
        if store is not None:
            store.close()


def run() -> None:
    run_worker()


if __name__ == "__main__":  # pragma: no cover
    run()
