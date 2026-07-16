"""Unit and integration tests for Argus Bridge and Scanner diagnostics logging (`phase2_bridge.log`)."""

import json
from pathlib import Path
from unittest.mock import patch
from argus.host.scanner import TargetDevice, scan_network, check_target_status
from argus.host.bridge import connect_target, bootstrap_target, resolve_target
from argus.common import ArgusLogger


def test_bridge_resolve_target(tmp_path: Path):
    with patch("argus.host.bridge.load_targets") as mock_load:
        mock_load.return_value = [
            TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=2222)
        ]
        target = resolve_target("0")
        assert target is not None
        assert target.hostname == "armcreate-pi4"
        assert target.tunnel_port == 2222


def test_scan_network_logging(tmp_path: Path):
    logger = ArgusLogger.get_instance(log_dir=tmp_path)
    logger.clear_phase_logs("phase2_bridge")

    with patch("argus.host.scanner.check_target_status") as mock_check, \
         patch("argus.host.scanner.save_targets"):
        mock_check.return_value = ("ONLINE (Ready)", "BCM2711 / Cortex-A72", True)
        targets = scan_network(subnet="192.168.1.0/24", known_ips=["192.168.1.100"])

        assert len(targets) == 2
        assert targets[0].ip == "192.168.1.100"
        assert targets[0].soc_model == "BCM2711 / Cortex-A72"

        logs = logger.get_phase_logs("phase2_bridge")
        assert len(logs) >= 1
        scan_logs = [l for l in logs if "Network Scan Completed" in l["event"]]
        assert len(scan_logs) == 1
        assert scan_logs[0]["details"]["discovered"] == 2


def test_connect_target_logging(tmp_path: Path):
    logger = ArgusLogger.get_instance(log_dir=tmp_path)
    logger.clear_phase_logs("phase2_bridge")

    with patch("argus.host.bridge.resolve_target") as mock_resolve, \
         patch("subprocess.run") as mock_run, \
         patch("argus.host.bridge.sync_mcp_configs"):
        mock_resolve.return_value = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=2222)
        mock_run.return_value.returncode = 0

        res = connect_target("0")
        assert res["success"] is True

        logs = logger.get_phase_logs("phase2_bridge")
        connect_logs = [l for l in logs if "Bridge Connected Target [0]" in l["event"]]
        assert len(connect_logs) == 1
        assert connect_logs[0]["details"]["port"] == 2222
