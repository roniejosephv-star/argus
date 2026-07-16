"""Configuration generation for ROS 2 optimization."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from argus.core.models import HardwareProfile, Scorecard, ConfigFile, ConfigArtifact


def generate_cyclonedds_xml(profile: HardwareProfile, dds_profile: str = "balanced") -> str:
    cache_line = profile.cache_line_size
    total_ram_mb = int(profile.total_ram_gb * 1024)
    
    if dds_profile == "low-latency":
        max_msg_size = min(max(total_ram_mb * 2, 65536), 1048576)
        rcv_buf = min(max(total_ram_mb * 8, 65536), 1048576)
        whc_high = min(max(total_ram_mb * 50, 10000), 50000)
    elif dds_profile == "high-throughput":
        max_msg_size = min(max(total_ram_mb * 8, 262144), 4194304)
        rcv_buf = min(max(total_ram_mb * 32, 262144), 4194304)
        whc_high = min(max(total_ram_mb * 200, 50000), 500000)
    elif dds_profile == "low-memory":
        max_msg_size = 65536
        rcv_buf = 65536
        whc_high = 5000
    else:  # balanced
        max_msg_size = min(max(total_ram_mb * 4, 131072), 2097152)
        rcv_buf = min(max(total_ram_mb * 16, 131072), 2097152)
        whc_high = min(max(total_ram_mb * 100, 25000), 200000)
    
    frag_size = cache_line * 1024
    max_participants = min(profile.total_cores, 16)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
  <Domain id="0">
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
      <MaxMessageSize>{max_msg_size}</MaxMessageSize>
      <FragmentSize>{frag_size}</FragmentSize>
    </General>
    <Internal>
      <SocketReceiveBufferSize>{rcv_buf}</SocketReceiveBufferSize>
      <Watermarks>
        <WhcHigh>{whc_high}</WhcHigh>
        <WhcLow>{whc_high // 2}</WhcLow>
      </Watermarks>
      <MaxAutoParticipantIndex>{max_participants}</MaxAutoParticipantIndex>
      <IntraSharedMemory>true</IntraSharedMemory>
    </Internal>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <MaxAutoParticipantIndex>{max_participants}</MaxAutoParticipantIndex>
    </Discovery>
  </Domain>
</CycloneDDS>"""


def generate_fastdds_xml(profile: HardwareProfile, dds_profile: str = "balanced") -> str:
    total_ram_mb = int(profile.total_ram_gb * 1024)
    
    if dds_profile == "low-latency":
        send_buf = min(max(total_ram_mb * 4, 65536), 524288)
        recv_buf = min(max(total_ram_mb * 8, 131072), 1048576)
        max_msg = 65536
    elif dds_profile == "high-throughput":
        send_buf = min(max(total_ram_mb * 16, 262144), 2097152)
        recv_buf = min(max(total_ram_mb * 32, 524288), 4194304)
        max_msg = 1048576
    elif dds_profile == "low-memory":
        send_buf = 65536
        recv_buf = 65536
        max_msg = 65536
    else:  # balanced
        send_buf = min(max(total_ram_mb * 8, 131072), 1048576)
        recv_buf = min(max(total_ram_mb * 16, 262144), 2097152)
        max_msg = 262144
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>shm_and_udp</transport_id>
      <type>SHM</type>
      <enable_udp>true</enable_udp>
      <max_message_size>{max_msg}</max_message_size>
      <send_buffer_size>{send_buf}</send_buffer_size>
      <receive_buffer_size>{recv_buf}</receive_buffer_size>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="argus_optimized" is_default_profile="true">
    <rtps>
      <builtin>
        <metatrafficUnicastLocatorList>
          <locator>
            <udpv4/>
          </locator>
        </metatrafficUnicastLocatorList>
        <metatrafficMulticastLocatorList>
          <locator>
            <udpv4/>
          </locator>
        </metatrafficMulticastLocatorList>
        <initialPeersList/>
      </builtin>
      <port>
        <portBase>7400</portBase>
      </port>
      <useBuiltinTransports>false</useBuiltinTransports>
      <userTransports>
        <transport_id>shm_and_udp</transport_id>
      </userTransports>
    </rtps>
    <historyMemoryPolicy>DYNAMIC</historyMemoryPolicy>
  </participant>
</profiles>"""


def generate_zenoh_advice(profile: HardwareProfile) -> str:
    if profile.total_ram_gb < 1.0:
        return """# Zenoh Recommendation: STRONGLY RECOMMENDED
**Your system has < 1GB RAM.** DDS overhead will consume significant resources.

## Recommended: Zenoh-Pico
- Ultra-lightweight (~100KB flash, ~10KB RAM)
- No DDS middleware overhead
- Native ROS 2 integration via `rmw_zenoh`
- Ideal for microcontrollers and constrained devices

## Configuration
```yaml
# zenoh_pico_config.yaml
mode: peer
connect:
  - tcp/localhost:7447
listen:
  - tcp/0.0.0.0:7447
```

## Migration Path
1. Install `zenoh-pico` and `rmw_zenoh`
2. Set `RMW_IMPLEMENTATION=rmw_zenoh_cpp`
3. Use `zenoh-bridge-dds` if interoperability with DDS nodes needed
"""
    elif profile.total_ram_gb < 2.0:
        return """# Zenoh Recommendation: RECOMMENDED
**Your system has 1-2GB RAM.** Consider Zenoh for reduced memory footprint.

## Zenoh vs DDS on Your Hardware
| Metric | CycloneDDS | Zenoh |
|--------|------------|-------|
| RAM overhead | ~50-100MB | ~10-20MB |
| Latency (local) | ~200μs | ~100μs |
| Discovery | Complex | Simple |

## Configuration
```yaml
# zenoh_config.yaml
mode: peer
connect:
  - tcp/localhost:7447
listen:
  - tcp/0.0.0.0:7447
plugins:
  - name: ros2
    library: libzenoh_plugin_ros2.so
```
"""
    else:
        return """# Zenoh Recommendation: OPTIONAL
**Your system has sufficient RAM for full DDS.** Zenoh beneficial for:
- Multi-robot / fleet scenarios
- Cloud-edge bridging
- Low-latency requirements (<100μs)
- Mesh networking

## When to Consider Zenoh
- Deploying across unreliable networks (WiFi, 5G)
- Mixing micro-ROS and full ROS 2 nodes
- Need for efficient topic routing at scale

## Basic Config
```yaml
mode: peer
connect:
  - tcp/localhost:7447
```"""


def generate_sysctl_config(profile: HardwareProfile) -> str:
    total_ram_mb = int(profile.total_ram_gb * 1024)
    
    # High maximum socket buffers for high-rate UDP multicast discovery over WiFi/Ethernet
    rmem_max = 2147483647 if "raspberry" in profile.model.lower() else min(max(total_ram_mb * 1024, 1048576), 16777216)
    wmem_max = rmem_max
    
    # SD Card wear reduction and responsiveness (preventing multi-second flush freezes on mmcblk0)
    dirty_ratio = 10 if "raspberry" in profile.model.lower() else 30
    dirty_bg_ratio = 3 if "raspberry" in profile.model.lower() else 5
    
    return f"""# Argus-generated sysctl configuration for ROS 2
# Generated: {datetime.now().isoformat()}
# Hardware: {profile.model} ({profile.total_ram_gb:.1f} GB RAM)

# Network buffers for DDS traffic (tuned for high-rate WiFi / Ethernet multicast discovery)
net.core.rmem_max={rmem_max}
net.core.wmem_max={wmem_max}
net.core.rmem_default=262144
net.core.wmem_default=262144
net.core.netdev_max_backlog=5000
net.core.somaxconn=1024

# IP fragmentation for large DDS packets
net.ipv4.ipfrag_time=30
net.ipv4.ipfrag_high_thresh=8388608
net.ipv4.ipfrag_low_thresh=4194304

# Memory management for ROS 2 nodes (optimized to prevent SD card IO lockup)
vm.dirty_ratio={dirty_ratio}
vm.dirty_background_ratio={dirty_bg_ratio}
vm.swappiness=10

# Scheduler for real-time workloads
kernel.sched_autogroup_enabled=0
kernel.sched_min_granularity_ns=1000000
kernel.sched_wakeup_granularity_ns=1500000

# Huge pages for DDS shared memory (if available)
# vm.nr_hugepages=1024
"""


def generate_build_flags(profile: HardwareProfile) -> dict:
    mcpu = profile.compiler_target
    
    if "apple" in mcpu:
        march = "armv8.5-a"
    elif "cortex-a72" in mcpu or "cortex-a76" in mcpu or "cortex-a78" in mcpu:
        march = "armv8-a"
    elif "neoverse" in mcpu:
        march = "armv8.5-a"
    else:
        march = "armv8-a"
    
    # Avoid -O3 -flto on low RAM Raspberry Pi systems to prevent OOM freezes
    opt_level = "-O2" if profile.total_ram_gb <= 4.0 else "-O3"
    workers = max(1, min(profile.total_cores, int(profile.total_ram_gb // 2))) if profile.total_ram_gb <= 8.0 else profile.total_cores
    
    return {
        "mcpu": mcpu,
        "march": march,
        "lto": profile.total_ram_gb > 4.0,
        "lto_mode": "auto" if profile.total_ram_gb > 4.0 else "none",
        "vectorization": True,
        "colcon_workers": workers,
        "colcon_args": [
            f"--parallel-workers {workers}",
            "--executor sequential" if profile.total_ram_gb <= 4.0 else "--executor parallel",
        ],
        "cmake_args": [
            f"-DCMAKE_CXX_FLAGS=-mcpu={mcpu} {opt_level} -march={march}",
            f"-DCMAKE_C_FLAGS=-mcpu={mcpu} {opt_level} -march={march}",
        ],
        "env": {
            "CFLAGS": f"-mcpu={mcpu} {opt_level}",
            "CXXFLAGS": f"-mcpu={mcpu} {opt_level}",
            "MAKEFLAGS": f"-j{workers}",
        }
    }


def generate_install_script(profile: HardwareProfile, tier: str, rmw: str) -> str:
    distro = "jazzy"
    if profile.os_version:
        v = str(profile.os_version)
        if "24.04" in v:
            distro = "jazzy"
        elif "22.04" in v:
            distro = "humble"
        elif "20.04" in v:
            distro = "foxy"
    
    tier_packages = {
        "ros-desktop": f"ros-{distro}-desktop",
        "ros-base-full": f"ros-{distro}-ros-base ros-{distro}-navigation2 ros-{distro}-ros2-control",
        "ros-base": f"ros-{distro}-ros-base",
        "micro-ros": f"ros-{distro}-ros-base ros-{distro}-micro-ros-agent",
        "zenoh-pico": f"ros-{distro}-ros-base ros-{distro}-rmw-zenoh-cpp",
    }
    
    pkg = tier_packages.get(tier, f"ros-{distro}-ros-base")
    
    rmw_packages = {
        "cyclonedds": f"ros-{distro}-cyclonedds ros-{distro}-rmw-cyclonedds-cpp",
        "fastdds": f"ros-{distro}-fastdds ros-{distro}-rmw-fastrtps-cpp",
        "zenoh": f"ros-{distro}-rmw-zenoh-cpp",
    }
    rmw_pkg = rmw_packages.get(rmw, rmw_packages["cyclonedds"])
    
    os_name = profile.os
    if os_name == "darwin":
        pkg_mgr = "brew"
        install_cmd = f"brew install ros/{distro}/{pkg} {rmw_pkg}"
    else:
        pkg_mgr = "apt"
        install_cmd = f"sudo apt update && sudo apt install -y {pkg} {rmw_pkg}"
    
    return f"""#!/bin/bash
# Argus-generated ROS 2 installation script
# Generated: {datetime.now().isoformat()}
# Hardware: {profile.model}
# Tier: {tier}
# RMW: {rmw}
# Distro: {distro}
# OS: {os_name}

set -euo pipefail

echo "Installing ROS 2 {distro} ({tier} tier) with {rmw}..."

# Add ROS 2 repository
if [ "{os_name}" = "linux" ]; then
    sudo apt update && sudo apt install -y curl gnupg2 lsb-release
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    sudo apt update
fi

# Install ROS 2 tier package
{install_cmd}

# Set up environment
echo "source /opt/ros/{distro}/setup.bash" >> ~/.bashrc
echo "export RMW_IMPLEMENTATION={rmw}" >> ~/.bashrc

# Install colcon and tools
if [ "{os_name}" = "linux" ]; then
    sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-vcstool
fi

# Initialize rosdep
sudo rosdep init || true
rosdep update

echo "ROS 2 {distro} {tier} installation complete!"
echo "Run 'source /opt/ros/{distro}/setup.bash' to use ROS 2."
"""


def generate_all_configs(profile: HardwareProfile, scorecard: Scorecard, output_dir: str = "./configs") -> ConfigArtifact:
    soc_dir = Path(output_dir) / profile.model.lower().replace(" ", "-").replace("(", "").replace(")", "")
    soc_dir.mkdir(parents=True, exist_ok=True)
    
    configs = []
    
    # CycloneDDS
    cyclonedds = generate_cyclonedds_xml(profile, scorecard.dds_profile.value)
    cyclonedds_path = soc_dir / "cyclonedds.xml"
    cyclonedds_path.write_text(cyclonedds)
    configs.append(ConfigFile(name="cyclonedds.xml", path=str(cyclonedds_path), content=cyclonedds, size_bytes=len(cyclonedds)))
    
    # FastDDS
    fastdds = generate_fastdds_xml(profile, scorecard.dds_profile.value)
    fastdds_path = soc_dir / "fastdds.xml"
    fastdds_path.write_text(fastdds)
    configs.append(ConfigFile(name="fastdds.xml", path=str(fastdds_path), content=fastdds, size_bytes=len(fastdds)))
    
    # Zenoh
    zenoh = generate_zenoh_advice(profile)
    zenoh_path = soc_dir / "zenoh_advice.md"
    zenoh_path.write_text(zenoh)
    configs.append(ConfigFile(name="zenoh_advice.md", path=str(zenoh_path), content=zenoh, size_bytes=len(zenoh)))
    
    # sysctl
    sysctl = generate_sysctl_config(profile)
    sysctl_path = soc_dir / "sysctl.conf"
    sysctl_path.write_text(sysctl)
    configs.append(ConfigFile(name="sysctl.conf", path=str(sysctl_path), content=sysctl, size_bytes=len(sysctl)))
    
    # Build flags
    build_flags = generate_build_flags(profile)
    build_flags_json = json.dumps(build_flags, indent=2)
    build_flags_path = soc_dir / "build_flags.json"
    build_flags_path.write_text(build_flags_json)
    configs.append(ConfigFile(name="build_flags.json", path=str(build_flags_path), content=build_flags_json, size_bytes=len(build_flags_json)))
    
    # Install script
    install_sh = generate_install_script(profile, scorecard.tier.value, scorecard.recommended_rmw.value)
    install_path = soc_dir / "install_ros2.sh"
    install_path.write_text(install_sh)
    install_path.chmod(0o755)
    configs.append(ConfigFile(name="install_ros2.sh", path=str(install_path), content=install_sh, size_bytes=len(install_sh)))
    
    # Metadata
    metadata = {
        "soc_model": profile.model,
        "fingerprint": profile.fingerprint,
        "argus_version": "0.1.0",
        "generated_at": datetime.now().isoformat(),
        "tier": scorecard.tier.value,
        "tier_score": scorecard.score,
        "artifacts": [c.name for c in configs],
    }
    metadata_yaml = yaml.dump(metadata, sort_keys=False)
    metadata_path = soc_dir / "metadata.yaml"
    metadata_path.write_text(metadata_yaml)
    configs.append(ConfigFile(name="metadata.yaml", path=str(metadata_path), content=metadata_yaml, size_bytes=len(metadata_yaml)))
    
    return ConfigArtifact(
        soc_model=profile.model,
        fingerprint=profile.fingerprint,
        argus_version="0.1.0",
        generated_at=datetime.now(),
        tier=scorecard.tier.value,
        scorecard=scorecard,
        files=configs,
    )