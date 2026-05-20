from __future__ import annotations

from pathlib import Path

import pytest

from mac_mini_core.config import AppConfig, HostConfig, load_config


# AC-1.1: valid config loads hosts
def test_ac_1_1_valid_config_loads_hosts(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
hosts:
  - id: mac-mini
    display_name: Mac Mini Hub
    tailscale_host: mac-mini
    ssh_user: deploy
    ssh_key_path: ~/.ssh/id_ed25519
    os: darwin
    poll_interval_sec: 30
default_poll_interval_sec: 30
"""
    )
    config = load_config(config_file)
    assert len(config.hosts) == 1
    assert config.hosts[0].id == "mac-mini"
    assert config.hosts[0].os.value == "darwin"


# AC-1.2: poll interval out of range rejected
@pytest.mark.parametrize("poll_value", [14, 61, 0])
def test_ac_1_2_poll_interval_out_of_range_rejected(poll_value: int) -> None:
    with pytest.raises(ValueError, match="poll_interval_sec"):
        AppConfig(
            hosts=[
                {
                    "id": "h1",
                    "display_name": "Host",
                    "tailscale_host": "h1",
                    "ssh_user": "u",
                    "ssh_key_path": "~/.ssh/id",
                    "os": "linux",
                    "poll_interval_sec": poll_value,
                }
            ]
        )


# AC-1.3: missing required host field rejected
def test_ac_1_3_missing_required_host_field_rejected() -> None:
    with pytest.raises(ValueError):
        AppConfig(hosts=[{"id": "h1", "display_name": "Host"}])


# AC-1.4: invalid os rejected
def test_ac_1_4_invalid_os_rejected() -> None:
    with pytest.raises(ValueError):
        AppConfig(
            hosts=[
                {
                    "id": "h1",
                    "display_name": "Host",
                    "tailscale_host": "h1",
                    "ssh_user": "u",
                    "ssh_key_path": "~/.ssh/id",
                    "os": "windows",
                }
            ]
        )


# EC-1.1: empty hosts list valid
def test_ec_1_1_empty_hosts_list_valid() -> None:
    config = AppConfig()
    assert config.hosts == []


def test_host_poll_interval_none_allowed() -> None:
    config = AppConfig(
        hosts=[
            {
                "id": "h1",
                "display_name": "Host",
                "tailscale_host": "h1",
                "ssh_user": "u",
                "ssh_key_path": "~/.ssh/id",
                "os": "linux",
            }
        ]
    )
    assert config.hosts[0].poll_interval_sec is None

    host = HostConfig(
        id="h2",
        display_name="Host 2",
        tailscale_host="h2",
        ssh_user="u",
        ssh_key_path="~/.ssh/id",
        os="linux",
        poll_interval_sec=None,
    )
    assert host.poll_interval_sec is None


def test_default_poll_interval_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="default_poll_interval_sec"):
        AppConfig(default_poll_interval_sec=10)


def test_load_config_empty_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")
    config = load_config(config_file)
    assert config.hosts == []


# EC-1.2: duplicate host ids rejected
def test_ec_1_2_duplicate_host_ids_rejected() -> None:
    host = {
        "id": "dup",
        "display_name": "Host",
        "tailscale_host": "h1",
        "ssh_user": "u",
        "ssh_key_path": "~/.ssh/id",
        "os": "linux",
    }
    with pytest.raises(ValueError, match="duplicate host id"):
        AppConfig(hosts=[host, host])
