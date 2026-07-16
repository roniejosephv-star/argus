"""Network and target scanner for Argus Host CLI on Mac Mini."""

from __future__ import annotations

import json
import socket
import subprocess
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from argus.common.logger import log_event


class TargetDevice(BaseModel):
    """Represents a discovered hardware target on the local network."""
    id: int = Field(description="Unique numeric index of the target (e.g. 0)")
    hostname: str = Field(description="Hostname or device identifier")
    ip: str = Field(description="IPv4 or IPv6 network address")
    soc_model: str = Field(default="Unknown ARM SoC", description="Detected CPU/SoC model")
    arch: str = Field(default="aarch64", description="CPU architecture")
    status: str = Field(default="DISCOVERED", description="Status: ONLINE, DISCOVERED, UNBOOTSTRAPPED, OFFLINE")
    username: str = Field(default="armcreate", description="Default SSH login username")
    port: int = Field(default=22, description="SSH port")
    is_bootstrapped: bool = Field(default=False, description="Whether Argus Target CLI is installed")
    tunnel_port: int = Field(default=2222, description="Local loopback forwarding port")


def get_targets_file_path() -> Path:
    """Return the absolute path to ~/.argus/targets.json."""
    argus_dir = Path.home() / ".argus"
    argus_dir.mkdir(parents=True, exist_ok=True)
    return argus_dir / "targets.json"


def load_targets() -> List[TargetDevice]:
    """Load cached targets from ~/.argus/targets.json."""
    path = get_targets_file_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [TargetDevice(**item) for item in data]
        if isinstance(data, dict) and "targets" in data:
            return [TargetDevice(**item) for item in data["targets"]]
    except Exception:
        pass
    return []


def save_targets(targets: List[TargetDevice]) -> None:
    """Save target registry to ~/.argus/targets.json."""
    path = get_targets_file_path()
    data = {"targets": [t.model_dump() for t in targets]}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def check_ssh_port(ip: str, port: int = 22, timeout: float = 0.5) -> bool:
    """Check if TCP port is reachable."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def check_target_status(ip: str, username: str = "armcreate", port: int = 22, tunnel_port: Optional[int] = 2222) -> tuple[str, str, bool]:
    """Inspect target over SSH to detect SoC and check if Argus is installed."""
    connect_ip = ip
    connect_port = port
    
    # Check if direct port is reachable, or fallback to loopback tunnel if active (bypass macOS App Sandbox)
    if not check_ssh_port(connect_ip, connect_port):
        if tunnel_port and check_ssh_port("127.0.0.1", tunnel_port):
            connect_ip = "127.0.0.1"
            connect_port = tunnel_port
        else:
            return ("OFFLINE", "Unknown ARM SoC", False)
    
    cmd = (
        f"ssh -o BatchMode=yes -o ConnectTimeout=2 -o StrictHostKeyChecking=no -p {connect_port} {username}@{connect_ip} "
        "'python3 -c \"import platform; print(platform.machine())\" 2>/dev/null; "
        "if [ -f ~/Argus/.venv/bin/argus ]; then echo \"BOOTSTRAPPED\"; else echo \"UNBOOTSTRAPPED\"; fi'"
    )
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=4)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
            arch = lines[0] if len(lines) > 0 else "aarch64"
            status_line = lines[1] if len(lines) > 1 else "UNBOOTSTRAPPED"
            is_bootstrapped = (status_line == "BOOTSTRAPPED")
            status = "ONLINE (Ready)" if is_bootstrapped else "ONLINE (Needs Bootstrap)"
            soc = "BCM2711 / Cortex-A72" if "aarch" in arch.lower() or "arm" in arch.lower() else "ARM SoC"
            try:
                log_event("phase2_bridge", f"Target Probe {connect_ip}:{connect_port}", status="SUCCESS", details={"status": status, "soc": soc, "bootstrapped": is_bootstrapped})
            except Exception:
                pass
            return (status, soc, is_bootstrapped)
    except Exception as e:
        try:
            log_event("phase2_bridge", f"Target Probe Failed {connect_ip}:{connect_port}", status="ERROR", details={"error": str(e)})
        except Exception:
            pass
    return ("DISCOVERED (Auth/Key required)", "ARM Target", False)


def scan_network(subnet: str = "192.168.1.0/24", known_ips: Optional[List[str]] = None) -> List[TargetDevice]:
    """Scan local network and known targets to discover ARM edge devices."""
    targets = []
    seen_ips = set()
    
    # 1. First include existing cached IPs to preserve ID mapping if possible
    existing = load_targets()
    id_map = {t.ip: t.id for t in existing}
    next_id = max(id_map.values(), default=-1) + 1
    
    ips_to_check = known_ips or ["192.168.1.43"]
    for t in existing:
        if t.ip not in ips_to_check:
            ips_to_check.append(t.ip)
            
    # Also inspect local ARP table (`arp -a`) on macOS for known Raspberry Pi MAC OUIs (e.g., d8:3a:dd, b8:27:eb, e4:5f:01)
    try:
        arp_res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=3)
        for line in arp_res.stdout.splitlines():
            if "(" in line and ")" in line:
                ip_part = line.split("(")[1].split(")")[0]
                if ip_part.startswith("192.168.") or ip_part.startswith("10.") or ip_part.startswith("172."):
                    if "d8:3a:dd" in line.lower() or "b8:27:eb" in line.lower() or "e4:5f:01" in line.lower() or "dc:a6:32" in line.lower():
                        if ip_part not in ips_to_check:
                            ips_to_check.append(ip_part)
    except Exception:
        pass

    for ip in ips_to_check:
        if ip in seen_ips:
            continue
        seen_ips.add(ip)
        status, soc, is_bootstrapped = check_target_status(ip)
        if status != "OFFLINE":
            tid = id_map.get(ip, next_id)
            if tid == next_id:
                next_id += 1
            hostname = "armcreate-pi4" if ip == "192.168.1.43" else f"arm-target-{tid}"
            targets.append(
                TargetDevice(
                    id=tid,
                    hostname=hostname,
                    ip=ip,
                    soc_model=soc,
                    status=status,
                    is_bootstrapped=is_bootstrapped,
                    tunnel_port=2222 + tid
                )
            )
            
    # Sort by ID
    targets.sort(key=lambda x: x.id)
    save_targets(targets)
    try:
        log_event("phase2_bridge", f"Network Scan Completed ({subnet})", status="SUCCESS", details={"discovered": len(targets), "ips": [t.ip for t in targets]})
    except Exception:
        pass
    return targets
