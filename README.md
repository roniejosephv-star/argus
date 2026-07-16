<pre align="center">
<code>
      ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
      █  Argus — Arm-Native Edge Robotics & DDS Control Plane        █
      █           MAC MINI HOST TIER ◄═ [BRIDGE] ═► ARM EDGE TARGET  █
      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
</code>
</pre>

<p align="center">
  <strong>Argus</strong> — The Dual-Tier Arm-Native Edge Robotics & DDS Control Plane for ROS 2 & AI Agents
</p>

<p align="center">
  <a href="#-quick-start"><strong>Quick Start</strong></a> •
  <a href="#-features"><strong>Features</strong></a> •
  <a href="#-dual-tier-architecture"><strong>Dual-Tier Architecture</strong></a> •
  <a href="#-cli-command-directory"><strong>CLI Commands</strong></a> •
  <a href="#-mcp-ai-integration"><strong>MCP AI Integration</strong></a> •
  <a href="#-ros-2--smart-tv-robotics-project"><strong>Smart TV Robotics</strong></a> •
  <a href="#-hardware-support"><strong>Hardware Support</strong></a> •
  <a href="#-testing--verification"><strong>Testing</strong></a>
</p>

<p align="center">
  <a href="https://github.com/roniejosephv-star/argus/actions"><img src="https://github.com/roniejosephv-star/argus/workflows/CI/badge.svg" alt="CI Status"></a>
  <a href="https://pypi.org/project/argus/"><img src="https://img.shields.io/pypi/v/argus.svg" alt="PyPI Version"></a>
  <a href="https://github.com/roniejosephv-star/argus/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
  <a href="https://github.com/roniejosephv-star/argus/stargazers"><img src="https://img.shields.io/github/stars/roniejosephv-star/argus.svg" alt="Stars"></a>
</p>

---

### 🚀 The Arm Edge Challenge

Deploying high-performance robotics (ROS 2, DDS, AI Agents) across distributed Arm edge hardware (Raspberry Pi 4/5, Apple Silicon, Jetson Orin) involves solving critical system complexities:
- **Distributed Fleet Orchestration:** Managing remote headless Arm boards from a central development host without brittle manual SSH configurations.
- **Hardware-Aware Tiering:** Determining whether an edge target can handle full `ros-desktop`, `ros-base`, `micro-ros`, or `zenoh-pico` based on real-time cache topology, RAM constraints, and thermal limits.
- **DDS & Kernel Optimization:** Tuning FastDDS/CycloneDDS shared-memory watermarks, socket buffers, and `sysctl` real-time schedulers specifically for ARMv8/v9 CPU caches.
- **AI-Native Control:** Enabling autonomous AI agents (**Google Antigravity / OpenCode / Claude Code**) to directly query edge telemetry, profile SoC registers, and orchestrate ROS 2 topics.

---

## 💡 The Solution: Argus Dual-Tier Control Plane

**Argus** solves this by establishing an autonomous **Dual-Tier Control Plane**:
1. **Mac Mini Host Tier (`argus` on macOS):** Acts as the central command hub. It scans subnets (`192.168.1.0/24`) and mDNS for ARM targets, establishes self-healing loopback SSH tunnels (`localhost:2222`), automatically bootstraps remote virtual environments, and exposes a high-level orchestration prompt & Host MCP server.
2. **ARM Edge Target Tier (`argus` natively on Linux/aarch64):** Runs directly on edge boards (Raspberry Pi 4/5, etc.). It inspects `/proc`, `/sys`, and CPU topology, executes hardware scorecards (`assess`), runs thermal/RAM stress tests (`stress`), serves target-side MCP tools, and manages native ROS 2 nodes and topics.

> **Name Origin:** *Argus Panoptes* — the all-seeing giant of Greek mythology with 100 eyes. Argus sees every detail of your distributed Arm hardware fleet.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🌐 **Host Fleet & Tunneling Tier**
- **Zero-Config Discovery:** `argus scan` sweeps local network subnets (`192.168.1.0/24`) and mDNS (`.local`) for Arm targets.
- **Loopback SSH Bridge:** `argus connect <ID>` establishes persistent, auto-reconnecting loopback tunnels (`localhost:2222`).
- **One-Click Bootstrapping:** `argus bootstrap <ID>` deploys Python virtual environments and target daemons over SSH automatically.
- **Interactive Host REPL:** Context-aware terminal loop (`argus [Host]> ` / `argus [Device 1]> `) with instant remote login (`argus login 0`).

### 🔍 **Deep Arm SoC Profiling**
- **Multi-OS Detection:** macOS (`sysctl`) and Linux (`/proc`, `/sys`, `vcgencmd`).
- **CPU Topology:** Pinpoints P/E core layouts, L1/L2/L3 cache line sizes (`64B` vs `128B`), and instruction sets (`NEON`, `SVE`, `SVE2`, `LSE`).
- **Thermal & RAM Sensing:** Real-time millisecond thermal zone probes and dynamic memory availability scoring.

</td>
<td width="50%">

### 📊 **ROS 2 Assessment & DDS Tuning**
- **5-Tier Scorecard:** Evaluates and maps hardware (0–100 score) into `ros-desktop`, `ros-base-full`, `ros-base`, `micro-ros`, or `zenoh-pico`.
- **7 Auto-Generated Artifacts:**
  - `cyclonedds.xml` & `fastdds.xml`: Cache-line aligned fragment sizes and SHM buffer tuning.
  - `zenoh_advice.yaml`: Recommendations on when to offload DDS to Zenoh.
  - `sysctl.conf`: Real-time kernel scheduling and network buffer limits.
  - `build_flags.json`: Arm ISA vectorization flags (`-mcpu=cortex-a72 -O3`).
  - `install_ros2.sh` & `metadata.yaml`.

### 🤖 **AI-Native & Smart TV Robotics**
- **31+ MCP Tools Across Tiers:** Exposes native host orchestration (`argus mcp-host`) and target diagnostics (`argus mcp`) directly to AI agents.
- **Smart TV ROS 2 Demo:** End-to-end natural language channel/volume controller running inside Raspberry Pi over ROS 2 topics (`/smart_tv/command`).

</td>
</tr>
</table>

---

## 🏗️ Dual-Tier Architecture

```
argus/
├── __main__.py               # Entry point wrapper
├── cli.py                    # OS-Aware CLI dispatcher & interactive REPL loop
├── core/
│   ├── profiler.py           # Deep Arm SoC detection (Cortex-A72, M4, Neoverse)
│   ├── assess.py             # 5-tier ROS 2 scoring algorithm
│   ├── optimizer.py          # 7 DDS/Kernel config artifact generators
│   ├── stresser.py           # Multi-core CPU/RAM/Thermal stress engine
│   ├── ram_sampler.py        # Process & system RAM sampler
│   └── models.py             # Pydantic data structures (Tier, Scorecard, Profile)
├── host/
│   ├── scanner.py            # Subnet & mDNS discovery engine (`argus scan`)
│   ├── bridge.py             # Loopback SSH tunneling, sync, and bootstrap (`connect`, `login`)
│   └── mcp_host.py           # Mac Mini Host MCP Server (`argus mcp-host`)
├── robotics/
│   └── ros_manager.py        # ROS 2 lifecycle, topic pub/echo, and Smart TV deployment
├── ui.py                     # Dynamic cyberpunk UI, Host/Target banners, and `argus dash`
├── mcp/
│   ├── server.py             # Target FastMCP Server (23 tools + resources + prompts)
│   └── resources.py          # 10 hardware/telemetry resource URIs
├── safety/                   # Blast-radius gatekeeper & destructive command blocklist
├── common/logger.py          # Centralized structured telemetry logging (`argus-reports/`)
└── tests/                    # 31 comprehensive pytest unit tests
```

---

## 🖥️ CLI Command Directory

Argus automatically adapts its menu and available commands depending on whether it runs on the **Mac Mini Host** or natively on the **Raspberry Pi Target**.

### 1️⃣ Host Control Tier Commands (Mac Mini / macOS)

| Command | Syntax | Description |
| :--- | :--- | :--- |
| **Interactive REPL** | `argus` | Launches the OS-aware Cyberpunk Host Control Tier & target selection menu. |
| **Scan Fleet** | `argus scan` | Sweeps local subnet (`192.168.1.0/24`) and mDNS for available Arm hardware targets. |
| **Connect Bridge** | `argus connect <ID>` | Establishes a self-healing loopback SSH tunnel (`localhost:2222`) to remote Target ID. |
| **Bootstrap Target** | `argus bootstrap <ID>` | Automatically deploys Python `.venv` and `argus` CLI onto remote target via SSH. |
| **Interactive Login** | `argus login <ID>` | Drops right into the remote target's native `argus` interactive REPL loop over SSH bridge. |
| **Remote Dashboard** | `argus login <ID> --dash` | Instantly launches real-time target telemetry dashboard across the SSH tunnel. |
| **ROS 2 Orchestrator** | `argus ros <subcmd>` | Manage remote ROS 2 workspaces (`create`, `build`, `launch`, `topics`, `pub`, `tv-channel`). |
| **Host MCP Server** | `argus mcp-host` | Starts the FastMCP host orchestration server (`stdio` / `http`) for AI agents. |

---

### 2️⃣ Target Edge Tier Commands (Raspberry Pi / Linux / ARM)

| Command | Syntax | Description |
| :--- | :--- | :--- |
| **Diagnose SoC** | `argus diagnose` | Profiles local Arm SoC, cache lines, ISA extensions, thermal zones, and serial ports. |
| **Assess Tier** | `argus assess` | Evaluates hardware against ROS 2 tiers and generates all 7 optimal DDS/sysctl configs. |
| **Stress Hardware** | `argus stress --duration 30` | Executes multi-core CPU & memory stress tests while tracking thermal throttling risk. |
| **Live Telemetry** | `argus dash` | Launches a real-time cyberpunk terminal dashboard tracking RAM, CPU, and thermal status. |
| **Target MCP Server** | `argus mcp` | Starts the target-side FastMCP server (**23 tools**) for direct hardware AI access. |

---

## 🤖 MCP AI Integration

Argus is built from the ground up for **Advanced Agentic Coding** (Google Antigravity, OpenCode, Claude Code). By configuring MCP servers, AI agents gain full visibility into local host orchestration and remote edge hardware registers.

### MCP Configuration Example (`~/.opencode/mcp.json` or `claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "argus-host": {
      "command": "argus",
      "args": ["mcp-host", "--transport", "stdio"]
    },
    "argus-pi4": {
      "command": "ssh",
      "args": ["-p", "2222", "armcreate@127.0.0.1", "~/Argus/.venv/bin/argus", "mcp", "--transport", "stdio"]
    }
  }
}
```

### 🧰 Target MCP Tools (23 Tools via `argus mcp`)
- **Discovery & Profiling:** `detect_arm_soc`, `detect_os`, `measure_thermal`, `measure_ram`
- **Stress & Diagnostics:** `stress_cpu`, `stress_memory`, `assess_hardware`
- **Config Generation:** `generate_cyclonedds_config`, `generate_fastdds_config`, `generate_zenoh_advice`, `generate_sysctl_config`, `generate_build_flags`, `generate_install_script`, `generate_all_configs`
- **Peripherals & UART:** `detect_serial_ports`, `configure_micro_ros_uart`
- **Project & Git Verification:** `project_list_files`, `project_read_file`, `project_write_file`, `project_git_status`, `project_git_diff`, `project_pip_install`, `project_run_command`

### 🧰 Host MCP Tools (8 Tools via `argus mcp-host`)
- **Fleet Management:** `host_scan_network`, `host_list_targets`, `host_connect_target`
- **Remote Execution:** `host_run_on_target`, `host_assess_target`, `host_stress_target`, `host_sync_config`
- **ROS 2 Proxying:** `host_deploy_ros2_node`, `host_check_ros2_topics`

---

## 📺 ROS 2 & Smart TV Robotics Project

As part of our end-to-end verification, Argus includes a full **Natural Language Smart TV Robotics Controller** deployed from the Mac Mini Host onto the Raspberry Pi target over ROS 2 topics:

```bash
# 1. Deploy & verify the Smart TV node package on the target
argus ros tv-channel --target 0

# 2. Send natural language commands from Mac over ROS 2 bridge
argus ros pub /smart_tv/command std_msgs/msg/String '{"data": "channel up"}' --target 0
argus ros pub /smart_tv/command std_msgs/msg/String '{"data": "mute volume"}' --target 0

# 3. Echo live status updates coming from the Pi
argus ros topics echo /smart_tv/status --target 0
```

---

## 🖥️ Hardware Support Matrix

| Platform | SoC | CPU Topology | RAM | Cache Line | Recommended Tier | Pre-Generated Configs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Raspberry Pi 4** | BCM2711 | 4× Cortex-A72 | 2/4/8 GB | 64 B | `micro-ros` / `ros-base` | ✅ `configs/raspberry-pi-4/` |
| **Raspberry Pi 5** | BCM2712 | 4× Cortex-A76 | 4/8 GB | 64 B | `ros-base` | ✅ `configs/raspberry-pi-5/` |
| **Apple M1 / M2 / M3** | Apple Silicon | 4P+4E Cores | 8–24 GB | 128 B | `ros-base-full` | ✅ `configs/apple-m4/` |
| **Apple M4 (Mac Mini)** | Apple M4 | 4P+6E Cores | 24–48 GB | 128 B | `ros-desktop` | ✅ `configs/apple-m4/` |
| **Jetson Orin** | T234 | 12× Cortex-A78AE | 8–32 GB | 64 B | `ros-desktop` | 🔜 Dynamic Auto |

---

## 🧪 Testing & Verification

Argus features a robust suite of **31 unit tests** covering hardware detection, determinism, logger persistence, bridge networking, and ROS 2 lifecycle management:

```bash
# Activate virtual environment
source .venv/bin/activate

# Execute full pytest suite
pytest -v
```

### Test Summary (`31 passed in 0.15s`)
- `tests/test_core.py`: Pi 4 / Pi 5 / Apple SoC fixture parsing, SHA-256 hardware determinism, RAM score formulas (`9 tests`).
- `tests/test_bridge_diagnostics.py`: Target resolution, scanning logging, connection checks (`3 tests`).
- `tests/test_host_bridge.py`: Loopback bridge forwarding and CLI login simulation (`2 tests`).
- `tests/test_host_scanner.py`: Device model serialization and target JSON caching (`2 tests`).
- `tests/test_logger.py`: Singleton event logging and structured file retrieval (`3 tests`).
- `tests/test_new_tools.py`: Serial port detection, Micro-ROS UART setup, and 23-tool MCP registry verification (`6 tests`).
- `tests/test_ros_manager.py`: ROS 2 environment probing, package generation, builds, topic echo/pub, and Smart TV deployment (`6 tests`).

---

## 🏆 Hackathon Highlights (Arm Create 2026)

| Category | Hackathon Delivery |
| :--- | :--- |
| **Dual-Tier Control Plane** | Seamless operation across macOS Host development environments and headless Linux ARM edge targets. |
| **Arm ISA & Cache Mastery** | Deep hardware extraction (`NEON`, `SVE`, `LSE`, `64B/128B` cache lines) mapped to compiler flags (`-mcpu=cortex-a72`). |
| **AI-Native MCP Integration** | **31 total MCP tools** across host and target enabling autonomous agentic debugging & orchestration. |
| **Zero-Touch Edge Bridge** | Self-healing loopback SSH tunnels (`localhost:2222`) with one-command virtual environment bootstrapping. |
| **Production Verification** | 31/31 unit tests passing + live deployment of natural language Smart TV ROS 2 robotics node. |

---

## 📜 License

MIT License — see [`LICENSE`](LICENSE) for details.

---

<p align="center">
  <strong>Built for the Arm Create Hackathon 2026</strong><br>
  Made by <a href="https://github.com/roniejosephv-star">roniejosephv-star</a>
</p>