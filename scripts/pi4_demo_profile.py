
import sys
from pathlib import Path
from argus.core.profiler import _map_linux_cpu_part, _parse_cpuinfo
from argus.core.models import HardwareProfile

def demo_pi4_profile():
    # Simulate /proc/cpuinfo parsing from fixture
    cpuinfo_path = "tests/fixtures/cpuinfo_pi4_2gb.txt"
    cpuinfo = {}
    with open(cpuinfo_path) as f:
        for line in f:
            if ":" in line:
                key, val = line.split(":", 1)
                cpuinfo[key.strip()] = val.strip()
    
    # Extract needed fields
    cpu_part = cpuinfo.get("CPU part", "").lower()
    cpu_implementer = cpuinfo.get("CPU implementer", "").lower()
    board_model = cpuinfo.get("Model", "Raspberry Pi 4 Model B")
    
    # Map to model and target
    model, target = _map_linux_cpu_part(cpu_implementer, cpu_part, board_model)
    
    print(f"--- SoC Detection (Pi 4 Fixture) ---")
    print(f"Model: {model}")
    print(f"Compiler Target: {target}")
    print(f"CPU Part: {cpu_part}")
    print(f"Features: {cpuinfo.get('Features')}")
    
    # Simulate thermal measurement from fixture
    thermal_path = "tests/fixtures/thermal_pi4.txt"
    try:
        with open(thermal_path) as f:
            content = f.read().strip()
            name, val = content.split()
            temp_c = float(val) / 1000.0
            print(f"\n--- Thermal Measurement (Pi 4 Fixture) ---")
            print(f"Sensor: {name}")
            print(f"Temperature: {temp_c:.1f}°C")
    except Exception as e:
        print(f"Could not read thermal fixture: {e}")

if __name__ == "__main__":
    demo_pi4_profile()
