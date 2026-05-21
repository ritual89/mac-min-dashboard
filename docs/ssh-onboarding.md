# SSH Onboarding — Mac Mini Fleet Dashboard

Set up SSH access from the hub (Mac Mini) to each fleet host.

## Prerequisites

- Hub and target host on the same Tailscale network
- `sshd` running on the target host

## Per-host checklist

### 1. Create a dedicated user on the target

```bash
# Linux
sudo adduser --system --group --shell /bin/bash dashboard

# macOS
sudo sysadminctl -addUser dashboard -shell /bin/bash
```

### 2. Generate an SSH key on the hub (one-time)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dashboard_ed25519 -N ""
```

### 3. Copy the public key to the target

```bash
ssh-copy-id -i ~/.ssh/dashboard_ed25519.pub dashboard@<tailscale-host>
```

### 4. Verify passwordless SSH

```bash
ssh -i ~/.ssh/dashboard_ed25519 dashboard@<tailscale-host> "echo ok"
```

### 5. Grant Docker access (Linux targets)

```bash
# On the target host
sudo usermod -aG docker dashboard
```

### 6. Grant systemctl access (Linux targets, optional)

If the dashboard user needs to restart/stop systemd units:

```bash
# /etc/sudoers.d/dashboard
dashboard ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *, /usr/bin/systemctl stop *
```

### 7. Add host to config.yaml

```yaml
hosts:
  - id: vultr-1
    display_name: "Vultr VPS 1"
    tailscale_host: vultr-1
    ssh_user: dashboard
    ssh_key_path: ~/.ssh/dashboard_ed25519
    os: linux
```

### 8. Test from the dashboard

```bash
cd ~/dev/mac-mini-dashboard
uv run python -c "
from mac_mini_core.config import load_config
from mac_mini_core.ssh.subprocess import SubprocessSshExecutor
from mac_mini_core.ssh.commands import CommandTemplate

config = load_config('config/config.yaml')
host = config.hosts[0]
executor = SubprocessSshExecutor(host=host.tailscale_host, user=host.ssh_user, key_path=host.ssh_key_path)
result = executor.execute(CommandTemplate.DOCKER_PS)
print(result.stdout[:200])
"
```

## Security notes

- Use a dedicated `dashboard` user with minimal permissions
- Never use root for SSH access
- Docker group membership is required for container inspection (Linux)
- `ssh_key_path` in config.yaml points to the private key on the hub
- All SSH commands are allowlisted — no arbitrary command execution
