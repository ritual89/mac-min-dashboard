from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx


class TelegramSender(Protocol):
    def send_alert(
        self,
        host: str,
        workload_name: str,
        severity: str,
        reason: str | None,
        dashboard_url: str | None,
    ) -> bool: ...


@dataclass
class TelegramNotifier:
    bot_token: str
    chat_id: str
    client: httpx.Client = field(default_factory=httpx.Client)

    def send_alert(
        self,
        host: str,
        workload_name: str,
        severity: str,
        reason: str | None,
        dashboard_url: str | None,
    ) -> bool:
        lines = [
            f"🔴 {severity.upper()}" if severity == "red" else f"🟠 {severity.upper()}",
            f"Host: {host}",
            f"Workload: {workload_name}",
        ]
        if reason:
            lines.append(f"Reason: {reason}")
        if dashboard_url:
            lines.append(f"Dashboard: {dashboard_url}")
        text = "\n".join(lines)

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            resp = self.client.post(url, json={"chat_id": self.chat_id, "text": text})
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


@dataclass
class FakeTelegramNotifier:
    sent: list[dict[str, str | None]] = field(default_factory=list)
    fail: bool = False

    def send_alert(
        self,
        host: str,
        workload_name: str,
        severity: str,
        reason: str | None,
        dashboard_url: str | None,
    ) -> bool:
        self.sent.append({
            "host": host,
            "workload_name": workload_name,
            "severity": severity,
            "reason": reason,
            "dashboard_url": dashboard_url,
        })
        return not self.fail
