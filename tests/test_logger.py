"""Unit tests for Argus structured diagnostics logger."""

import json
from pathlib import Path
from argus.common import ArgusLogger, log_event, get_phase_logs, clear_phase_logs


def test_logger_singleton(tmp_path: Path):
    logger1 = ArgusLogger.get_instance(log_dir=tmp_path)
    logger2 = ArgusLogger.get_instance(log_dir=tmp_path)
    assert logger1 is logger2


def test_log_event_and_retrieval(tmp_path: Path):
    logger = ArgusLogger(log_dir=tmp_path)
    payload = logger.log_event(
        phase="phase1_derivation",
        event="SoC Detection Started",
        status="SUCCESS",
        details={"model": "Apple M3 Max", "cores": 16},
        target_id="Host",
    )

    assert payload["event"] == "SoC Detection Started"
    assert payload["status"] == "SUCCESS"
    assert payload["details"]["model"] == "Apple M3 Max"

    logs = logger.get_phase_logs("phase1_derivation")
    assert len(logs) == 1
    assert logs[0]["event"] == "SoC Detection Started"
    assert logs[0]["target_id"] == "Host"


def test_clear_logs(tmp_path: Path):
    logger = ArgusLogger(log_dir=tmp_path)
    logger.log_event(phase="phase2_bridge", event="Tunnel Connected", status="OK")
    assert len(logger.get_phase_logs("phase2_bridge")) == 1

    logger.clear_phase_logs("phase2_bridge")
    assert len(logger.get_phase_logs("phase2_bridge")) == 0
