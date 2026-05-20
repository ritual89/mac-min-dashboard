from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mac_mini_core.db import connect, get_setting, init_schema, table_names


# AC-1.5: schema init creates all tables
def test_ac_1_5_schema_init_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    try:
        init_schema(conn)
        names = table_names(conn)
        assert names >= {"hosts", "workloads", "workload_state", "settings"}
    finally:
        conn.close()


# AC-1.6: default notification settings
def test_ac_1_6_default_notification_settings(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    try:
        init_schema(conn)
        assert get_setting(conn, "notify_orange") == "true"
        assert get_setting(conn, "notify_red") == "true"
    finally:
        conn.close()


def test_init_schema_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db")
    try:
        init_schema(conn)
        init_schema(conn)
        assert len(table_names(conn)) >= 4
    finally:
        conn.close()
