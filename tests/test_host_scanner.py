"""Unit tests for argus.host.scanner."""

from __future__ import annotations

import json
from pathlib import Path
from argus.host.scanner import TargetDevice, save_targets, load_targets


def test_target_device_model():
    t = TargetDevice(
        id=0,
        hostname="armcreate-pi4",
        ip="192.168.1.43",
        soc_model="BCM2711 / Cortex-A72",
        status="ONLINE (Ready)",
        is_bootstrapped=True,
        tunnel_port=2222
    )
    assert t.id == 0
    assert t.ip == "192.168.1.43"
    assert t.tunnel_port == 2222


def test_save_and_load_targets(tmp_path, monkeypatch):
    test_file = tmp_path / "targets.json"
    monkeypatch.setattr("argus.host.scanner.get_targets_file_path", lambda: test_file)
    
    t1 = TargetDevice(id=0, hostname="pi4", ip="192.168.1.43", soc_model="Cortex-A72")
    t2 = TargetDevice(id=1, hostname="jetson", ip="192.168.1.108", soc_model="Tegra X1")
    
    save_targets([t1, t2])
    assert test_file.exists()
    
    loaded = load_targets()
    assert len(loaded) == 2
    assert loaded[0].id == 0
    assert loaded[0].ip == "192.168.1.43"
    assert loaded[1].id == 1
    assert loaded[1].ip == "192.168.1.108"
