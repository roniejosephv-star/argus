<pre align="center">
<code>
      ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
      █  Argus — Arm-native ROS 2 Diagnostic & Optimization Platform  █
      █                    CREATE MODE ON                             █
      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
</code>
</pre>

<p align="center">
  <strong>Argus</strong> — Arm-native ROS 2 Diagnostic & Optimization Platform
</p>

<p align="center">
  <a href="#-quick-start"><strong>Quick Start</strong></a> •
  <a href="#-features"><strong>Features</strong></a> •
  <a href="#-hardware-support"><strong>Hardware Support</strong></a> •
  <a href="#-mcp-integration"><strong>MCP Integration</strong></a> •
  <a href="#-architecture"><strong>Architecture</strong></a> •
  <a href="#-documentation"><strong>Documentation</strong></a> •
  <a href="#-contributing"><strong>Contributing</strong></a>
</p>

<p align="center">
  <a href="https://github.com/roniejosephv-star/argus/actions"><img src="https://github.com/roniejosephv-star/argus/workflows/CI/badge.svg" alt="CI Status"></a>
  <a href="https://pypi.org/project/argus/"><img src="https://img.shields.io/pypi/v/argus.svg" alt="PyPI Version"></a>
  <a href="https://github.com/roniejosephv-star/argus/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
  <a href="https://github.com/roniejosephv-star/argus/issues"><img src="https://img.shields.io/github/issues/roniejosephv-star/argus.svg" alt="Issues"></a>
  <a href="https://github.com/roniejosephv-star/argus/stargazers"><img src="https://img.shields.io/github/stars/roniejosephv-star/argus.svg" alt="Stars"></a>
</p>

---

**Deploying ROS 2 on Arm is a guessing game.** Developers don't know:
- Which ROS 2 variant fits their board (ros-desktop, ros-base, micro-ros, zenoh-pico)
- Optimal DDS configuration for their specific CPU cache topology and RAM
- Compiler flags that unlock Arm ISA capabilities (NEON, LSE, SVE)
- Kernel/sysctl tuning for real-time robotic workloads

**Result:** Suboptimal performance, wasted resources, failed deployments.

---

## 💡 The Solution: Argus

**Argus** is an **Arm-native, MCP-enabled diagnostic and optimization platform for ROS 2** that bridges the gap between Arm hardware capabilities and ROS 2 deployment decisions.

> **Name origin:** *Argus Panoptes* — the all-seeing giant of Greek mythology with 100 eyes. Argus sees every detail of your Arm hardware.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔍 **Hardware Profiling**
- **Cross-platform**: macOS (sysctl), Linux (/proc, /sys, vcgencmd)
- **Deep detection**: CPU topology (P/E cores), cache hierarchy, ISA features (NEON, SVE, SVE2, LSE), RAM, thermal zones
- **Fingerprinting**: SHA-256 hardware identity for reproducibility
- **Compiler target mapping**: `-mcpu=cortex-a72`, `apple-m4`, `neoverse-v2`, etc.

### 📊 **ROS 2 Tier Assessment**
- **5-tier scoring** (0–100): `ros-desktop` → `ros-base-full` → `ros-base` → `micro-ros` → `zenoh-pico`
- **Weighted breakdown**: RAM (30), Compute (20), ISA (15), Cache (10), Thermal (10), RT (15)
- **Recommendations**: RMW (CycloneDDS/FastDDS/Zenoh), DDS profile, warnings

</td>
<td width="50%">

### ⚙️ **Config Generation (7 Artifacts)**
| Artifact | Purpose |
|----------|---------|
| `cyclonedds.xml` | FragmentSize aligned to cache line, watermarks scaled to RAM |
| `fastdds.xml` | SHM+UDP transport, buffer sizes scaled to RAM |
| `zenoh_advice.yaml` | When to switch from DDS to Zenoh |
| `sysctl.conf` | Network buffers, VM dirty ratios, scheduler tuning |
| `build_flags.json` | `-mcpu`, `-march`, `-O3 -flto=auto`, vectorization |
| `install_ros2.sh` | OS-specific ROS 2 install + RMW setup |
| `metadata.yaml` | Fingerprint, tier, score, artifact manifest |

### 🛡️ **Safety & Governance**
- **Blast-radius gatekeeper**: NONE/LOW → auto-approve, MEDIUM → prompt, HIGH → warn + prompt, CRITICAL → deny
- **Blocklist**: `rm -rf /`, `sudo`, `dd`, `mkfs`, pipe-to-shell, fork bombs
- **Audit trail**: Every permission decision logged with reason

</td>
</tr>
</table>

---

## 🤖 MCP Integration — AI-Native by Design

Argus exposes **all capabilities via MCP (Model Context Protocol)** — making any AI agent (OpenCode, Claude Code, Gemini CLI, Cursor) **hardware-aware on Arm**.

```json
// ~/.opencode/mcp.json  (or claude_desktop_config.json)
{
  "mcpServers": {
    "argus": {
      "command": "argus",
      "args": ["mcp", "serve", "--transport", "stdio"]
    },
    "argus-pi4": {
      "command": "ssh",
      "args": ["pi@raspberrypi.local", "argus", "mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

### 🧰 14 MCP Tools
| Category | Tools |
|----------|-------|
| **Discovery** | `detect_arm_soc`, `detect_os` |
| **Profiling** | `stress_cpu`, `stress_memory`, `measure_thermal`, `measure_ram` |
| **Assessment** | `assess_hardware` |
| **Generation** | `generate_cyclonedds_config`, `generate_fastdds_config`, `generate_zenoh_advice`, `generate_sysctl_config`, `generate_build_flags`, `generate_install_script`, `generate_all_configs` |
| **Project** | `project_list_files`, `project_read_file`, `project_write_file`, `project_git_status`, `project_git_diff`, `project_pip_install`, `project_pytest`, `project_run_command` |

### 📚 10 MCP Resources
| URI | Content |
|-----|---------|
| `argus://system/info` | Full hardware profile |
| `argus://system/cpu` | CPU topology, cache, ISA |
| `argus://system/memory` | RAM usage, available |
| `argus://sensors/temperature` | Live thermal readings |
| `argus://stress/latest` | Latest stress test results |
| `argus://configs/cyclonedds` | Generated CycloneDDS XML |
| `argus://configs/fastdds` | Generated FastDDS XML |
| `argus://configs/sysctl` | Generated sysctl.conf |
| `argus://scorecard/latest` | Latest assessment scorecard |
| `argus://reports/latest` | Latest diagnostic report |

### 💬 4 MCP Prompts
| Prompt | Description |
|--------|-------------|
| `tune-ros2` | Full ROS 2 optimization workflow |
| `profile-arm` | Profile Arm SoC and explain results |
| `optimize-dds` | Analyze hardware + generate optimal DDS config |
| `debug-thermal` | Run thermal stress + analyze throttling risk |

---

## 🖥️ Hardware Support

| Platform | SoC | CPU | RAM | Cache Line | Tier | Configs |
|----------|-----|-----|-----|------------|------|---------|
| **Raspberry Pi 4** | BCM2711 | 4× Cortex-A72 | 2/4/8 GB | 64 B | `micro-ros` / `ros-base` | ✅ 7 files |
| **Raspberry Pi 5** | BCM2712 | 4× Cortex-A76 | 4/8 GB | 64 B | `ros-base` | ✅ 7 files |
| **Apple M1** | M1 | 4P+4E | 8/16 GB | 128 B | `ros-base-full` | ✅ 7 files |
| **Apple M2** | M2 | 4P+4E | 8/24 GB | 128 B | `ros-base-full` | ✅ 7 files |
| **Apple M3** | M3 | 4P+4E | 8/24 GB | 128 B | `ros-base-full` | ✅ 7 files |
| **Apple M4** | M4 | 4P+6E | 24/48 GB | 128 B | `ros-desktop` | ✅ 7 files |
| **Jetson Orin** | T234 | 12× Cortex-A78AE | 8/32 GB | 64 B | `ros-desktop` | 🔜 |
| **Generic Arm** | Any | Any | Any | 64 B | Auto | 🔜 |

> **Pre-generated configs** in `configs/` for instant deployment — no profiling needed on known boards.

---

## 🚀 Quick Start

### Installation
```bash
# From PyPI (when published)
pip install argus

# Or from source (hackathon)
git clone https://github.com/roniejosephv-star/argus.git
cd argus
pip install -e .
```

### Basic Usage
```bash
# Full hardware profile
argus diagnose --detailed

# Stress test (CPU + memory + thermal)
argus stress --duration 30

# Full ROS 2 assessment + config generation
argus assess --output-dir ./my-robot-configs

# Start MCP server for AI agents
argus mcp serve --transport stdio
```

### Example Output
```
              Hardware Profile: Raspberry Pi 4 Model B Rev 1.5             
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property                 ┃ Value                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ OS / Arch                │ Linux / aarch64                              │
│ Model                    │ BCM2711 (Pi 4)                               │
│ Cores                    │ 4 (P:4 E:0)                                  │
│ RAM                      │ 1.8 GB total, 1.4 GB available               │
│ Cache Line               │ 64 bytes                                     │
│ NEON / LSE / SVE         │ ✓ / ✗ / ✗                                  │
│ Compiler Target          │ cortex-a72                                   │
│ Fingerprint              │ a1b2c3d4e5f6...                              │
└──────────────────────────┴────────────────────────────────────────────┘

     ROS 2 Assessment Scorecard       
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Metric          ┃ Score            ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Total Score     │ 33/100           │
│ Tier            │ micro-ros        │
│ Recommended RMW │ cyclonedds       │
│ DDS Profile     │ low-memory       │
└─────────────────┴──────────────────┘
```

---

## 🏗️ Architecture

```
argus/
├── cli.py                    # Click commands: diagnose, stress, assess, mcp
├── core/
│   ├── profiler.py           # Hardware detection (macOS + Linux)
│   ├── assess.py             # 5-tier scoring algorithm
│   ├── optimizer.py          # 7 config generators
│   ├── stresser.py           # CPU/mem/thermal stress (multiprocessing + numpy)
│   ├── ram_sampler.py        # Process/system RAM sampling
│   ├── toolbox.py            # 14-tool registry + dispatcher
│   └── models.py             # Pydantic models (HardwareProfile, Scorecard, etc.)
├── safety/
│   ├── blast_radius.py       # NONE/LOW/MEDIUM/HIGH/CRITICAL
│   ├── blocklist.py          # Destructive command patterns
│   └── gatekeeper.py         # Auto/ask/deny permission flow
├── mcp/
│   ├── server.py             # FastMCP server, 14 tools + resources + prompts
│   ├── resources.py          # 10 resource URIs
│   ├── auth.py               # Bearer token middleware (HTTP)
│   └── transports.py         # stdio + HTTP config
├── state/
│   ├── report.py             # Report, Diff, Lesson models
│   ├── report_store.py       # Persistence + diff engine
│   └── knowledge.py          # Lesson extraction from diffs
├── safety/                   # Blast radius + blocklist
├── state/                    # Reports, diffs, lessons
└── cli.py                    # Click CLI
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=argus --cov-report=html

# Run specific module
pytest tests/test_core.py::test_pi4_cpu_part_mapping -v
```

**Current Status**: 9/9 core tests passing ✅

---

## 📁 Project Structure

```
argus/
├── .github/workflows/ci.yml          # CI/CD pipeline
├── .gitignore
├── LICENSE                           # MIT
├── pyproject.toml                    # Build config (excludes configs/ from package)
├── .gitignore
├── argus/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core/                         # Business logic
│   ├── safety/                       # Blast radius + blocklist
│   ├── mcp/                          # FastMCP server
│   └── state/                        # Reports + knowledge
├── configs/                          # Pre-generated configs (excluded from package)
│   ├── raspberry-pi-4/               # 2GB Pi 4 — micro-ros tier
│   ├── raspberry-pi-5/               # 8GB Pi 5 — ros-base tier
│   ├── apple-m4/                     # 24GB M4 — ros-desktop tier
│   └── raspberry-pi-5/               # Alias for bcm2712
├── docs/                             # 8 documentation files
├── scripts/
│   └── pi4_profile_collector.sh      # Auto-profile Pi via SSH
├── tests/
│   ├── test_core.py                  # 9 tests
│   └── fixtures/                     # Pi 4, Pi 5, Jetson, Apple fixtures
├── scripts/
└── pyproject.toml
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture diagrams |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Full CLI + MCP tool reference |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Pi deployment, ROS 2 install, systemd |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Blast radius, blocklist, threat model |
| [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) | Test strategy, fixtures, CI |
| [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) | End-user guide |
| [`docs/UX_DESIGN.md`](docs/UX_DESIGN.md) | CLI/UX design decisions |
| [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md) | Pydantic model schemas |

### Planning & Analysis (for judges)
| Document | Purpose |
|----------|---------|
| `PRD.md` | Product Requirements Document |
| `PRS.md` | Project Requirements Specification |
| `IMPLEMENTATION_SPEC.md` | Consolidated technical spec |
| `PHASE_BUILD_PLAN.md` | 35-day build plan |
| `EDGE_CASE_ANALYSIS.md` | 47 edge cases catalogued |
| `DECISION_SUMMARY.md` | 7 key decisions (D1–D7) |
| `DECISION_GUIDE.md` | Explanations for each decision |
| `SELF_HOSTED_DEV_LOOP_PLAN.md` | Full self-hosted dev loop architecture |
| `PI4_ROS2_ANALYSIS_PLAN.md` | Pi 4 specific analysis |

---

## 🤝 Contributing

We welcome contributions! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
git clone https://github.com/roniejosephv-star/argus.git
cd argus
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pre-commit install
```

### Code Quality
```bash
ruff check .           # Linting
ruff format .          # Formatting
mypy argus/            # Type checking
pytest                 # Tests
```

---

## 🏆 Hackathon Highlights

| Category | Achievement |
|----------|-------------|
| **Innovation** | First Arm-native ROS 2 optimizer with MCP integration |
| **Completeness** | Full stack: profiler → assessor → generator → MCP server |
| **Hardware Coverage** | 4 platforms pre-configured, extensible to any Arm |
| **AI-Native** | 14 MCP tools + 10 resources + 4 prompts for AI agents |
| **Safety-First** | Blast-radius gatekeeper + destructive command blocklist |
| **Self-Hosted Dev** | OpenCode on Mac → SSH → Pi → Argus builds/tests itself |
| **Production Ready** | Pre-generated configs for Pi 4, Pi 5, Apple M4 |

---

## 📜 License

MIT License — see [`LICENSE`](LICENSE) for details.

---

## 🙏 Acknowledgments

- **FastMCP** — Excellent MCP server framework
- **Pydantic** — Data validation & serialization
- **Click** — Beautiful CLI interfaces
- **Rich** — Beautiful terminal output
- **NumPy** — High-performance stress testing
- **psutil** — Cross-platform system profiling
- **ROS 2 Community** — Inspiration & documentation

---

<p align="center">
  <strong>Built for the Arm Create Hackathon 2026</strong><br>
  Made by <a href="https://github.com/roniejosephv-star">roniejosephv-star</a>
</p>

<p align="center">
  <a href="https://github.com/roniejosephv-star/argus/stargazers">⭐ Star this repo</a> •
  <a href="https://github.com/roniejosephv-star/argus/issues">🐛 Report Bug</a> •
  <a href="https://github.com/roniejosephv-star/argus/discussions">💬 Discuss</a>
</p>