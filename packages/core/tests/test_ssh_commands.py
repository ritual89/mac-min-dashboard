from __future__ import annotations

import pytest

from mac_mini_core.ssh.commands import CommandTemplate, render_command
from mac_mini_core.ssh.errors import CommandValidationError, UnknownCommandError


@pytest.mark.parametrize(
    ("template", "params", "expected"),
    [
        (CommandTemplate.DOCKER_PS, {}, "docker ps --format '{{json .}}'"),
        (CommandTemplate.DOCKER_INSPECT, {"name": "web"}, "docker inspect web"),
        (CommandTemplate.DOCKER_LOGS, {"name": "web", "n": 200}, "docker logs --tail 200 web"),
        (CommandTemplate.DOCKER_RESTART, {"name": "web"}, "docker restart web"),
        (CommandTemplate.DOCKER_STOP, {"name": "web"}, "docker stop web"),
        (CommandTemplate.SYSTEMCTL_LIST_UNITS, {}, "systemctl list-units --type=service --state=running --no-pager --plain"),
        (CommandTemplate.SYSTEMCTL_IS_ACTIVE, {"unit": "nginx.service"}, "systemctl is-active nginx.service"),
        (CommandTemplate.SYSTEMCTL_RESTART, {"unit": "nginx.service"}, "systemctl restart nginx.service"),
        (CommandTemplate.SYSTEMCTL_STOP, {"unit": "nginx.service"}, "systemctl stop nginx.service"),
        (
            CommandTemplate.JOURNALCTL_UNIT,
            {"unit": "nginx.service", "n": 100},
            "journalctl -u nginx.service -n 100 --no-pager",
        ),
        (CommandTemplate.LAUNCHCTL_LIST, {}, "launchctl list"),
        (CommandTemplate.LAUNCHCTL_KICKSTART, {"label": "com.example.app"}, "launchctl kickstart -k com.example.app"),
        (CommandTemplate.LOG_SHOW_LAST, {"duration": "5m"}, "/usr/bin/log show --last 5m --style compact"),
        (CommandTemplate.CRONTAB_LIST, {}, "crontab -l"),
    ],
)
def test_ac_2_1_allowlisted_templates_render(
    template: CommandTemplate,
    params: dict[str, object],
    expected: str,
) -> None:
    assert render_command(template, **params) == expected


@pytest.mark.parametrize(
    "bad_value",
    ["web;rm", "web|cat", "web`id`", "web$name", "web&", "web<file"],
)
def test_ac_2_2_shell_metacharacters_rejected(bad_value: str) -> None:
    with pytest.raises(CommandValidationError):
        render_command(CommandTemplate.DOCKER_INSPECT, name=bad_value)


def test_ac_2_3_unknown_template_rejected() -> None:
    with pytest.raises(UnknownCommandError):
        render_command("rm_rf_everything")


def test_ec_2_1_empty_name_rejected() -> None:
    with pytest.raises(CommandValidationError):
        render_command(CommandTemplate.DOCKER_INSPECT, name="")


@pytest.mark.parametrize("bad_n", [0, -1, 10001])
def test_ec_2_2_invalid_line_count_rejected(bad_n: int) -> None:
    with pytest.raises(CommandValidationError):
        render_command(CommandTemplate.DOCKER_LOGS, name="web", n=bad_n)


@pytest.mark.parametrize("bad_duration", ["5", "5x", ""])
def test_ec_2_3_invalid_log_duration_rejected(bad_duration: str) -> None:
    with pytest.raises(CommandValidationError):
        render_command(CommandTemplate.LOG_SHOW_LAST, duration=bad_duration)
