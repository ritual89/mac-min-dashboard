from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from mac_mini_core.models import HostOS


class HostConfig(BaseModel):
    id: str
    display_name: str
    tailscale_host: str
    ssh_user: str
    ssh_key_path: str
    os: HostOS
    poll_interval_sec: int | None = None

    @field_validator("poll_interval_sec")
    @classmethod
    def validate_poll_interval(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if not 15 <= value <= 60:
            msg = "poll_interval_sec must be between 15 and 60 inclusive"
            raise ValueError(msg)
        return value


class PromoteRulesConfig(BaseModel):
    project_roots: list[str] = Field(default_factory=lambda: ["~/dev", "~/projects", "~/code"])
    allowlist: list[str] = Field(default_factory=lambda: ["hermes", "dashboard-for-life"])
    port_denylist: list[int] = Field(default_factory=list)


class AppConfig(BaseModel):
    default_poll_interval_sec: int = 30
    ssh_timeout_sec: int = 30
    restart_loop_threshold_1h: int = 5
    log_tail_lines: int = 200
    hosts: list[HostConfig] = Field(default_factory=list)
    promote: PromoteRulesConfig = Field(default_factory=PromoteRulesConfig)

    @field_validator("default_poll_interval_sec")
    @classmethod
    def validate_default_poll(cls, value: int) -> int:
        if not 15 <= value <= 60:
            msg = "default_poll_interval_sec must be between 15 and 60 inclusive"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_unique_host_ids(self) -> AppConfig:
        ids = [host.id for host in self.hosts]
        if len(ids) != len(set(ids)):
            msg = "duplicate host id in config"
            raise ValueError(msg)
        return self


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        raw = {}
    return AppConfig.model_validate(raw)
