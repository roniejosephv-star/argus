# Argus User Manual

**Version**: 1.0  
**Date**: 2026-07-10  
**Status**: Draft

---

## 1. Introduction

### 1.1 What is Argus?

Argus is an Arm-native diagnostic and optimization platform for ROS 2. It analyzes your Arm hardware (Apple Silicon, Raspberry Pi, Jetson), determines the best ROS 2 variant for your device, and generates optimized configuration files to maximize performance.

### 1.2 Who is it for?

- **ROS 2 developers** running on Arm hardware who want maximum performance
- **Hobbyists** setting up ROS 2 on Raspberry Pi and unsure which variant to use
- **Robotics researchers** deploying on Jetson who need DDS tuning
- **System integrators** building physical AI systems on Arm

### 1.3 Quick Start (30 seconds)

```bash
# 1. Diagnose your hardware
argus diagnose

# 2. Assess and optimize
argus assess --report

# 3. Apply the generated configs
# Files are in configs/<your-hardware-model>/
ls configs/*/
```

---

## 2. Installation

### 2.1 Prerequisites

- Python 3.11 or later
- macOS (Apple Silicon) or Linux (aarch64)

### 2.2 Install from Source

```bash
git clone https://github.com/your-org/argus.git
cd argus
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2.3 Verify Installation

```bash
argus --version
```

Expected output: `Argus v0.1.0`

### 2.4 Optional Dependencies

- `google-genai`: Gemini CLI wrapper
- `pyhwloc`: Extended hardware topology (Linux only)

Install with: `pip install google-genai pyhwloc`

---

## 3. Hardware Diagnosis

### 3.1 `argus diagnose`

Shows a complete hardware profile of your Arm system:

```
argus diagnose
```

Output includes:
- SoC model (e.g., "Apple M3 Pro", "BCM2712" for Pi 5)
- Operating system and architecture
- CPU core count (performance + efficiency cores)
- RAM size and available memory
- Cache line size (64B or 128B)
- ISA features (NEON, SVE, LSE, etc.)
- Compiler target string
- Hardware fingerprint (unique identifier for your device)

**Detailed mode**:

```
argus diagnose --detailed
```

Adds cache topology (L1/L2 sizes), per-core ISA feature lists, and NUMA node info.

### 3.2 `argus stress`

Runs CPU and memory stress tests to measure raw performance:

```
argus stress
```

Tests:
- **CPU**: Prime number computation (bogo ops/s)
- **Memory**: Bandwidth test (read/write/copy MB/s + latency ns)
- **Thermal**: Temperature monitoring during load

Options:

```
argus stress --duration 30 --workers 4
```

- `--duration`: Test length in seconds (default: 10)
- `--workers`: Number of CPU workers (default: auto = CPU count)

### 3.3 `argus ram`

Samples RAM usage over time:

```
argus ram --pid 4021 --interval 0.5 --duration 20
```

- Without `--pid`: Shows system-wide RAM stats
- With `--pid`: Monitors a specific process (e.g., your ROS 2 node)
- `--interval`: Sampling interval in seconds (default: 1.0)
- `--duration`: Number of samples (default: 10)

---

## 4. ROS 2 Optimization

### 4.1 `argus assess`

The core command. Assesses your hardware for ROS 2 suitability and generates optimized configurations:

```
argus assess
```

**With report**:

```
argus assess --report
```

**Assessment only** (skip config generation):

```
argus assess --no-configs
```

#### Understanding Your Scorecard

Argus scores your hardware on four dimensions:

| Dimension | Weight | What It Measures |
|---|---|---|
| Compute | 35% | Core count, CPU model, ISA features |
| Memory | 30% | RAM size and bandwidth |
| Thermal | 20% | Cooling capability, temp under load |
| ISA | 15% | NEON, SVE, LSE support |

Total score: 0-100

#### 5-Tier System

| Tier | Min Score | When to Use |
|---|---|---|
| **ros-desktop** | 80 | Full ROS 2 Desktop with GUI tools. For powerful Arm devices (M-series Mac, high-end Jetson) |
| **ros-base-full** | 60 | ROS 2 Base + all libraries. For mid-range Arm devices (Pi 5 8GB) |
| **ros-base** | 40 | Minimal ROS 2 core. For resource-constrained devices (Pi 4 2GB) |
| **micro-ros** | 20 | Micro-controller-grade ROS 2. For MCUs and very limited systems |
| **zenoh-pico** | 0 | Zenoh protocol only (no DDS). For sub-256MB devices |

### 4.2 Generated Configurations

After assessment, Argus generates these files in `configs/<your-hardware-model>/`:

#### CycloneDDS XML (`cyclonedds.xml`)

Optimizes DDS communication for your specific Arm CPU. Key parameters:

- **FragmentSize**: Aligned to cache line size for efficient memory access
- **Watermarks (WhcHigh)**: Buffer limits tuned to your RAM
- **IntraSharedMemory**: Enables shared memory for single-machine deployments

#### Fast DDS XML (`fastdds.xml`)

Configures the eProsima Fast DDS middleware:

- **Transport**: SHM + UDPv4 for local + distributed deployments
- **Domain ID**: Set to avoid conflicts
- **History QoS**: Short history for low latency

#### Zenoh Advice (`zenoh_advice.yaml`)

When Argus detects your device is better suited for Zenoh than DDS, it generates advice on switching. Includes Zenoh configuration if recommended.

#### Sysctl Tuning (`sysctl.conf`)

Kernel parameter tuning for real-time ROS 2 performance:

| Parameter | Effect |
|---|---|
| `net.core.rmem_max` | Max receive buffer (networking throughput) |
| `net.core.wmem_max` | Max send buffer |
| `vm.dirty_ratio` | Write-back threshold (I/O performance) |
| `kernel.sched_autogroup_enabled` | Process scheduling fairness |

#### Build Flags (`build_flags.json`)

Compiler optimization flags for building ROS 2 from source:

- `-mcpu=native`: Optimize for your exact CPU
- `-O3`: Maximum optimization level
- `-flto=auto`: Link-time optimization
- `-march=armv8.5-a` (or detected march)

#### Install Script (`install_ros2.sh`)

A ready-to-run script that installs the correct ROS 2 variant for your tier:

```bash
# Example for ros-desktop tier on Ubuntu arm64:
sudo apt update
sudo apt install -y ros-jazzy-desktop
```

---

## 5. Reporting

### 5.1 Generating a Report

```bash
argus assess --report
```

This saves a detailed report to `~/.argus/reports/<fingerprint>/`.

### 5.2 Listing Reports

```bash
argus report --list
```

Shows all saved reports with date, score, and tier.

### 5.3 Diffing Reports

Compare two reports to see what changed:

```bash
argus report --diff a1b2c3 d4e5f6
```

Shows:
- Added files
- Removed files
- Changed parameters (with old/new values)
- Score difference

Useful for comparing:
- Before vs after hardware upgrade
- Different optimization strategies
- Pi 4 vs Pi 5 performance

### 5.4 Managing Lessons

Lessons are optimization insights that Argus saves automatically:

```bash
# List all lessons
argus report --lessons

# View a specific lesson
argus report --lesson 3

# Delete a lesson
argus report --delete-lesson 3

# Export lessons to share
argus report --export-lessons my_lessons.json

# Import lessons from another system
argus report --import-lessons my_lessons.json
```

---

## 6. MCP Integration

### 6.1 What is MCP?

The Model Context Protocol (MCP) allows AI agents (Claude Code, Gemini, etc.) to use Argus tools directly. This means you can ask an AI to optimize your ROS 2 system and it will use Argus as its toolbox.

### 6.2 Starting the MCP Server

```bash
# stdio transport (for local AI agents)
argus mcp serve

# HTTP transport (for remote AI agents)
argus mcp serve --transport http --port 8080
```

### 6.3 Connecting Claude Code

Add to your Claude Code config:

```json
{
    "mcpServers": {
        "argus": {
            "command": "argus",
            "args": ["mcp", "serve"]
        }
    }
}
```

Then in Claude Code: `"Optimize my Pi 5 for ROS 2"`

### 6.4 Using the Gemini CLI Wrapper

```bash
export ARGUS_GEMINI_KEY="your-key"
python scripts/argus_mcp_gemini.py "Should I use micro-ROS on this device?"
```

### 6.5 Using MCP Inspector

```bash
argus mcp serve --transport http --port 8080
# Open http://localhost:8080/mcp in browser
```

### 6.6 Security Notes

- stdio transport: no auth needed (local process only)
- HTTP transport: requires Bearer token for connections from other machines

---

## 7. Pi 4/5 Setup Guide

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python
sudo apt install -y python3 python3-pip python3-venv

# 3. Install Argus
git clone https://github.com/your-org/argus.git
cd argus
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 4. Run diagnosis
argus diagnose

# 5. Run assessment
argus assess --report

# 6. The generated configs will be in configs/raspberry-pi-5/
ls configs/raspberry-pi-5/
```

**Pi-specific notes**:
- Pi 4 (Cortex-A72, 64B cache line) → typically tiers 2-3 (ros-base-full or ros-base)
- Pi 5 (Cortex-A76, 64B cache line) → typically tiers 1-2 (ros-desktop or ros-base-full)
- Thermal throttling is common on Pi: `argus stress` will show if your cooling is adequate

---

## 8. Frequently Asked Questions

### Does Argus work on x86?

No. Argus is designed specifically for Arm aarch64 hardware. It detects Arm SoC features and generates Arm-optimized configs.

### Does Argus install ROS 2?

Argus generates an install script for the correct ROS 2 variant, but does not automatically execute it. Review the script, then run it manually.

### Do I need a Gemini API key?

Only for the Gemini CLI wrapper (`scripts/argus_mcp_gemini.py`). The core CLI and MCP server work without any external API keys.

### Is Argus safe to run on my system?

Yes. Argus has a permission gatekeeper that:
- Auto-approves read-only operations
- Asks for permission before writing files
- Blocks dangerous operations entirely
- Shows exactly what will change before it happens

### Can I commit reports to git?

Yes. Reports are JSON files. You can commit them to track optimization history. Note that reports contain hardware fingerprints which are unique to your device.

### How do I uninstall Argus?

```bash
pip uninstall argus
rm -rf ~/.argus/
```

### Does Argus support Docker?

Argus runs inside Docker containers on Arm hosts. The hardware detection will report the host's CPU (since Docker shares the kernel). For best results, run Argus directly on the host.
