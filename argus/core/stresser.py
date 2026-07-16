"""CPU, memory, and thermal stress testing."""

from __future__ import annotations

import multiprocessing
import time
import threading
from typing import Any

import numpy as np
import psutil


def _cpu_worker(duration: float, results: list, idx: int) -> None:
    end_time = time.time() + duration
    ops = 0
    arr = np.random.rand(1000, 1000).astype(np.float64)
    while time.time() < end_time:
        arr = np.matmul(arr, arr.T)
        arr = np.sqrt(np.abs(arr))
        arr = arr + 1.0
        ops += 1
    results[idx] = ops


def _memory_worker(duration: float, array_size_mb: int, results: list, idx: int) -> None:
    end_time = time.time() + duration
    n = (array_size_mb * 1024 * 1024) // 8
    a = np.ones(n, dtype=np.float64) * 1.0
    b = np.ones(n, dtype=np.float64) * 2.0
    c = np.ones(n, dtype=np.float64) * 3.0
    
    copy_ops = scale_ops = add_ops = triad_ops = 0
    
    while time.time() < end_time:
        np.copyto(a, b)
        copy_ops += 1
        
        np.multiply(b, 3.0, out=a)
        scale_ops += 1
        
        np.add(b, c, out=a)
        add_ops += 1
        
        np.multiply(c, 3.0, out=a)
        np.add(b, a, out=a)
        triad_ops += 1
    
    results[idx] = (copy_ops, scale_ops, add_ops, triad_ops)


def stress_cpu(duration_s: int = 10, workers: int | None = None) -> dict[str, Any]:
    if workers is None:
        workers = multiprocessing.cpu_count()
    workers = min(workers, multiprocessing.cpu_count())
    
    ctx = multiprocessing.get_context("spawn")
    manager = ctx.Manager()
    results = manager.list([0] * workers)
    processes = []
    
    start_time = time.time()
    for i in range(workers):
        p = ctx.Process(target=_cpu_worker, args=(duration_s, results, i))
        processes.append(p)
        p.start()
    
    thermal_samples = []
    peak_temp = None
    thermal_throttled = False
    
    def thermal_monitor():
        nonlocal peak_temp, thermal_throttled
        end_time = time.time() + duration_s
        while time.time() < end_time:
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            thermal_samples.append({
                                "timestamp": time.time() - start_time,
                                "sensor": name,
                                "temp_c": entry.current
                            })
                            if peak_temp is None or entry.current > peak_temp:
                                peak_temp = entry.current
                            if entry.current > 80:
                                thermal_throttled = True
            except Exception:
                pass
            time.sleep(1.0)
    
    monitor_thread = threading.Thread(target=thermal_monitor)
    monitor_thread.start()
    
    for p in processes:
        p.join()
    
    monitor_thread.join(timeout=2)
    
    elapsed = time.time() - start_time
    total_ops = sum(results)
    bogo_ops_s = total_ops / elapsed if elapsed > 0 else 0
    
    avg_temp = None
    if thermal_samples:
        avg_temp = sum(s["temp_c"] for s in thermal_samples) / len(thermal_samples)
    
    return {
        "bogo_ops_s": round(bogo_ops_s, 1),
        "avg_temp_c": round(avg_temp, 1) if avg_temp else None,
        "peak_temp_c": round(peak_temp, 1) if peak_temp else None,
        "thermal_throttled": thermal_throttled,
        "workers": workers,
        "duration_s": duration_s,
        "samples": thermal_samples[-100:],
    }


def stress_memory(duration_s: int = 10, array_size_mb: int = 256) -> dict[str, Any]:
    avail_mb = psutil.virtual_memory().available // (1024 * 1024)
    max_array_mb = max(64, avail_mb // 2)
    array_size_mb = min(array_size_mb, max_array_mb)
    
    workers = min(2, multiprocessing.cpu_count())
    
    ctx = multiprocessing.get_context("spawn")
    manager = ctx.Manager()
    results = manager.list([None] * workers)
    processes = []
    
    start_time = time.time()
    for i in range(workers):
        p = ctx.Process(target=_memory_worker, args=(duration_s, array_size_mb, results, i))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    elapsed = time.time() - start_time
    
    total_copy = total_scale = total_add = total_triad = 0
    for r in results:
        if r:
            c, s, a, t = r
            total_copy += c
            total_scale += s
            total_add += a
            total_triad += t
    
    bytes_per_op = array_size_mb * 1024 * 1024
    
    copy_mbps = (total_copy * bytes_per_op * 2) / (elapsed * 1024 * 1024) * workers
    scale_mbps = (total_scale * bytes_per_op * 2) / (elapsed * 1024 * 1024) * workers
    add_mbps = (total_add * bytes_per_op * 3) / (elapsed * 1024 * 1024) * workers
    triad_mbps = (total_triad * bytes_per_op * 3) / (elapsed * 1024 * 1024) * workers
    
    return {
        "copy_mbps": round(copy_mbps, 1),
        "scale_mbps": round(scale_mbps, 1),
        "add_mbps": round(add_mbps, 1),
        "triad_mbps": round(triad_mbps, 1),
        "array_size_mb": array_size_mb,
        "duration_s": duration_s,
        "workers": workers,
    }


def stress_thermal(duration_s: int = 30) -> dict[str, Any]:
    import threading
    
    cpu_result = {}
    mem_result = {}
    thermal_samples = []
    peak_temp = None
    thermal_throttled = False
    
    def run_cpu():
        cpu_result.update(stress_cpu(duration_s, workers=multiprocessing.cpu_count()))
    
    def run_mem():
        mem_result.update(stress_memory(duration_s, array_size_mb=128))
    
    def monitor_thermal():
        nonlocal peak_temp, thermal_throttled
        end_time = time.time() + duration_s
        while time.time() < end_time:
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            thermal_samples.append({
                                "timestamp": time.time(),
                                "sensor": name,
                                "temp_c": entry.current
                            })
                            if peak_temp is None or entry.current > peak_temp:
                                peak_temp = entry.current
                            if entry.current > 80:
                                thermal_throttled = True
            except Exception:
                pass
            time.sleep(1.0)
    
    threads = [
        threading.Thread(target=run_cpu),
        threading.Thread(target=run_mem),
        threading.Thread(target=monitor_thermal),
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=duration_s + 5)
    
    avg_temp = None
    if thermal_samples:
        avg_temp = sum(s["temp_c"] for s in thermal_samples) / len(thermal_samples)
    
    return {
        "cpu_bogo_ops_s": cpu_result.get("bogo_ops_s"),
        "memory_copy_mbps": mem_result.get("copy_mbps"),
        "memory_scale_mbps": mem_result.get("scale_mbps"),
        "memory_add_mbps": mem_result.get("add_mbps"),
        "memory_triad_mbps": mem_result.get("triad_mbps"),
        "peak_temp_c": round(peak_temp, 1) if peak_temp else None,
        "avg_temp_c": round(avg_temp, 1) if avg_temp else None,
        "thermal_throttled": thermal_throttled,
        "duration_s": duration_s,
        "thermal_samples": thermal_samples[-100:],
    }


def measure_thermal() -> dict[str, Any]:
    try:
        temps = psutil.sensors_temperatures()
        sensors = []
        current_temp = None
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None:
                    sensors.append({
                        "name": f"{name}:{entry.label or 'core'}",
                        "temp_c": entry.current
                    })
                    if current_temp is None or entry.current > current_temp:
                        current_temp = entry.current
        
        return {
            "temp_c": round(current_temp, 1) if current_temp else None,
            "sensor_count": len(sensors),
            "sensors": sensors,
        }
    except Exception:
        return {
            "temp_c": None,
            "sensor_count": 0,
            "sensors": [],
        }