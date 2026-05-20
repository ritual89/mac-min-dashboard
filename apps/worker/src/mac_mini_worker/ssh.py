"""Re-export subprocess SSH helpers from core (shared with API)."""

from mac_mini_core.ssh.subprocess import SubprocessSshExecutor, create_executor_factory

__all__ = ["SubprocessSshExecutor", "create_executor_factory"]
