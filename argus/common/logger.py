"""Structured multi-phase diagnostic logger (`ArgusLogger`) for Argus Control Plane.

Outputs JSON Lines (`JSONL`) and human-readable summaries to `test_logs/` across all phases:
- `phase1_derivation`: Hardware SoC, RAM, OS kernel, and dynamic banner checks.
- `phase2_bridge`: Network scanning (`scan`), loopback tunnel status (`localhost:2222`), `rsync`, and `bootstrap`.
- `phase3_ros2`: ROS 2 environment discovery, package creation (`argus ros create`), and `colcon build`.
- `phase4_application`: Node execution (`argus ros launch`) and topic publishing (`argus ros pub`).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ArgusLogger:
    """Universal structured diagnostics logger for Argus."""

    _instance: Optional["ArgusLogger"] = None
    _lock = threading.Lock()

    def __init__(self, log_dir: Optional[Union[str, Path]] = None):
        if log_dir is None:
            # Check if running inside local development workspace or installed globally
            workspace_root = Path.cwd()
            if (workspace_root / "pyproject.toml").exists() and (workspace_root / "argus").exists():
                self.log_dir = workspace_root / "test_logs"
            else:
                self.log_dir = Path.home() / ".argus" / "test_logs"
        else:
            self.log_dir = Path(log_dir)

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback to /tmp if home or workspace isn't writable
            self.log_dir = Path("/tmp") / "argus_test_logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self._file_locks: Dict[str, threading.Lock] = {}

    @classmethod
    def get_instance(cls, log_dir: Optional[Union[str, Path]] = None) -> "ArgusLogger":
        """Get or initialize singleton instance of ArgusLogger."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(log_dir=log_dir)
            return cls._instance

    def _get_lock_for_phase(self, phase: str) -> threading.Lock:
        with self._lock:
            if phase not in self._file_locks:
                self._file_locks[phase] = threading.Lock()
            return self._file_locks[phase]

    def _normalize_phase(self, phase: str) -> str:
        clean = phase.lower().strip()
        if not clean.endswith(".log"):
            if not clean.startswith("phase") and not clean in ("telemetry", "system", "bridge", "ros2", "application"):
                clean = f"{clean}"
            clean = f"{clean}.log"
        return clean

    def log_event(
        self,
        phase: str,
        event: str,
        status: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
        target_id: str = "Host",
    ) -> Dict[str, Any]:
        """Record a structured log entry into the specified phase log file (`JSONL` format)."""
        filename = self._normalize_phase(phase)
        log_file = self.log_dir / filename
        lock = self._get_lock_for_phase(filename)

        timestamp_iso = datetime.now(timezone.utc).isoformat()
        timestamp_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        payload = {
            "timestamp": timestamp_iso,
            "timestamp_human": timestamp_human,
            "phase": phase.replace(".log", ""),
            "target_id": target_id,
            "event": event,
            "status": status.upper(),
            "details": details or {},
        }

        jsonl_line = json.dumps(payload, default=str) + "\n"

        with lock:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(jsonl_line)
            except Exception as e:
                print(f"[ArgusLogger Error] Could not write to {log_file}: {e}", file=sys.stderr)

        return payload

    def get_phase_logs(self, phase: str, lines: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent structured log entries for the specified phase."""
        filename = self._normalize_phase(phase)
        log_file = self.log_dir / filename
        lock = self._get_lock_for_phase(filename)

        if not log_file.exists():
            return []

        entries = []
        with lock:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    raw_lines = f.readlines()
                    for line in raw_lines[-lines:]:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            # If non-JSON line exists, wrap it
                            entries.append({
                                "timestamp": "",
                                "event": line,
                                "status": "RAW",
                                "details": {},
                            })
            except Exception as e:
                entries.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": f"Error reading log file {log_file}: {e}",
                    "status": "ERROR",
                    "details": {},
                })

        return entries

    def clear_phase_logs(self, phase: Optional[str] = None) -> bool:
        """Clear specific phase log or all logs in `test_logs/` directory."""
        if phase:
            filename = self._normalize_phase(phase)
            log_file = self.log_dir / filename
            lock = self._get_lock_for_phase(filename)
            with lock:
                try:
                    if log_file.exists():
                        log_file.unlink()
                    return True
                except Exception as e:
                    print(f"[ArgusLogger Error] Could not clear {log_file}: {e}", file=sys.stderr)
                    return False
        else:
            with self._lock:
                try:
                    for item in self.log_dir.glob("*.log"):
                        try:
                            item.unlink()
                        except Exception:
                            pass
                    return True
                except Exception as e:
                    print(f"[ArgusLogger Error] Could not clear directory {self.log_dir}: {e}", file=sys.stderr)
                    return False


# Global helper shortcuts
def get_logger(log_dir: Optional[Union[str, Path]] = None) -> ArgusLogger:
    return ArgusLogger.get_instance(log_dir=log_dir)


def log_event(
    phase: str,
    event: str,
    status: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
    target_id: str = "Host",
) -> Dict[str, Any]:
    return get_logger().log_event(phase=phase, event=event, status=status, details=details, target_id=target_id)


def get_phase_logs(phase: str, lines: int = 50) -> List[Dict[str, Any]]:
    return get_logger().get_phase_logs(phase=phase, lines=lines)


def clear_phase_logs(phase: Optional[str] = None) -> bool:
    return get_logger().clear_phase_logs(phase=phase)
