from __future__ import annotations

from mac_mini_core.models import HostOS

# Non-interactive SSH often omits Homebrew; Colima/Docker CLI live under /opt/homebrew/bin.
_DARWIN_PATH = 'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"; '
_LINUX_PATH = 'export PATH="/usr/local/bin:/snap/bin:$PATH"; '


def wrap_remote_command(command: str, os: HostOS) -> str:
    if os is HostOS.DARWIN:
        return f"{_DARWIN_PATH}{command}"
    if os is HostOS.LINUX:
        return f"{_LINUX_PATH}{command}"
    return command  # pragma: no cover — HostOS is darwin|linux only
