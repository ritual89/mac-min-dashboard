from __future__ import annotations

import httpx
import pytest

from mac_mini_core.telegram import FakeTelegramNotifier, TelegramNotifier


def test_fake_notifier_records_sent() -> None:
    fake = FakeTelegramNotifier()
    result = fake.send_alert("mac-mini", "nginx", "red", "unhealthy", "http://dash")
    assert result is True
    assert len(fake.sent) == 1
    assert fake.sent[0]["host"] == "mac-mini"
    assert fake.sent[0]["severity"] == "red"


def test_fake_notifier_can_fail() -> None:
    fake = FakeTelegramNotifier(fail=True)
    result = fake.send_alert("mac-mini", "nginx", "red", None, None)
    assert result is False
    assert len(fake.sent) == 1


def test_real_notifier_sends_to_api() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"ok": True})
    )
    client = httpx.Client(transport=transport)
    notifier = TelegramNotifier(bot_token="tok123", chat_id="456", client=client)
    result = notifier.send_alert("mac-mini", "nginx", "red", "unhealthy", "http://dash")
    assert result is True


def test_real_notifier_returns_false_on_error() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(500, json={"ok": False})
    )
    client = httpx.Client(transport=transport)
    notifier = TelegramNotifier(bot_token="tok", chat_id="1", client=client)
    result = notifier.send_alert("host", "svc", "orange", None, None)
    assert result is False


def test_real_notifier_returns_false_on_network_error() -> None:
    transport = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("down")))
    client = httpx.Client(transport=transport)
    notifier = TelegramNotifier(bot_token="tok", chat_id="1", client=client)
    result = notifier.send_alert("host", "svc", "red", "reason", None)
    assert result is False


def test_real_notifier_formats_orange() -> None:
    sent_body: dict[str, object] = {}

    def capture(req: httpx.Request) -> httpx.Response:
        import json
        sent_body.update(json.loads(req.content))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(capture)
    client = httpx.Client(transport=transport)
    notifier = TelegramNotifier(bot_token="tok", chat_id="1", client=client)
    notifier.send_alert("host", "svc", "orange", "stopped", None)
    text = str(sent_body.get("text", ""))
    assert "ORANGE" in text
    assert "stopped" in text
