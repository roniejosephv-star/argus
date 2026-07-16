"""RAM usage sampling for processes and system."""

from __future__ import annotations

import time
from typing import Any

import psutil


def sample_ram(pid: int | None = None, interval_s: float = 1.0, duration_s: int = 10) -> dict[str, Any]:
    """Sample RAM usage over time.
    
    Args:
        pid: Process ID to sample (None = system-wide)
        interval_s: Sampling interval in seconds
        duration_s: Total duration in seconds
    
    Returns:
        Dict with samples, statistics, and system memory info
    """
    samples = []
    end_time = time.time() + duration_s
    
    if pid is not None:
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
        except psutil.NoSuchProcess:
            return {
                "error": f"Process {pid} not found",
                "pid": pid,
                "samples": [],
                "avg_rss_kb": 0,
                "peak_rss_kb": 0,
                "system_total_kb": 0,
                "system_available_kb": 0,
            }
    else:
        proc = None
        proc_name = "system"
    
    system_mem = psutil.virtual_memory()
    
    while time.time() < end_time:
        timestamp = time.time()
        
        if proc:
            try:
                mem_info = proc.memory_info()
                sample = {
                    "timestamp": timestamp,
                    "rss_kb": mem_info.rss // 1024,
                    "vms_kb": mem_info.vms // 1024,
                }
            except psutil.NoSuchProcess:
                break
        else:
            sample = {
                "timestamp": timestamp,
                "used_kb": system_mem.total // 1024 - system_mem.available // 1024,
                "available_kb": system_mem.available // 1024,
                "percent": system_mem.percent,
            }
        
        samples.append(sample)
        time.sleep(interval_s)
    
    if proc:
        rss_values = [s["rss_kb"] for s in samples]
        return {
            "pid": pid,
            "process_name": proc_name,
            "samples": samples,
            "avg_rss_kb": round(sum(rss_values) / len(rss_values), 1) if rss_values else 0,
            "peak_rss_kb": max(rss_values) if rss_values else 0,
            "system_total_kb": system_mem.total // 1024,
            "system_available_kb": system_mem.available // 1024,
        }
    else:
        used_values = [s["used_kb"] for s in samples]
        return {
            "pid": None,
            "process_name": "system",
            "samples": samples,
            "avg_used_kb": round(sum(used_values) / len(used_values), 1) if used_values else 0,
            "peak_used_kb": max(used_values) if used_values else 0,
            "system_total_kb": system_mem.total // 1024,
            "system_available_kb": system_mem.available // 1024,
        }


def get_system_memory() -> dict[str, Any]:
    """Get current system memory status."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total_kb": mem.total // 1024,
        "available_kb": mem.available // 1024,
        "used_kb": mem.used // 1024,
        "free_kb": mem.free // 1024,
        "percent": mem.percent,
        "swap_total_kb": swap.total // 1024,
        "swap_used_kb": swap.used // 1024,
        "swap_free_kb": swap.free // 1024,
    }


def get_process_memory(pid: int) -> dict[str, Any] | None:
    """Get memory info for a specific process."""
    try:
        proc = psutil.Process(pid)
        mem = proc.memory_info()
        return {
            "pid": pid,
            "name": proc.name(),
            "rss_kb": mem.rss // 1024,
            "vms_kb": mem.vms // 1024,
            "percent": proc.memory_percent(),
        }
    except psutil.NoSuchProcess:
        return None