from __future__ import annotations

from mac_mini_core.models import HostOS
from mac_mini_core.ssh.shell import wrap_remote_command


# AC-2.7
def test_ac_2_7_wraps_darwin_command_with_homebrew_path() -> None:
    remote = wrap_remote_command("docker ps", HostOS.DARWIN)
    assert remote.startswith('export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"; ')
    assert remote.endswith("docker ps")


# AC-2.7
def test_ac_2_7_wraps_linux_command_with_standard_path() -> None:
    remote = wrap_remote_command("docker ps", HostOS.LINUX)
    assert remote.startswith('export PATH="/usr/local/bin:/snap/bin:$PATH"; ')
    assert remote.endswith("docker ps")
