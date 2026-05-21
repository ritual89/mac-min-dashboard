from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from mac_mini_core.config import PromoteRulesConfig
from mac_mini_core.db import init_schema
from mac_mini_core.models import Severity, WorkloadSnapshot
from mac_mini_core.promote import WorkloadPromoteInput, should_promote
from mac_mini_core.severity import SeverityInput, evaluate_severity


@dataclass(frozen=True)
class HostRow:
    id: str
    display_name: str
    tailscale_host: str
    ssh_user: str
    ssh_key_path: str
    os: str
    last_seen: str | None


@dataclass(frozen=True)
class WorkloadRow:
    id: str
    host_id: str
    kind: str
    name: str
    monitored: bool
    pinned: bool
    status: str
    severity: str
    severity_reason: str | None
    last_seen: str | None
    metadata: dict[str, Any]


@dataclass
class WorkloadStore:
    conn: sqlite3.Connection

    @classmethod
    def open(cls, path: str) -> WorkloadStore:
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        init_schema(conn)
        return cls(conn=conn)

    def close(self) -> None:
        self.conn.close()

    def ensure_host(self, host: HostConfig) -> None:
        self.conn.execute(
            """
            INSERT INTO hosts (id, display_name, tailscale_host, ssh_user, ssh_key_path, os)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                tailscale_host = excluded.tailscale_host,
                ssh_user = excluded.ssh_user,
                ssh_key_path = excluded.ssh_key_path,
                os = excluded.os
            """,
            (
                host.id,
                host.display_name,
                host.tailscale_host,
                host.ssh_user,
                host.ssh_key_path,
                host.os.value,
            ),
        )
        self.conn.commit()

    def is_pinned(self, workload_id: str) -> bool:
        row = self.conn.execute(
            "SELECT pinned FROM workloads WHERE id = ?",
            (workload_id,),
        ).fetchone()
        return bool(row and row["pinned"])

    def upsert_snapshot(
        self,
        snapshot: WorkloadSnapshot,
        *,
        project_roots: list[str] | None = None,
        allowlist: list[str] | None = None,
        port_denylist: list[int] | None = None,
    ) -> None:
        rules = PromoteRulesConfig(
            project_roots=project_roots or ["~/dev"],
            allowlist=allowlist or [],
            port_denylist=port_denylist or [],
        )
        pinned = self.is_pinned(snapshot.workload_id)
        promote_input = WorkloadPromoteInput(
            kind=snapshot.kind,
            name=snapshot.name,
            project_path=None,
            listen_port=None,
            pinned=pinned,
        )
        monitored = should_promote(promote_input, rules)

        metadata = {
            "image": snapshot.image,
            "compose_project": snapshot.compose_project,
            "compose_service": snapshot.compose_service,
        }
        now = datetime.now(UTC).isoformat()

        self.conn.execute(
            """
            INSERT INTO hosts (id, display_name, tailscale_host, ssh_user, ssh_key_path, os)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                snapshot.host_id,
                snapshot.host_id,
                snapshot.host_id,
                "unknown",
                "~/.ssh/id_ed25519",
                "linux",
            ),
        )
        self.conn.execute(
            """
            INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                name = excluded.name,
                monitored = excluded.monitored,
                metadata_json = excluded.metadata_json
            """,
            (
                snapshot.workload_id,
                snapshot.host_id,
                snapshot.kind.value,
                snapshot.name,
                1 if monitored else 0,
                1 if pinned else 0,
                json.dumps(metadata),
            ),
        )
        self.conn.execute(
            """
            INSERT INTO workload_state (
                workload_id, last_seen, status, severity, severity_reason,
                restart_count_1h, last_error_snippet
            )
            VALUES (?, ?, ?, ?, ?, 0, NULL)
            ON CONFLICT(workload_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                status = excluded.status
            """,
            (
                snapshot.workload_id,
                now,
                snapshot.status,
                Severity.GREEN.value,
                None,
            ),
        )
        self.conn.commit()

    def list_monitored_ids(self, host_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT id FROM workloads WHERE host_id = ? AND monitored = 1",
            (host_id,),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def apply_poll_update(
        self,
        workload_id: str,
        snapshot: WorkloadSnapshot | None,
        *,
        restart_loop_threshold: int = 5,
        log_tail: str | None = None,
        restart_count: int = 0,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        if snapshot is None:
            self.conn.execute(
                """
                UPDATE workload_state SET
                    last_seen = ?,
                    status = ?,
                    severity = ?,
                    severity_reason = ?
                WHERE workload_id = ?
                """,
                (
                    now,
                    "missing",
                    Severity.ORANGE.value,
                    "not found in scan",
                    workload_id,
                ),
            )
            self.conn.commit()
            return

        row = self.conn.execute(
            "SELECT restart_count_1h FROM workload_state WHERE workload_id = ?",
            (workload_id,),
        ).fetchone()
        effective_restart_count = restart_count if restart_count > 0 else (int(row["restart_count_1h"]) if row else 0)

        result = evaluate_severity(
            SeverityInput(
                status=snapshot.status,
                docker_health=snapshot.docker_health,
                expected_running=True,
                restart_count_1h=effective_restart_count,
                restart_loop_threshold=restart_loop_threshold,
                log_tail=log_tail,
            )
        )
        self.conn.execute(
            """
            UPDATE workload_state SET
                last_seen = ?,
                status = ?,
                severity = ?,
                severity_reason = ?,
                restart_count_1h = ?
            WHERE workload_id = ?
            """,
            (
                now,
                snapshot.status,
                result.severity.value,
                result.reason,
                effective_restart_count,
                workload_id,
            ),
        )
        self.conn.commit()

    def pin_workload(self, workload_id: str) -> bool:
        row = self.conn.execute(
            "SELECT id FROM workloads WHERE id = ?", (workload_id,)
        ).fetchone()
        if row is None:
            return False
        self.conn.execute(
            "UPDATE workloads SET pinned = 1, monitored = 1 WHERE id = ?",
            (workload_id,),
        )
        self.conn.commit()
        return True

    def unpin_workload(
        self,
        workload_id: str,
        rules: PromoteRulesConfig,
    ) -> bool:
        row = self.conn.execute(
            "SELECT id, kind, name FROM workloads WHERE id = ?",
            (workload_id,),
        ).fetchone()
        if row is None:
            return False

        promote_input = WorkloadPromoteInput(
            kind=str(row["kind"]),
            name=str(row["name"]),
            project_path=None,
            listen_port=None,
            pinned=False,
        )
        monitored = should_promote(promote_input, rules)
        self.conn.execute(
            "UPDATE workloads SET pinned = 0, monitored = ? WHERE id = ?",
            (1 if monitored else 0, workload_id),
        )
        self.conn.commit()
        return True

    _KNOWN_SETTINGS = frozenset({"notify_orange", "notify_red"})

    def get_settings(self) -> dict[str, bool]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(row["key"]): str(row["value"]) == "true" for row in rows}

    def update_settings(self, patch: dict[str, bool]) -> set[str]:
        unknown = set(patch.keys()) - self._KNOWN_SETTINGS
        if unknown:
            return unknown
        for key, value in patch.items():
            self.conn.execute(
                "UPDATE settings SET value = ? WHERE key = ?",
                ("true" if value else "false", key),
            )
        self.conn.commit()
        return set()

    def record_alert(self, workload_id: str, severity: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO alert_history (workload_id, severity, sent_at) VALUES (?, ?, ?)",
            (workload_id, severity, now),
        )
        self.conn.commit()

    def last_alert_time(self, workload_id: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT sent_at FROM alert_history WHERE workload_id = ? ORDER BY sent_at DESC LIMIT 1",
            (workload_id,),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(str(row["sent_at"]))

    def get_state(self, workload_id: str) -> tuple[str, str, str | None]:
        row = self.conn.execute(
            """
            SELECT status, severity, severity_reason
            FROM workload_state WHERE workload_id = ?
            """,
            (workload_id,),
        ).fetchone()
        if row is None:
            return ("unknown", Severity.GREEN.value, None)
        return (
            str(row["status"]),
            str(row["severity"]),
            row["severity_reason"],
        )

    def count_workloads(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM workloads").fetchone()
        return int(row["c"])

    def get_monitored(self, workload_id: str) -> bool:
        row = self.conn.execute(
            "SELECT monitored FROM workloads WHERE id = ?",
            (workload_id,),
        ).fetchone()
        return bool(row and row["monitored"])

    def list_hosts(self) -> list[HostRow]:
        rows = self.conn.execute(
            """
            SELECT h.id, h.display_name, h.tailscale_host, h.ssh_user, h.ssh_key_path, h.os,
                   MAX(ws.last_seen) AS last_seen
            FROM hosts h
            LEFT JOIN workloads w ON w.host_id = h.id
            LEFT JOIN workload_state ws ON ws.workload_id = w.id
            GROUP BY h.id
            ORDER BY h.display_name
            """
        ).fetchall()
        return [
            HostRow(
                id=str(row["id"]),
                display_name=str(row["display_name"]),
                tailscale_host=str(row["tailscale_host"]),
                ssh_user=str(row["ssh_user"]),
                ssh_key_path=str(row["ssh_key_path"]),
                os=str(row["os"]),
                last_seen=row["last_seen"],
            )
            for row in rows
        ]

    def list_workloads(
        self,
        *,
        monitored: bool | None = None,
        host_id: str | None = None,
        severity: str | None = None,
    ) -> list[WorkloadRow]:
        clauses: list[str] = []
        params: list[object] = []
        if monitored is not None:
            clauses.append("w.monitored = ?")
            params.append(1 if monitored else 0)
        if host_id is not None:
            clauses.append("w.host_id = ?")
            params.append(host_id)
        if severity is not None:
            clauses.append("ws.severity = ?")
            params.append(severity)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT w.id, w.host_id, w.kind, w.name, w.monitored, w.pinned, w.metadata_json,
                   ws.status, ws.severity, ws.severity_reason, ws.last_seen
            FROM workloads w
            JOIN workload_state ws ON ws.workload_id = w.id
            {where}
            ORDER BY w.host_id, w.kind, w.name
            """,
            params,
        ).fetchall()
        return [_row_to_workload(row) for row in rows]

    def get_host(self, host_id: str) -> HostRow | None:
        row = self.conn.execute(
            """
            SELECT h.id, h.display_name, h.tailscale_host, h.ssh_user, h.ssh_key_path, h.os,
                   MAX(ws.last_seen) AS last_seen
            FROM hosts h
            LEFT JOIN workloads w ON w.host_id = h.id
            LEFT JOIN workload_state ws ON ws.workload_id = w.id
            WHERE h.id = ?
            GROUP BY h.id
            """,
            (host_id,),
        ).fetchone()
        if row is None:
            return None
        return HostRow(
            id=str(row["id"]),
            display_name=str(row["display_name"]),
            tailscale_host=str(row["tailscale_host"]),
            ssh_user=str(row["ssh_user"]),
            ssh_key_path=str(row["ssh_key_path"]),
            os=str(row["os"]),
            last_seen=row["last_seen"],
        )

    def get_workload(self, workload_id: str) -> WorkloadRow | None:
        row = self.conn.execute(
            """
            SELECT w.id, w.host_id, w.kind, w.name, w.monitored, w.pinned, w.metadata_json,
                   ws.status, ws.severity, ws.severity_reason, ws.last_seen
            FROM workloads w
            JOIN workload_state ws ON ws.workload_id = w.id
            WHERE w.id = ?
            """,
            (workload_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_workload(row)


def _row_to_workload(row: sqlite3.Row) -> WorkloadRow:
    return WorkloadRow(
        id=str(row["id"]),
        host_id=str(row["host_id"]),
        kind=str(row["kind"]),
        name=str(row["name"]),
        monitored=bool(row["monitored"]),
        pinned=bool(row["pinned"]),
        status=str(row["status"]),
        severity=str(row["severity"]),
        severity_reason=row["severity_reason"],
        last_seen=row["last_seen"],
        metadata=json.loads(str(row["metadata_json"])),
    )
