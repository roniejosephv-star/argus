import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil

from argus.core.models import HardwareProfile


def detect_arm_soc(detailed: bool = False) -> HardwareProfile:
    """Detect Arm SoC capabilities. Delegates to platform-specific backend."""
    system = sys.platform
    if system == "darwin":
        return _detect_macos(detailed)
    elif system == "linux":
        return _detect_linux(detailed)
    else:
        raise NotImplementedError(f"Platform {system} not supported")


def _detect_macos(detailed: bool = False) -> HardwareProfile:
    """macOS hardware detection via sysctl."""
    def sysctl(key: str) -> str:
        try:
            result = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=False)
            return result.stdout.strip()
        except Exception:
            return ""

    # Basic info
    brand = sysctl("machdep.cpu.brand_string")
    model = brand or "Apple Silicon"
    total_cores = int(sysctl("hw.ncpu") or "0")
    
    # P/E cores (Apple Silicon)
    p_cores = int(sysctl("hw.perflevel0.logicalcpu") or "0")
    e_cores = int(sysctl("hw.perflevel1.logicalcpu") or "0")
    if p_cores == 0 and e_cores == 0:
        p_cores = total_cores

    # Memory
    mem_bytes = int(sysctl("hw.memsize") or "0")
    total_ram_gb = mem_bytes / (1024**3)
    available_ram_gb = psutil.virtual_memory().available / (1024**3)

    # Cache
    cache_line = int(sysctl("hw.cachelinesize") or "128")
    l1d = sysctl("hw.l1dcachesize")
    l2 = sysctl("hw.l2cachesize")
    l3 = sysctl("hw.l3cachesize") if detailed else None

    # ISA features
    neon = sysctl("hw.optional.neon") == "1"
    lse = sysctl("hw.optional.arm.FEAT_LSE") == "1"

    # Compiler target
    compiler_target = _map_apple_model_to_target(brand)

    # Fingerprint
    fingerprint = compute_fingerprint({
        "implementer": "Apple",
        "part": compiler_target,
        "total_ram_kb": int(total_ram_gb * 1024 * 1024),
        "board_model": sysctl("hw.model"),
        "cache_line_size": cache_line,
    })

    return HardwareProfile(
        os="darwin",
        arch="arm64",
        model=model,
        p_cores=p_cores,
        e_cores=e_cores,
        total_cores=total_cores,
        total_ram_gb=round(total_ram_gb, 1),
        available_ram_gb=round(available_ram_gb, 1),
        neon=neon,
        lse=lse,
        cache_line_size=cache_line,
        l1d_cache=f"{int(l1d)/1024:.0f}KB" if l1d else None,
        l2_cache=f"{int(l2)/1024/1024:.0f}MB" if l2 else None,
        l3_cache=f"{int(l3)/1024/1024:.0f}MB" if l3 else None,
        has_preempt_rt=False,
        compiler_target=compiler_target,
        fingerprint=fingerprint,
    )


def _detect_linux(detailed: bool = False) -> HardwareProfile:
    """Linux hardware detection via /proc, /sys, psutil."""
    # CPU info from /proc/cpuinfo
    cpuinfo = _parse_cpuinfo()
    
    # Board model
    board_model = _read_first_line("/proc/device-tree/model") or _read_first_line("/sys/firmware/devicetree/base/model")
    if not board_model:
        board_model = cpuinfo.get("Hardware", "Unknown Arm Board")

    # CPU part mapping
    cpu_part = cpuinfo.get("CPU part", "").lower()
    cpu_implementer = cpuinfo.get("CPU implementer", "").lower()
    
    model, compiler_target = _map_linux_cpu_part(cpu_implementer, cpu_part, board_model)

    # Cores
    total_cores = psutil.cpu_count(logical=True) or 0
    p_cores = total_cores  # Assume all perf cores unless big.LITTLE detected
    e_cores = 0
    
    # Try to detect big.LITTLE from /sys
    try:
        for cpu_dir in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
            cap_file = cpu_dir / "cpu_capacity"
            if cap_file.exists():
                cap = int(cap_file.read_text().strip())
                if cap < 1024:
                    e_cores += 1
                else:
                    p_cores += 1
        # If we found big.LITTLE, adjust
        if e_cores > 0 and p_cores > 0:
            p_cores = max(1, p_cores)
    except Exception:
        pass

    # Memory
    mem = psutil.virtual_memory()
    total_ram_gb = mem.total / (1024**3)
    available_ram_gb = mem.available / (1024**3)

    # Cache line size
    cache_line = _get_cache_line_size()

    # ISA features from cpuinfo Features line
    features = cpuinfo.get("Features", "").lower()
    neon = "neon" in features or "asimd" in features
    sve = "sve" in features
    sve2 = "sve2" in features
    lse = "lse" in features

    # PREEMPT_RT detection
    has_preempt_rt = _detect_preempt_rt()

    # Compiler target (already mapped)
    # Fingerprint
    fingerprint = compute_fingerprint({
        "implementer": cpu_implementer,
        "part": cpu_part,
        "total_ram_kb": int(total_ram_gb * 1024 * 1024),
        "board_model": board_model,
        "cache_line_size": cache_line,
    })

    distro, version = _parse_os_release()
    return HardwareProfile(
        os="linux",
        os_distro=distro,
        os_version=version,
        arch=platform.machine().lower(),
        model=model,
        p_cores=p_cores,
        e_cores=e_cores,
        total_cores=total_cores,
        total_ram_gb=round(total_ram_gb, 1),
        available_ram_gb=round(available_ram_gb, 1),
        neon=neon,
        sve=sve,
        sve2=sve2,
        lse=lse,
        cache_line_size=cache_line,
        l1d_cache=None,
        l2_cache=None,
        l3_cache=None,
        has_preempt_rt=has_preempt_rt,
        compiler_target=compiler_target,
        fingerprint=fingerprint,
    )


def _parse_cpuinfo() -> dict[str, str]:
    """Parse /proc/cpuinfo into dict."""
    result = {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if ":" in line:
                    key, val = line.split(":", 1)
                    result[key.strip()] = val.strip()
    except Exception:
        pass
    return result


def _map_linux_cpu_part(implementer: str, part: str, board_model: str) -> tuple[str, str]:
    """Map CPU implementer+part to model name and compiler target."""
    # ARM implementer
    if implementer == "0x41":
        part_map = {
            "0xd03": ("Cortex-A76", "cortex-a76"),
            "0xd08": ("Cortex-A72", "cortex-a72"),  # Pi 4
            "0xd04": ("Cortex-A76AE", "cortex-a76ae"),
            "0xd05": ("Cortex-A77", "cortex-a77"),
            "0xd06": ("Cortex-A77", "cortex-a77"),
            "0xd07": ("Cortex-A78", "cortex-a78"),
            "0xd09": ("Cortex-A78AE", "cortex-a78ae"),
            "0xd0a": ("Cortex-A78", "cortex-a78"),
            "0xd0b": ("Cortex-X1", "cortex-x1"),
            "0xd0c": ("Cortex-X1", "cortex-x1"),
            "0xd0d": ("Cortex-X2", "cortex-x2"),
            "0xd40": ("Neoverse-V2", "neoverse-v2"),
            "0xd41": ("Neoverse-N2", "neoverse-n2"),
            "0xd42": ("Neoverse-E2", "neoverse-e2"),
            "0xd43": ("Neoverse-V2", "neoverse-v2"),
            "0xd44": ("Neoverse-N2", "neoverse-n2"),
            "0xd46": ("Cortex-A78AE", "cortex-a78ae"),
            "0xd47": ("Cortex-A78AE", "cortex-a78ae"),
            "0xd48": ("Cortex-A510", "cortex-a510"),
            "0xd49": ("Cortex-A510", "cortex-a510"),
            "0xd4a": ("Cortex-A710", "cortex-a710"),
            "0xd4b": ("Cortex-X2", "cortex-x2"),
            "0xd4c": ("Cortex-A710", "cortex-a710"),
            "0xd4d": ("Cortex-X3", "cortex-x3"),
            "0xd4e": ("Cortex-A510", "cortex-a510"),
            "0xd4f": ("Neoverse-V3", "neoverse-v3"),
        }
        if part in part_map:
            return part_map[part]
    
    # Apple (on Linux via Asahi)
    if "apple" in board_model.lower():
        return "Apple Silicon", "apple-m1"
    
    # Raspberry Pi
    if "raspberry pi" in board_model.lower():
        if "4" in board_model:
            return "BCM2711 (Pi 4)", "cortex-a72"
        elif "5" in board_model:
            return "BCM2712 (Pi 5)", "cortex-a76"
        return "Raspberry Pi", "cortex-a72"
    
    # Jetson
    if "jetson" in board_model.lower():
        if "orin" in board_model.lower():
            return "Jetson Orin", "neoverse-v2"
        return "Jetson", "cortex-a78ae"
    
    return f"Arm {part}", "native"


def _map_apple_model_to_target(brand: str) -> str:
    brand_lower = brand.lower()
    if "m4" in brand_lower:
        return "apple-m4"
    elif "m3" in brand_lower:
        return "apple-m3"
    elif "m2" in brand_lower:
        return "apple-m2"
    elif "m1" in brand_lower:
        return "apple-m1"
    return "apple-m1"


def _get_cache_line_size() -> int:
    """Get CPU cache line size on Linux."""
    try:
        result = subprocess.run(["getconf", "LEVEL1_DCACHE_LINESIZE"], capture_output=True, text=True)
        return int(result.stdout.strip())
    except Exception:
        pass
    # Fallback: check sysfs
    try:
        with open("/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size") as f:
            return int(f.read().strip())
    except Exception:
        pass
    return 64


def _detect_preempt_rt() -> bool:
    """Detect PREEMPT_RT kernel."""
    try:
        # Check /proc/config.gz
        import gzip
        with gzip.open("/proc/config.gz", "rt") as f:
            for line in f:
                if "CONFIG_PREEMPT_RT_FULL=y" in line or "CONFIG_PREEMPT_RT=y" in line:
                    return True
    except Exception:
        pass
    # Check uname
    try:
        result = subprocess.run(["uname", "-r"], capture_output=True, text=True)
        if "rt" in result.stdout.lower() or "preempt" in result.stdout.lower():
            return True
    except Exception:
        pass
    return False


def _read_first_line(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip().rstrip('\x00')
    except Exception:
        return None


def _parse_os_release() -> tuple[str | None, str | None]:
    try:
        distro, version = None, None
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro = line.split("=", 1)[1].strip().strip('"').lower()
                elif line.startswith("VERSION_ID="):
                    version = line.split("=", 1)[1].strip().strip('"')
        return distro, version
    except Exception:
        return None, None


def compute_fingerprint(data: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint from hardware identifying fields."""
    # Sort keys for determinism
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode()).hexdigest()


def get_cache_line_size() -> int:
    """Public API for cache line size."""
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["sysctl", "-n", "hw.cachelinesize"], capture_output=True, text=True)
            return int(result.stdout.strip())
        except Exception:
            return 128
    else:
        return _get_cache_line_size()


def get_compiler_target() -> str:
    """Public API for compiler target."""
    if sys.platform == "darwin":
        brand = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        return _map_apple_model_to_target(brand)
    else:
        cpuinfo = _parse_cpuinfo()
        _, target = _map_linux_cpu_part(
            cpuinfo.get("CPU implementer", ""),
            cpuinfo.get("CPU part", ""),
            _read_first_line("/proc/device-tree/model") or ""
        )
        return target


def detect_os() -> dict:
    """Detect operating system information."""
    import platform
    distro, distro_version = _parse_os_release() if sys.platform == "linux" else (None, None)
    return {
        "os": sys.platform,
        "distro": distro,
        "distro_version": distro_version,
        "platform": platform.platform(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }