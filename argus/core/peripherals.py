"""Peripheral detection and micro-ROS UART configuration tools."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class SerialPortInfo(BaseModel):
    device: str
    is_ttyama: bool = False
    is_ttys: bool = False
    is_usb: bool = False
    blocked_by_getty: bool = False
    blocked_by_cmdline: bool = False
    description: str


class MicroRosUartAdvice(BaseModel):
    device: str
    baudrate: int
    getty_service: str
    requires_cmdline_fix: bool
    requires_config_txt_fix: bool
    setup_script: str
    systemd_unit: str


def detect_serial_ports() -> list[dict[str, Any]]:
    """Detect available serial ports and inspect potential console conflicts."""
    results: list[SerialPortInfo] = []
    
    # Check common serial device paths
    dev_path = Path("/dev")
    candidates = ["ttyAMA0", "ttyS0"] + [p.name for p in dev_path.glob("ttyUSB*")] + [p.name for p in dev_path.glob("ttyACM*")]
    
    # Check if we are on a real Linux filesystem or macOS/test environment
    for name in sorted(set(candidates)):
        full_path = dev_path / name
        if not full_path.exists() and platform.system() == "Linux":
            continue
        
        # Check if getty is active on this tty
        blocked_by_getty = False
        getty_svc = f"serial-getty@{name}.service"
        try:
            res = subprocess.run(["systemctl", "is-active", getty_svc], capture_output=True, text=True, check=False)
            if res.stdout.strip() == "active":
                blocked_by_getty = True
        except Exception:
            pass
            
        # Check if console=ttyAMA0 or console=serial0 is in cmdline.txt
        blocked_by_cmdline = False
        cmdline_paths = ["/boot/firmware/cmdline.txt", "/boot/cmdline.txt", "/proc/cmdline"]
        for cpath in cmdline_paths:
            if Path(cpath).exists():
                try:
                    content = Path(cpath).read_text()
                    if f"console={name}" in content or ("ttyAMA0" in name and "console=serial0" in content):
                        blocked_by_cmdline = True
                        break
                except Exception:
                    pass
                    
        is_ttyama = name.startswith("ttyAMA")
        is_ttys = name.startswith("ttyS")
        is_usb = name.startswith("ttyUSB") or name.startswith("ttyACM")
        
        desc = "Raspberry Pi Hardware PL011 UART" if is_ttyama else ("Mini UART / Serial" if is_ttys else "USB Serial Device")
        
        info = SerialPortInfo(
            device=f"/dev/{name}",
            is_ttyama=is_ttyama,
            is_ttys=is_ttys,
            is_usb=is_usb,
            blocked_by_getty=blocked_by_getty,
            blocked_by_cmdline=blocked_by_cmdline,
            description=desc,
        )
        if full_path.exists() or name in ["ttyAMA0", "ttyS0"]:
            results.append(info)
            
    return [r.model_dump() for r in results]


def configure_micro_ros_uart(device: str = "/dev/ttyAMA0", baudrate: int = 115200) -> dict[str, Any]:
    """Generate configuration and setup scripts to dedicate hardware serial (/dev/ttyAMA0) to micro-ROS."""
    dev_name = device.replace("/dev/", "")
    getty_svc = f"serial-getty@{dev_name}.service"
    
    # Determine which boot files are used on Ubuntu 24.04 ARM vs Debian
    cmdline_path = "/boot/firmware/cmdline.txt"
    config_path = "/boot/firmware/config.txt"
    
    setup_script = f"""#!/bin/bash
# Argus micro-ROS UART Setup Script for {device}
# Hardware target: Raspberry Pi 4 / Ubuntu ARM64
set -euo pipefail

echo "==> 1. Disabling login console on {device} ({getty_svc})..."
if systemctl list-unit-files | grep -q "{getty_svc}"; then
    sudo systemctl disable --now "{getty_svc}" || true
    sudo systemctl mask "{getty_svc}" || true
fi

echo "==> 2. Checking and removing console serial boot arguments from {cmdline_path}..."
if [ -f "{cmdline_path}" ]; then
    sudo cp "{cmdline_path}" "{cmdline_path}.bak"
    sudo sed -i 's/console=serial0,[0-9]\\+ //g' "{cmdline_path}"
    sudo sed -i 's/console={dev_name},[0-9]\\+ //g' "{cmdline_path}"
fi

echo "==> 3. Enabling hardware UART in {config_path}..."
if [ -f "{config_path}" ]; then
    if ! grep -q "^enable_uart=1" "{config_path}"; then
        echo "enable_uart=1" | sudo tee -a "{config_path}" > /dev/null
    fi
fi

echo "==> UART {device} configured for micro-ROS at {baudrate} baud."
echo "NOTE: A reboot is recommended if boot cmdline or config.txt were modified."
"""

    systemd_unit = f"""[Unit]
Description=micro-ROS Agent (Serial UART on {device})
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/ros2 run micro_ros_agent micro_ros_agent serial --dev {device} -b {baudrate}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
"""

    advice = MicroRosUartAdvice(
        device=device,
        baudrate=baudrate,
        getty_service=getty_svc,
        requires_cmdline_fix=True,
        requires_config_txt_fix=True,
        setup_script=setup_script,
        systemd_unit=systemd_unit,
    )
    return advice.model_dump()
