from __future__ import annotations


class SshError(Exception):
    """Base SSH layer error."""


class UnknownCommandError(SshError):
    """Raised when a command template id is not allowlisted."""


class CommandValidationError(SshError):
    """Raised when template parameters fail validation."""


class SshExecutionError(SshError):
    """Raised when SSH execution fails after retries."""
