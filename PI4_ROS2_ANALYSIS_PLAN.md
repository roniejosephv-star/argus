# Pi 4 Model B — ROS 2 Native Optimization Analysis Plan

**Target:** `ssh armcreate@192.168.1.43` (Raspberry Pi 4 Model B, 64-bit OS)  
**Goal:** Profile hardware → Assess ROS 2 tier → Generate optimized configs → Validate performance  
**Integration:** Feed real Pi 4 data into Argus implementation

---

## 1. Prerequisites & Access

### 1.1 SSH Connection
```bash
# Test connection
ssh armcreate@192.168.1.43

# If key-based auth needed
ssh-copy-id armcreate@192.168.1.43
```

### 1.2 Required Packages on Pi (install first)
```bash
sudo apt update && sudo apt install -y \
    python3 python3-pip python3-venv \
    linux-tools-common linux-tools-$(uname -r) \
    stress-ng \
    ros-humble-desktop  # or ros-jazzy-desktop for newer
```

### 1.3 Argus Deployment Options
| Option | Pros | Cons |
|--------|------|------|
| **A: Run Argus locally on Pi** | Native detection, real thermal data | Need to build/install on Pi |
| **B: Run Argus on Mac, SSH for data collection** | Faster dev iteration | Remote sysctl/proc parsing complexity |
| **C: Hybrid** — Profiler runs on Pi via SSH, rest on Mac | Best of both | More complex orchestration |

**Recommendation:** Start with **Option A** — deploy Argus to Pi, run full pipeline natively. This validates cross-platform profiler (Linux backend).

---

## 2. Data Collection Checklist (Run on Pi)

### 2.1 Hardware Profile (Profiler Inputs)
```bash
# CPU topology
cat /proc/cpuinfo
lscpu
cat /sys/devices/system/cpu/cpu*/topology/*

# Memory
cat /proc/meminfo
free -h

# Cache hierarchy
getconf LEVEL1_DCACHE_LINESIZE
getconf LEVEL1_DCACHE_SIZE
getconf LEVEL2_CACHE_SIZE
getconf LEVEL3_CACHE_SIZE

# Thermal zones
ls /sys/class/thermal/
cat /sys/class/thermal/thermal_zone*/temp

# Kernel / RT
uname -r
zcat /proc/config.gz | grep PREEMPT
# or: grep PREEMPT /boot/config-$(uname -r)

# Board model
cat /proc/device-tree/model
cat /sys/firmware/devicetree/base/model

# GPU/VPU (Pi 4 specific)
vcgencmd get_config int
vcgencmd measure_temp
```

### 2.2 ROS 2 Baseline (Pre-Optimization)
```bash
# Current ROS 2 install
ros2 --version
ros2 doctor
apt list --installed | grep ros-

# Current RMW
echo $RMW_IMPLEMENTATION
ros2 run demo_nodes_cpp talker &
ros2 run demo_nodes_cpp listener
# Measure latency with ros2 topic echo /chatter --qos-reliability best_effort
```

### 2.3 Stress Test Baselines
```bash
# CPU stress (stress-ng)
stress-ng --cpu 4 --timeout 30s --metrics-brief

# Memory bandwidth (STREAM-like)
stress-ng --vm 2 --vm-bytes 512M --timeout 30s

# Thermal under load
stress-ng --cpu 4 --timeout 60s &
watch -n 1 'vcgencmd measure_temp; cat /sys/class/thermal/thermal_zone0/temp'
```

---

## 3. Pi 4 Model B — Hardware Specs for Argus Mapping

| Component | Pi 4 Spec | Argus Profiler Mapping |
|-----------|-----------|------------------------|
| **SoC** | BCM2711 | `model: "BCM2711"` |
| **CPU** | 4× Cortex-A72 @ 1.5-1.8 GHz | `p_cores: 4, e_cores: 0, total_cores: 4` |
| **ISA** | ARMv8-A, NEON, VFPv4, LSE (ARMv8.1) | `neon: true, lse: true, sve: false` |
| **Cache Line** | 64 bytes | `cache_line_size: 64` |
| **L1** | 48 KB I + 32 KB D per core | `l1d_cache: "32KB"` |
| **L2** | 1 MB shared | `l2_cache: "1MB"` |
| **L3** | None | `l3_cache: null` |
| **RAM** | 2/4/8 GB LPDDR4-3200 | `total_ram_gb: 4.0` (adjust for your model) |
| **Thermal** | SoC sensor (thermal_zone0) | `measure_thermal()` via `/sys/class/thermal` |
| **PREEMPT_RT** | Available via kernel build | `has_preempt_rt: false` (stock) |
| **Compiler Target** | `cortex-a72` | `compiler_target: "cortex-a72"` |

**Expected Argus Tier:** `ros-base-full` (4 GB RAM, 4 cores, NEON+LSE)
- Score ~65-75/100
- RMW: `cyclonedds` (balanced) or `fastdds` (if RT needed)
- DDS Profile: `balanced` or `low-memory`

---

## 4. Argus Implementation — Pi 4 Specifics

### 4.1 Profiler Linux Backend (`core/profiler.py`)
```python
# Key Pi 4 detection logic
def detect_arm_soc_linux(detailed: bool = False) -> HardwareProfile:
    # 1. Read /proc/device-tree/model -> "Raspberry Pi 4 Model B Rev 1.4"
    # 2. Parse /proc/cpuinfo for:
    #    - CPU part: 0xd08 (Cortex-A72)
    #    - Features: neon, vfp, lse, aes, pmull, sha1, sha2, crc32
    # 3. Read /sys/devices/system/cpu/cpu0/cache/index*/size
    # 4. Read /proc/meminfo for MemTotal
    # 5. Check /sys/class/thermal/thermal_zone0/temp
    # 6. Check kernel config for PREEMPT_RT
    # 7. Compute fingerprint from: model, ram, cores, cache_line, cpu_part
```

### 4.2 Optimizer Configs for Pi 4

#### CycloneDDS XML (low-memory profile)
```xml
<CycloneDDS>
  <Domain id="0">
    <Internal>
      <FragmentSize>65536</FragmentSize>        <!-- 64KB = cache line * 1024 -->
      <Watermarks>
        <WhcHigh>50000</WhcHigh>                 <!-- Lower for 4GB RAM -->
      </Watermarks>
    </Internal>
    <Discovery>
      <MaxAutoParticipantIndex>4</MaxAutoParticipantIndex>  <!-- 4 cores -->
    </Discovery>
  </Domain>
</CycloneDDS>
```

#### FastDDS XML (if RT kernel)
```xml
<participant profile_name="argus_pi4_optimized" is_default_profile="true">
  <rtps>
    <builtin>
      <metatrafficUnicastLocatorList>
        <locator>
          <udpv4/>
        </locator>
      </metatrafficUnicastLocatorList>
    </builtin>
    <port>
      <portBase>7400</portBase>
    </port>
  </rtps>
  <historyMemoryPolicy>DYNAMIC</historyMemoryPolicy>
</participant>
```

#### Sysctl (network + memory for 4GB)
```bash
net.core.rmem_max=8388608
net.core.wmem_max=8388608
net.core.somaxconn=1024
vm.dirty_ratio=30
vm.dirty_background_ratio=5
kernel.sched_autogroup_enabled=0
```

#### Build Flags
```json
{
  "mcpu": "cortex-a72",
  "march": "armv8-a+crc+crypto",
  "lto": true,
  "cmake_args": [
    "-DCMAKE_CXX_FLAGS=-mcpu=cortex-a72 -O3 -flto=auto -march=armv8-a+crc+crypto",
    "-DCMAKE_C_FLAGS=-mcpu=cortex-a72 -O3 -flto=auto -march=armv8-a+crc+crypto"
  ]
}
```

#### Install Script (Ubuntu 22.04/24.04 on Pi)
```bash
#!/bin/bash
# argus-generated install_ros2.sh for Pi 4 (ros-base-full tier)
sudo apt update
sudo apt install -y curl gnupg2 lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-jazzy-cyclonedds ros-jazzy-rmw-cyclonedds-cpp
# Add to bashrc: source /opt/ros/jazzy/setup.bash
# Set RMW: export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

---

## 5. Validation & Benchmarking Plan

### 5.1 Functional Validation
| Test | Command | Pass Criteria |
|------|---------|---------------|
| Profiler runs | `argus diagnose --detailed` | Shows BCM2711, 4 cores, 4GB, NEON, LSE |
| Stress test | `argus stress --duration 30` | Returns bogo-ops, thermal data |
| Assessment | `argus assess --report` | Tier = ros-base-full, score 65-75 |
| Configs generated | `ls configs/raspberry-pi-4/` | 6 files + metadata.yaml |
| MCP server | `argus mcp serve --transport stdio` | Starts, responds to tool calls |

### 5.2 ROS 2 Performance Benchmarks
```bash
# Latency test (talker/listener)
ros2 run ros2_benchmark benchmark_latency --topic /chatter --duration 60s

# Throughput test
ros2 run ros2_benchmark benchmark_throughput --topic /scan --duration 60s

# Memory footprint
# Monitor RSS of talker + listener + daemon
```

### 5.3 Pre/Post Optimization Comparison
```bash
# 1. Baseline (default configs)
argus assess --report --reason pre_assess

# 2. Apply generated configs
cp configs/raspberry-pi-4/cyclonedds.xml ~/.config/cyclonedds.xml
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
sudo sysctl -p configs/raspberry-pi-4/sysctl.conf

# 3. Re-assess
argus assess --report --reason post_assess

# 4. Diff
argus report --diff <pre_id> <post_id>
```

---

## 6. Integration with Argus Codebase

### 6.1 Add Pi 4 Fixtures (for CI testing)
```
tests/fixtures/
├── cpuinfo_pi4.txt          # /proc/cpuinfo from Pi 4
├── meminfo_pi4_4gb.txt      # /proc/meminfo
├── thermal_pi4.txt          # /sys/class/thermal/thermal_zone0/temp
├── devicetree_pi4.txt       # /proc/device-tree/model
└── kernel_config_pi4.txt    # PREEMPT_RT status
```

### 6.2 Expected Test Vectors
```python
# test_profiler.py
def test_pi4_detection(cpuinfo_pi4, meminfo_pi4_4gb):
    profile = detect_arm_soc_from_fixtures(cpuinfo_pi4, meminfo_pi4_4gb)
    assert profile.model == "BCM2711"
    assert profile.total_cores == 4
    assert profile.total_ram_gb == 4.0
    assert profile.neon is True
    assert profile.lse is True
    assert profile.cache_line_size == 64
    assert profile.compiler_target == "cortex-a72"

# test_assess.py
def test_pi4_tier():
    profile = pi4_profile_fixture()
    scorecard = assess_hardware(profile)
    assert scorecard.tier == "ros-base-full"
    assert 60 <= scorecard.score <= 80
    assert scorecard.recommended_rmw in ["cyclonedds", "fastdds"]
```

### 6.3 Pre-Generated Configs (Week 4 Deliverable)
```
configs/
└── raspberry-pi-4/
    ├── metadata.yaml
    ├── cyclonedds.xml
    ├── fastdds.xml
    ├── zenoh_advice.yaml
    ├── sysctl.conf
    ├── build_flags.json
    └── install_ros2.sh
```

---

## 7. Execution Steps (When You're Ready)

### Phase 1: Connect & Profile (30 min)
```bash
# 1. SSH to Pi
ssh armcreate@192.168.1.43

# 2. Run data collection script (I'll provide)
curl -sSL https://raw.githubusercontent.com/your-repo/argus/main/scripts/pi4_collect.sh | bash

# 3. Copy results back
scp armcreate@192.168.1.43:~/pi4_profile.json ./tests/fixtures/
```

### Phase 2: Implement Profiler Linux Backend (Day 3 of build plan)
- Use collected fixtures to build/test `profiler.py` Linux path
- Validate fingerprint matches Pi 4

### Phase 3: Full Pipeline on Pi (Week 2)
- Deploy Argus to Pi (`pip install -e .`)
- Run `argus assess --report`
- Validate generated configs work

### Phase 4: Benchmark & Document (Week 3)
- Run ROS 2 benchmarks pre/post
- Document Pi 4 specific tuning guide
- Add to pre-generated configs

---

## 8. Questions for You

| # | Question | Options |
|---|----------|---------|
| Q1 | **Pi 4 RAM variant?** | 2GB / 4GB / 8GB (affects tier: 2GB→ros-base, 4GB→ros-base-full, 8GB→ros-desktop) |
| Q2 | **OS on Pi?** | Raspberry Pi OS 64-bit / Ubuntu Server 22.04/24.04 64-bit |
| Q3 | **ROS 2 distro target?** | Humble (LTS, Ubuntu 22.04) / Jazzy (Ubuntu 24.04) / Rolling |
| Q4 | **Real-time needed?** | Yes (PREEMPT_RT kernel) / No (standard kernel) |
| Q5 | **Deploy Argus how?** | A) On Pi natively / B) On Mac, SSH for data / C) Hybrid |
| Q6 | **Benchmarks to run?** | Latency / Throughput / Memory / CPU / All |
| Q7 | **MCP client to test?** | Claude Code / Gemini CLI / MCP Inspector / Antigravity 2.0 |

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pi 4 thermal throttling under stress | High | Medium | Use `stress-ng --timeout 30s`, monitor `vcgencmd measure_temp` |
| 32-bit userland on 64-bit kernel | Medium | High | Verify `uname -m` = `aarch64`, `file /bin/bash` = ELF 64-bit |
| PREEMPT_RT kernel not available | Low | Medium | Build custom kernel or use Ubuntu RT kernel PPA |
| Argus profiler misses Pi-specific sensors | Medium | Medium | Add `vcgencmd` fallback in thermal backend |
| Network latency affects MCP stdio over SSH | Low | Low | Use MCP HTTP transport with Bearer token instead |

---

**Next Action:** Confirm Q1-Q7 above, then I'll generate the data collection script and we can proceed with Phase 1.
