"""Report persistence layer."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from argus.core.models import (
    Report, ReportDiff, Lesson, HardwareSnapshot, OSSnapshot,
    ROS2Snapshot, ConfigSnapshot, PerformanceSnapshot, DiskSnapshot,
    Scorecard,
)


REPORT_DIR = Path("./argus-reports")
REPORT_DIR.mkdir(exist_ok=True)


def _fingerprint_dir(fingerprint: str) -> Path:
    short = fingerprint[:12]
    dir_path = REPORT_DIR / short
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def _lessons_path(fingerprint: str) -> Path:
    return _fingerprint_dir(fingerprint) / "lessons.json"


def save_report(report: Report) -> str:
    """Save report to disk. Returns report_id."""
    path = _fingerprint_dir(report.hardware.fingerprint) / f"{report.report_id}.json"
    path.write_text(report.model_dump_json(indent=2))
    
    # Also save lessons
    if report.lessons:
        lessons_file = _lessons_path(report.hardware.fingerprint)
        existing = []
        if lessons_file.exists():
            try:
                existing = json.loads(lessons_file.read_text())
            except Exception:
                pass
        existing.extend([l.model_dump() for l in report.lessons])
        lessons_file.write_text(json.dumps(existing, indent=2))
    
    return report.report_id


def load_report(report_id_or_path: str) -> Report | None:
    """Load report by ID (searches all fingerprints) or path."""
    path = Path(report_id_or_path)
    if path.exists():
        return Report.model_validate_json(path.read_text())
    
    # Search by ID
    for fp_dir in REPORT_DIR.iterdir():
        if not fp_dir.is_dir():
            continue
        for report_file in fp_dir.glob("*.json"):
            if report_id_or_path in report_file.stem:
                try:
                    return Report.model_validate_json(report_file.read_text())
                except Exception:
                    pass
    return None


def list_reports(fingerprint: str | None = None) -> list[dict]:
    """List all reports, optionally filtered by fingerprint."""
    reports = []
    for fp_dir in REPORT_DIR.iterdir():
        if not fp_dir.is_dir():
            continue
        if fingerprint and fp_dir.name != fingerprint[:12]:
            continue
        for report_file in fp_dir.glob("*.json"):
            try:
                report = Report.model_validate_json(report_file.read_text())
                reports.append({
                    "report_id": report.report_id,
                    "fingerprint": report.hardware.fingerprint,
                    "timestamp": report.timestamp.isoformat(),
                    "reason": report.reason,
                    "score": report.scorecard.score if report.scorecard else None,
                    "tier": report.scorecard.tier.value if report.scorecard else None,
                })
            except Exception:
                pass
    return sorted(reports, key=lambda r: r["timestamp"], reverse=True)


def latest_report(fingerprint: str) -> Report | None:
    """Get most recent report for a fingerprint."""
    reports = list_reports(fingerprint)
    if not reports:
        return None
    return load_report(reports[0]["report_id"])


def diff_reports(before: Report, after: Report) -> ReportDiff:
    """Compute structural diff between two reports."""
    diff = ReportDiff(
        report_before_id=before.report_id,
        report_after_id=after.report_id,
        timestamp_before=before.timestamp,
        timestamp_after=after.timestamp,
        fingerprint=before.hardware.fingerprint,
    )
    
    # Hardware changes
    diff.hardware_changed = before.hardware.model_dump() != after.hardware.model_dump()
    diff.os_changed = before.os.model_dump() != after.os.model_dump()
    diff.ros2_changed = before.ros2.model_dump() != after.ros2.model_dump()
    
    # Config changes
    before_configs = set(c.name for c in before.configs.files) if before.configs.files else set()
    after_configs = set(c.name for c in after.configs.files) if after.configs.files else set()
    diff.configs_added = list(after_configs - before_configs)
    diff.configs_removed = list(before_configs - after_configs)
    diff.configs_changed = diff.configs_added or diff.configs_removed
    
    # ROS 2 packages
    before_pkgs = set(before.ros2.packages) if before.ros2.packages else set()
    after_pkgs = set(after.ros2.packages) if after.ros2.packages else set()
    diff.ros2_packages_added = list(after_pkgs - before_pkgs)
    diff.ros2_packages_removed = list(before_pkgs - after_pkgs)
    
    # Performance deltas
    if before.performance and after.performance:
        if before.performance.cpu_bogo_ops_s and after.performance.cpu_bogo_ops_s:
            diff.cpu_bogo_ops_delta_pct = (
                (after.performance.cpu_bogo_ops_s - before.performance.cpu_bogo_ops_s)
                / before.performance.cpu_bogo_ops_s * 100
            )
        if before.performance.memory_copy_mbps and after.performance.memory_copy_mbps:
            diff.memory_bandwidth_delta_pct = (
                (after.performance.memory_copy_mbps - before.performance.memory_copy_mbps)
                / before.performance.memory_copy_mbps * 100
            )
        if before.performance.ram_used_kb and after.performance.ram_used_kb:
            diff.ram_usage_delta_kb = after.performance.ram_used_kb - before.performance.ram_used_kb
        if before.performance.peak_temp_c and after.performance.peak_temp_c:
            diff.temp_delta_c = after.performance.peak_temp_c - before.performance.peak_temp_c
    
    # Summary
    parts = []
    if diff.configs_added:
        parts.append(f"{len(diff.configs_added)} configs added")
    if diff.configs_removed:
        parts.append(f"{len(diff.configs_removed)} configs removed")
    if diff.cpu_bogo_ops_delta_pct is not None:
        parts.append(f"CPU {diff.cpu_bogo_ops_delta_pct:+.1f}%")
    if diff.memory_bandwidth_delta_pct is not None:
        parts.append(f"Memory BW {diff.memory_bandwidth_delta_pct:+.1f}%")
    if diff.temp_delta_c is not None:
        parts.append(f"Temp {diff.temp_delta_c:+.1f}°C")
    diff.summary = "; ".join(parts) if parts else "No significant changes"
    
    return diff