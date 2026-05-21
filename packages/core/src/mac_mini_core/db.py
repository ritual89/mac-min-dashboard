from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hosts (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    tailscale_host TEXT NOT NULL,
    ssh_user TEXT NOT NULL,
    ssh_key_path TEXT NOT NULL,
    os TEXT NOT NULL,
    poll_interval_sec INTEGER
);

CREATE TABLE IF NOT EXISTS workloads (
    id TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    monitored INTEGER NOT NULL DEFAULT 0,
    pinned INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (host_id) REFERENCES hosts(id)
);

CREATE TABLE IF NOT EXISTS workload_state (
    workload_id TEXT PRIMARY KEY,
    last_seen TEXT,
    status TEXT,
    severity TEXT NOT NULL DEFAULT 'green',
    severity_reason TEXT,
    restart_count_1h INTEGER NOT NULL DEFAULT 0,
    last_error_snippet TEXT,
    FOREIGN KEY (workload_id) REFERENCES workloads(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_history (
    workload_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    FOREIGN KEY (workload_id) REFERENCES workloads(id)
);
"""

DEFAULT_SETTINGS = {
    "notify_orange": "true",
    "notify_red": "true",
}


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row["name"]) for row in rows}
