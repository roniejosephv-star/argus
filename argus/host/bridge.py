"""Bridge and tunnel controller for Argus Host CLI on Mac Mini."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from argus.host.scanner import load_targets, TargetDevice
from argus.common.logger import log_event


def resolve_target(target_id_or_ip: str) -> Optional[TargetDevice]:
    """Resolve a target ID (e.g. '0') or IP string ('192.168.1.43') to a TargetDevice."""
    targets = load_targets()
    if target_id_or_ip.isdigit():
        tid = int(target_id_or_ip)
        for t in targets:
            if t.id == tid:
                return t
    for t in targets:
        if t.ip == target_id_or_ip or t.hostname == target_id_or_ip:
            return t
    return None


def connect_target(target_id_or_ip: str = "0", tunnel_port: int = 2222) -> Dict[str, Any]:
    """Establish loopback SSH tunnel to target, lock keep-alive, and update MCP config."""
    target = resolve_target(target_id_or_ip)
    if not target:
        # Fallback for default target if no scan was performed
        if target_id_or_ip in ("0", "192.168.1.43"):
            target = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=tunnel_port)
        else:
            return {"success": False, "error": f"Target not found: {target_id_or_ip}. Run 'argus scan' first."}

    # 1. Check if tunnel is already connected and responsive
    tunnel_alive = False
    try:
        check_cmd = f"ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -p {target.tunnel_port} {target.username}@127.0.0.1 'true' 2>/dev/null"
        if subprocess.run(check_cmd, shell=True).returncode == 0:
            tunnel_alive = True
    except Exception:
        pass

    if not tunnel_alive:
        # Kill stale loopback tunnels on this port
        try:
            subprocess.run(f'pkill -f "L {target.tunnel_port}:127.0.0.1:22"', shell=True, capture_output=True)
        except Exception:
            pass

        # Spawn fresh background tunnel
        tunnel_cmd = f"ssh -o StrictHostKeyChecking=no -f -N -L {target.tunnel_port}:127.0.0.1:22 {target.username}@{target.ip}"
        res = subprocess.run(tunnel_cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to start SSH tunnel on port {target.tunnel_port}: {res.stderr.strip()}"
            }

    # 3. Lock WiFi power saving off across tunnel
    keepalive_cmd = f'ssh -o ConnectTimeout=5 -p {target.tunnel_port} {target.username}@127.0.0.1 "sudo iw wlan0 set power_save off 2>/dev/null || true"'
    subprocess.run(keepalive_cmd, shell=True, capture_output=True)

    # 4. Synchronize MCP configurations across settings files
    sync_mcp_configs(target)

    try:
        log_event("phase2_bridge", f"Bridge Connected Target [{target.id}]", status="SUCCESS", details={"ip": target.ip, "port": target.tunnel_port})
    except Exception:
        pass

    return {
        "success": True,
        "target_id": target.id,
        "hostname": target.hostname,
        "ip": target.ip,
        "tunnel_port": target.tunnel_port,
        "message": f"Bridge established for Target [{target.id}] ({target.ip}) via localhost:{target.tunnel_port}."
    }


def sync_mcp_configs(target: TargetDevice) -> None:
    """Update settings.json and global mcp_config.json to route through argus mcp-host or loopback tunnel."""
    # We configure direct loopback tunnel string as the target configuration
    mcp_server_config = {
        "command": "ssh",
        "args": [
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-p",
            str(target.tunnel_port),
            f"{target.username}@127.0.0.1",
            "/home/armcreate/Argus/.venv/bin/argus mcp --transport stdio"
        ]
    }

    # 1. Update project .gemini/settings.json
    try:
        settings_path = Path(".gemini/settings.json")
        if settings_path.exists():
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"mcpServers": {}}
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"]["argus-pi"] = mcp_server_config
        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass

    # 2. Update global ~/.gemini/config/mcp_config.json and Antigravity IDE config
    global_paths = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
    ]
    for gpath in global_paths:
        try:
            if gpath.exists():
                gdata = json.loads(gpath.read_text(encoding="utf-8"))
            else:
                gpath.parent.mkdir(parents=True, exist_ok=True)
                gdata = {"mcpServers": {}}
            if "mcpServers" not in gdata:
                gdata["mcpServers"] = {}
            gdata["mcpServers"]["argus-pi"] = mcp_server_config
            gpath.write_text(json.dumps(gdata, indent=2), encoding="utf-8")
        except Exception:
            pass


def bootstrap_target(target_id_or_ip: str = "0", repo_url: str = "https://github.com/roniejosephv-star/argus.git") -> Dict[str, Any]:
    """SSH into remote ARM device, set up venv, and install Argus."""
    target = resolve_target(target_id_or_ip)
    if not target:
        if target_id_or_ip in ("0", "192.168.1.43"):
            target = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43")
        else:
            try:
                log_event("phase2_bridge", f"Bootstrap Failed: Target {target_id_or_ip} not found", status="ERROR")
            except Exception:
                pass
            return {"success": False, "error": f"Target {target_id_or_ip} not found in registry."}

    # Connect over direct SSH or tunnel
    ssh_prefix = f"ssh -o StrictHostKeyChecking=no {target.username}@{target.ip}"
    rsync_rsh = 'ssh -o StrictHostKeyChecking=no'
    if check_target_status_tunnel(target.tunnel_port):
        ssh_prefix = f"ssh -o StrictHostKeyChecking=no -p {target.tunnel_port} {target.username}@127.0.0.1"
        rsync_rsh = f'ssh -o StrictHostKeyChecking=no -p {target.tunnel_port}'

    # 1. First attempt to rsync current local workspace directly to target to avoid git pull lockups or unpushed changes
    try:
        local_dir = Path.cwd()
        if (local_dir / "pyproject.toml").exists() and (local_dir / "argus").exists():
            rsync_cmd = f"rsync -az --delete --exclude '.venv' --exclude 'test_logs' --exclude '.git' --exclude '__pycache__' -e '{rsync_rsh}' '{local_dir}/' {target.username}@{'127.0.0.1' if '127.0.0.1' in ssh_prefix else target.ip}:~/Argus/"
            subprocess.run(rsync_cmd, shell=True, capture_output=True, timeout=15)
    except Exception:
        pass

    bootstrap_script = (
        "set -euo pipefail; "
        "mkdir -p ~/Argus; "
        "echo '==> Checking Python environment...'; "
        "python3 -m venv ~/Argus/.venv || true; "
        "if [ ! -f ~/Argus/pyproject.toml ]; then "
        f"  git clone {repo_url} ~/Argus 2>/dev/null || true; "
        "fi; "
        "echo '==> Installing Argus Target CLI...'; "
        "~/Argus/.venv/bin/pip install -q -e ~/Argus; "
        "~/Argus/.venv/bin/argus version"
    )

    res = subprocess.run(f"{ssh_prefix} '{bootstrap_script}'", shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        target.is_bootstrapped = True
        target.status = "ONLINE (Ready)"
        try:
            log_event("phase2_bridge", f"Target Bootstrapped [{target.id}] ({target.ip})", status="SUCCESS", details={"output": res.stdout.strip()})
        except Exception:
            pass
        return {
            "success": True,
            "target_id": target.id,
            "ip": target.ip,
            "output": res.stdout.strip(),
            "message": f"Successfully bootstrapped Argus inside Target [{target.id}] ({target.ip})."
        }
    else:
        try:
            log_event("phase2_bridge", f"Target Bootstrap Failed [{target.id}] ({target.ip})", status="ERROR", details={"error": res.stderr.strip() or res.stdout.strip()})
        except Exception:
            pass
        return {
            "success": False,
            "target_id": target.id,
            "ip": target.ip,
            "error": res.stderr.strip() or res.stdout.strip()
        }


def check_target_status_tunnel(port: int = 2222) -> bool:
    """Check if loopback tunnel on port is active."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False
