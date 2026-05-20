from __future__ import annotations

import re
from enum import StrEnum
from typing import assert_never

from mac_mini_core.ssh.errors import CommandValidationError, UnknownCommandError

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@:/-]*$")
_LOG_DURATION_RE = re.compile(r"^\d+[smhd]$")


class CommandTemplate(StrEnum):
    DOCKER_PS = "docker_ps"
    DOCKER_INSPECT = "docker_inspect"
    DOCKER_LOGS = "docker_logs"
    DOCKER_RESTART = "docker_restart"
    SYSTEMCTL_IS_ACTIVE = "systemctl_is_active"
    SYSTEMCTL_RESTART = "systemctl_restart"
    JOURNALCTL_UNIT = "journalctl_unit"
    LAUNCHCTL_LIST = "launchctl_list"
    LAUNCHCTL_KICKSTART = "launchctl_kickstart"
    LOG_SHOW_LAST = "log_show_last"
    CRONTAB_LIST = "crontab_list"


def _validate_name(value: str, field: str) -> str:
    if not value or not _NAME_RE.fullmatch(value):
        msg = f"invalid {field}: {value!r}"
        raise CommandValidationError(msg)
    return value


def _validate_line_count(value: int, field: str) -> int:
    if value <= 0 or value > 10_000:
        msg = f"invalid {field}: must be 1..10000"
        raise CommandValidationError(msg)
    return value


def _validate_duration(value: str) -> str:
    if not _LOG_DURATION_RE.fullmatch(value):
        msg = f"invalid duration: {value!r}"
        raise CommandValidationError(msg)
    return value


def render_command(template: CommandTemplate | str, **params: object) -> str:
    try:
        cmd = CommandTemplate(template)
    except ValueError as exc:
        msg = f"unknown command template: {template!r}"
        raise UnknownCommandError(msg) from exc

    if cmd is CommandTemplate.DOCKER_PS:
        return "docker ps --format '{{json .}}'"

    if cmd is CommandTemplate.DOCKER_INSPECT:
        name = _validate_name(str(params.get("name", "")), "name")
        return f"docker inspect {name}"

    if cmd is CommandTemplate.DOCKER_LOGS:
        name = _validate_name(str(params.get("name", "")), "name")
        tail = _validate_line_count(int(params.get("n", 0)), "n")
        return f"docker logs --tail {tail} {name}"

    if cmd is CommandTemplate.DOCKER_RESTART:
        name = _validate_name(str(params.get("name", "")), "name")
        return f"docker restart {name}"

    if cmd is CommandTemplate.SYSTEMCTL_IS_ACTIVE:
        unit = _validate_name(str(params.get("unit", "")), "unit")
        return f"systemctl is-active {unit}"

    if cmd is CommandTemplate.SYSTEMCTL_RESTART:
        unit = _validate_name(str(params.get("unit", "")), "unit")
        return f"systemctl restart {unit}"

    if cmd is CommandTemplate.JOURNALCTL_UNIT:
        unit = _validate_name(str(params.get("unit", "")), "unit")
        lines = _validate_line_count(int(params.get("n", 0)), "n")
        return f"journalctl -u {unit} -n {lines} --no-pager"

    if cmd is CommandTemplate.LAUNCHCTL_LIST:
        return "launchctl list"

    if cmd is CommandTemplate.LAUNCHCTL_KICKSTART:
        label = _validate_name(str(params.get("label", "")), "label")
        return f"launchctl kickstart -k {label}"

    if cmd is CommandTemplate.LOG_SHOW_LAST:
        duration = _validate_duration(str(params.get("duration", "")))
        return f"log show --last {duration} --style compact"

    if cmd is CommandTemplate.CRONTAB_LIST:
        return "crontab -l"

    assert_never(cmd)  # pragma: no cover
