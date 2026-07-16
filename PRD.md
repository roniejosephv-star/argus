# Argus — Production PRD v3

## Arm-Native MCP-Enabled ROS 2 Diagnostic & Optimization Platform

| | |
|---|---|
| **Project** | Argus |
| **Track** | Arm Create AI Optimization Challenge 2026 — Track 1: Physical AI |
| **License** | MIT (visible in GitHub repo About section) |
| **Status** | v3 — Production PRD (strategy-aligned, hackathon-optimized) |
| **Deadline** | Aug 14, 2026 @ 4:00 PM Pacific (Aug 15 @ 4:30 AM IST) |
| **Time Budget** | ~35 days from today (Jul 10, 2026) |
| **Last updated** | 2026-07-10 |

---

## Table of Contents

1. [Strategic Positioning](#1-strategic-positioning)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Target Users](#4-target-users)
5. [MVP Scope — Hackathon Submission](#5-mvp-scope--hackathon-submission)
6. [Architecture](#6-architecture)
7. [Module Specifications](#7-module-specifications)
8. [Tool Catalog](#8-tool-catalog)
9. [MCP Server Design](#9-mcp-server-design)
10. [Data Models](#10-data-models)


12. [Production Build Plan](#12-production-build-plan)
13. [Submission Strategy](#13-submission-strategy)
14. [Verification & Testing](#14-verification--testing)
15. [Risk Register](#15-risk-register)
16. [Scoring Projections](#16-scoring-projections)
17. [Post-Hackathon Roadmap](#17-post-hackathon-roadmap)
18. [Dependencies & Licensing](#18-dependencies--licensing)
19. [References](#19-references)

---

## 1. Strategic Positioning

### 1.1 Why Argus Wins Track 1

Argus is a **developer infrastructure tool that optimizes the Arm platform layer that Physical AI systems depend on** — ROS 2 middleware, DDS communication, real-time configuration, and build optimization — all derived from the real, detected capability of the device.

**Track 1 alignment**: The Physical AI track explicitly includes *"Systems combining AI with robotics or autonomy software stacks, such as ROS 2, simulation environments, middleware, or real-time control frameworks"* and lists projects running on *"Arm-based embedded, edge, or automotive platforms, including robotics SoCs, embedded Linux boards."*

### 1.2 Direct Mapping to Arm Learning Paths

Argus doesn't just fit Track 1 — it directly builds on **Arm's own recommended learning paths**:

| Arm Learning Path | Argus Feature | Connection |
|---|---|---|
| [ROS 2 install guide](https://learn.arm.com/install-guides/ros2/) | `argus assess` → install script generator | Automates the exact setup Arm recommends |
| [Cyclone DDS install guide](https://learn.arm.com/install-guides/cyclonedds/) | `argus optimize` → CycloneDDS XML tuning | Hardware-aware DDS config generation |
| [Deploy multi-node Zenoh on Raspberry Pi](https://learn.arm.com/learning-paths/) | `argus assess` → Zenoh-pico tier + advice | Recommends Zenoh for RAM-constrained Arm devices |
| [Robot Simulation and RL Workflows on Arm](https://learn.arm.com/learning-paths/) | MCP server for AI agent integration | Enables AI-assisted robotics workflow on Arm |

### 1.3 Optimization Categories Addressed

The hackathon evaluates six optimization categories. Argus directly addresses three:

| Category | How Argus Addresses It | Strength |
|---|---|---|
| **Developer experience** | One CLI + MCP server replaces manual hardware research, DDS tuning, and variant selection | ⭐⭐⭐⭐⭐ |
| **Arm-specific optimization** | Every config derived from detected P/E cores, NEON/SVE2, cache line size, RAM | ⭐⭐⭐⭐⭐ |
| **Model speed / Inference speed** | Tuned DDS configs reduce ROS 2 node communication latency; optimized build flags improve execution speed | ⭐⭐⭐ |

### 1.4 Competitive Differentiation

Most hackathon submissions will be:
- Trained models running on Arm (common, expected)
- Robotics demos with ROS 2 (visual, but commodity)
- Edge inference benchmarks (measurable, but narrow)

**Argus is different**: It's **infrastructure that makes all of those better**. A robotics dev using Argus gets the right ROS 2 variant, tuned DDS, optimized build flags, and quantified hardware analysis — before writing a single line of robot code. The MCP server means any AI agent becomes hardware-aware on Arm, which is genuinely novel.

---

## 2. Problem Statement

Developing and deploying ROS 2 on Arm is inconsistent and suboptimal:

1. **Variant guessing**: Developers don't know whether their Arm board should run `ros-desktop` (2GB+ overhead) or `ros-base` (lighter) or skip full ROS 2 entirely for micro-ROS/Zenoh-pico. Wrong choices waste RAM or leave capability on the table.

2. **Default DDS configs hurt performance**: CycloneDDS and Fast DDS ship with generic defaults. On a Raspberry Pi 5 with 4GB RAM, the buffer sizes, watermarks, and socket settings should be completely different from a Jetson Orin with 32GB. Nobody tunes this.

3. **Build flag ignorance**: ROS 2 packages are compiled without Arm-specific flags (`-mcpu=cortex-a76`, NEON SIMD, LTO). Performance is left on the table.

4. **No hardware-aware tooling**: No existing tool profiles the Arm SoC, maps detected capabilities to ROS 2 configuration decisions, and emits reproducible, device-specific artifacts.

5. **No MCP integration**: No tool exposes Arm hardware diagnostics via the Model Context Protocol. AI agents building Physical AI on Arm are flying blind about the hardware they're targeting.

6. **Manual debugging**: When ROS 2 builds fail or nodes underperform on Arm, root-causing requires manual inspection of hardware specs, kernel config, DDS settings, and build flags across different sources.

---

## 3. Solution Overview

Argus is an **Arm-first platform diagnostic tool and MCP-enabled optimization server for ROS 2**.

### 3.1 Core Principles

> **Principle 1: Every optimization Argus applies is derived from the real, detected capability of the device.**

Argus never guesses. It probes the hardware, measures actual performance, and generates configurations tied to what it found.

> **Principle 2: No modification without user permission.**

Argus freely reads and measures (hardware detection, stress testing, RAM sampling, assessment). But any action that **modifies the system** — writing config files to disk, applying sysctl settings, executing build commands, running shell commands — requires explicit user confirmation first. This is enforced by the **Permission Gatekeeper**, a safety layer that classifies every tool by blast radius and gates execution accordingly.

```
  READ (auto-approved)              WRITE (user permission required)
  ─────────────────────             ──────────────────────────────────
  detect_arm_soc                    generate_all_configs (writes files)
  stress_cpu                        apply_sysctl (modifies kernel params)
  stress_memory                     run_command (shell execution)
  measure_ram                       write_config (creates/overwrites files)
  measure_thermal                   colcon_build (modifies build dirs)
  assess_hardware                   scaffold_ros2_package (creates dirs)
  generate_cyclonedds_config *      install_script execution
  generate_fastdds_config *
  generate_zenoh_advice *
  generate_build_flags *
  
  * generate_ tools return strings (auto-approved)
    but writing them to disk requires permission
```

### 3.2 Operating Modes

#### Mode 1: CLI (`argus <command>`)
Direct command-line interface for hardware profiling, stress testing, RAM measurement, and ROS 2 optimization. Runs locally, produces structured output, generates config artifacts.

```
argus diagnose    → Profile the Arm SoC
argus stress      → Stress-test CPU/memory/thermal
argus ram         → Measure process/system RAM usage
argus assess      → Generate scorecard + ROS 2 configs
```

#### Mode 2: MCP Server (`argus mcp serve`)
Exposes all diagnostic and optimization capabilities as MCP tools via stdio and Streamable HTTP transports. Any MCP-compatible client (Claude Code, Gemini CLI, Antigravity 2.0, Cline, web browsers) can connect and use Argus's Arm-native capabilities.

```
argus mcp serve                    → Start with both transports
argus mcp serve --transport stdio  → Stdio only (for Claude Code)
argus mcp serve --transport http   → HTTP only (for remote agents)
```

#### Mode 3: Standalone Agent (`argus agent`) — Post-Hackathon
A self-contained ToolLoopAgent connecting to Google Gemini for autonomous ROS 2 project creation, optimization, and debugging. Deferred to post-hackathon Phase 2.

### 3.3 Key Outputs

| Output | Format | Description |
|---|---|---|
| Hardware Profile | JSON | Full Arm SoC capabilities with fingerprint hash |
| Stress Results | JSON | CPU bogo-ops/s, memory bandwidth MB/s, thermal headroom |
| RAM Analysis | JSON | Per-process RSS, system available, peak usage over time |
| ROS 2 Scorecard | JSON | 0-100 score, 5-tier recommendation, rationale |
| CycloneDDS Config | XML | Device-tuned MaxMessageSize, buffer sizes, watermarks |
| Fast DDS Config | XML | Device-tuned buffer, QoS, history memory policies |
| Zenoh Advice | Markdown | When to use Zenoh, config templates, multi-device guidance |
| Sysctl Tuning | conf | `rmem_max`, `wmem_max`, `ipfrag` for ROS 2 networking |
| Install Script | shell | apt install commands for recommended ROS 2 tier |
| Build Flags | JSON/text | `-mcpu`, `-march`, LTO, SIMD flags for colcon builds |

---

## 4. Target Users

### 4.1 Primary (Hackathon Demo)

| Persona | Use Case | Entry Point |
|---|---|---|
| **Robotics developer on Arm** | Wants correct, optimized ROS 2 setup on Pi/Jetson/Mac | `argus assess` CLI |
| **AI agent user** | Uses Claude Code or Gemini CLI to build robotics projects; needs hardware-aware tooling | `argus mcp serve` → agent connects |

### 4.2 Secondary (Post-Hackathon)

| Persona | Use Case | Entry Point |
|---|---|---|
| **Edge/embedded engineer** | Needs to fit ROS 2 into tight RAM/compute on custom Arm boards | `argus diagnose` + `argus assess` |
| **ROS 2 developer in debug loop** | Wants autonomous diagnosis and fix for build failures | `argus agent` (Phase 2) |
| **Platform team** | Needs reproducible, device-specific ROS 2 deployment configs | CI/CD integration via MCP |

---

## 5. MVP Scope — Hackathon Submission

### 5.1 What Ships (Hard Scope)

> [!IMPORTANT]
> **MVP = Phase 1 only.** Everything below MUST be working, tested, and demo-ready by Aug 10 (4 days before deadline for buffer).

| ID | Feature | CLI Command | MCP Tool |
|---|---|---|---|
| **F1** | Arm SoC Detection | `argus diagnose` | `detect_arm_soc` |
| **F2** | CPU Stress Test | `argus stress` | `stress_cpu` |
| **F3** | Memory Bandwidth Test | `argus stress` | `stress_memory` |
| **F4** | Thermal Monitoring | `argus stress` | `measure_thermal` |
| **F5** | RAM Sampling | `argus ram` | `measure_ram` |
| **F6** | Hardware Scorecard | `argus assess` | `assess_hardware` |
| **F7** | CycloneDDS Config Gen | `argus assess` | `generate_cyclonedds_config` |
| **F8** | Fast DDS Config Gen | `argus assess` | `generate_fastdds_config` |
| **F9** | Zenoh Advice Gen | `argus assess` | `generate_zenoh_advice` |
| **F10** | Sysctl Tuning Gen | `argus assess` | `generate_sysctl_config` |
| **F11** | Build Flags Gen | `argus assess` | `generate_build_flags` |
| **F12** | Install Script Gen | `argus assess` | `generate_install_script` |
| **F13** | MCP Server (stdio) | `argus mcp serve` | — |
| **F14** | MCP Server (HTTP) | `argus mcp serve` | — |
| **F15** | MCP Resources | — | `argus://system/info`, etc. |
| **F16** | MCP Prompts | — | `tune-ros2`, `profile-arm`, etc. |
| **F17** | Permission Gatekeeper | All write operations | All write tools |
| **F18** | Blast Radius Classification | — | Tool metadata |
| **F19** | Command Blocklist | — | `run_command` filter |
| **F20** | Gemini CLI Integration | `python scripts/argus_mcp_gemini.py` | — |

### 5.2 What Does NOT Ship in MVP

| Feature | Reason | Phase |
|---|---|---|
| Standalone Agent (`argus agent`) | Separate project; MCP mode is the differentiator | Phase 2 |
| Gemini integration | Not needed for MCP server mode | Phase 2 |
| Workspace Manager | ROS 2 package discovery; not needed for diagnostics | Phase 2 |
| Multi-strategy Code Editor | Agent-only feature | Phase 2 |
| OAuth 2.1 | Bearer token sufficient for hackathon | Phase 3 |
| Sub-agent spawning | Agent-only feature | Phase 2 |
| MCP Client mode | Agent connecting to external MCP servers | Phase 2 |
| Performance benchmark integration | `performance_test` / `ros2_benchmark` wrappers | Phase 2 |
| Pre-generated config library | Nice-to-have; generate live instead | Phase 3 |

### 5.3 Non-Goals for MVP

- No GUI (CLI + MCP only)
- No container/sandbox isolation
- The MCP server is **not an LLM** — it is a tool server
- Not a replacement for `rosdep`/`colcon`
- No active re-profile gate (fingerprint recorded but not enforced)
- No ROS 2 installation on the demo machine (Argus generates the scripts; it doesn't execute them)
- The Permission Gatekeeper does NOT sandbox or virtualize operations — it gates them with user consent. Actual sandboxing is deferred to Phase 2

---

## 6. Architecture

### 6.1 High-Level System Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           ARGUS SYSTEM                               │
│                                                                      │
│  ┌──────────────────────────┐  ┌───────────────────────────────────┐  │
│  │   Mode 1: CLI             │  │  Mode 2: MCP Server              │  │
│  │   argus <command>         │  │  argus mcp serve                 │  │
│  │                           │  │                                  │  │
│  │   diagnose                │  │  ┌────────────────────────────┐  │  │
│  │   stress                  │  │  │ FastMCP v3+                │  │  │
│  │   ram                     │  │  │                            │  │  │
│  │   assess                  │  │  │ Stdio ← Claude/Gemini/Cline│  │  │
│  │                           │  │  │ HTTP  ← Antigravity/Web   │  │  │
│  │                           │  │  │ Bearer token auth (HTTP)   │  │  │
│  │                           │  │  └────────────────────────────┘  │  │
│  └───────────┬───────────────┘  └───────────────┬─────────────────┘  │
│              │                                   │                    │
│              └───────────┬───────────────────────┘                    │
│                          ▼                                            │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              🛡️  PERMISSION GATEKEEPER (safety/)             │     │
│  │                                                              │     │
│  │  Every tool call passes through the gatekeeper BEFORE        │     │
│  │  execution. Classification determines approval flow:         │     │
│  │                                                              │     │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌───────┐  │     │
│  │  │ NONE   │  │  LOW   │  │ MEDIUM │  │  HIGH  │  │ DENY  │  │     │
│  │  │ Green  │  │ Yellow │  │ Orange │  │  Red   │  │ Black │  │     │
│  │  │Auto-OK │  │Auto-OK │  │  ASK   │  │ASK+warn│  │ BLOCK │  │     │
│  │  │detect_ │  │stress_ │  │write_  │  │run_cmd │  │rm -rf │  │     │
│  │  │assess_ │  │measure_│  │generate│  │install │  │sudo * │  │     │
│  │  │        │  │        │  │_all*   │  │apply_  │  │dd/mkfs│  │     │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └───────┘  │     │
│  │                                                              │     │
│  │  * generate_ tools that return strings = NONE                │     │
│  │    generate_all_configs (writes to disk) = MEDIUM             │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                          │                                            │
│                          ▼ (approved tools only)                      │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    SHARED CORE ENGINE                        │     │
│  │                                                              │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │     │
│  │  │profiler  │ │stresser  │ │ram_sampler│ │  assess      │    │     │
│  │  │.py       │ │.py       │ │.py        │ │  .py         │    │     │
│  │  │          │ │          │ │           │ │              │    │     │
│  │  │detect_soc│ │stress_cpu│ │sample_ram │ │assess_hw     │    │     │
│  │  │cache_line│ │stress_mem│ │           │ │5-tier score  │    │     │
│  │  │compiler  │ │stress_thm│ │           │ │              │    │     │
│  │  └──────────┘ └──────────┘ └───────────┘ └──────────────┘    │     │
│  │                                                              │     │
│  │  ┌──────────────────────────────────────────────────────┐    │     │
│  │  │                    optimizer.py                       │    │     │
│  │  │  cyclonedds_xml │ fastdds_xml │ zenoh_advice         │    │     │
│  │  │  sysctl_config  │ build_flags │ install_script       │    │     │
│  │  └──────────────────────────────────────────────────────┘    │     │
│  │                                                              │     │
│  │  ┌──────────┐ ┌──────────────┐                               │     │
│  │  │models.py │ │ toolbox.py   │                               │     │
│  │  │Pydantic  │ │ TOOL_REGISTRY│                               │     │
│  │  │schemas   │ │ execute()    │                               │     │
│  │  └──────────┘ └──────────────┘                               │     │
│  └──────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Data Flow

```
Hardware Detection          Stress Testing           Assessment
     │                           │                       │
     ▼                           ▼                       ▼
 ┌──────────┐             ┌──────────┐            ┌──────────┐
 │ profiler │────────────▶│ stresser │───────────▶│ assess   │
 │          │  (auto-OK)  │          │  (auto-OK) │          │
 │ HW dict  │             │ Perf dict│            │ Scorecard│
 └──────────┘             └──────────┘            └────┬─────┘
                                                       │
                                                       ▼
                                                 ┌──────────┐
                                                 │optimizer │  (generates strings
                                                 │          │   → auto-OK)
                                                 │ Configs: │
                                                 │ XML/conf │
                                                 │ scripts  │
                                                 └────┬─────┘
                                                      │
                                            ┌─────────┴─────────┐
                                            ▼                   ▼
                                      return to            write to disk
                                      caller (OK)          ┌──────────┐
                                                           │🛡️GATE   │
                                                           │ ASK USER│
                                                           │ Y/N ?   │
                                                           └────┬────┘
                                                                │
                                                         ┌──────┴──────┐
                                                         ▼             ▼
                                                    configs/       DENIED
                                                    {soc}/        (logged)
```

### 6.3 Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | ROS 2 ecosystem compatibility, FastMCP requirement, rapid development |
| MCP Framework | FastMCP v3+ | Dominant Python MCP library, decorator-based, dual transport support |
| CLI Framework | `click` | Battle-tested, type hints, auto-generated help, composable commands |
| Data Validation | `pydantic` v2 | Structured tool I/O, JSON serialization, type safety |
| Hardware Detection | `psutil` + OS-native (`sysctl`/`/proc`) | No fragile compiled dependencies; `pyhwloc` made optional fallback |
| Stress Engine | Python-first (`numpy` + `multiprocessing`) | Zero-compile install; ~85-95% of native C performance |
| Native Backend | C with Python build script | Arm compilation flag demo; judges see `-mcpu=apple-m3` in action |
| Config Templates | Jinja2-style string formatting | Simple, readable, no external template engine needed |
| State | Generated files in `configs/{soc}/` | Reproducible artifacts, no database needed for MVP |
| **Safety** | **Permission Gatekeeper in toolbox** | **All tool calls pass through blast-radius gate before execution. Read = auto, Write = ask user** |

> [!IMPORTANT]
> **`pyhwloc` is demoted to optional.** The original PRD listed it as a primary dependency, but it requires `hwloc` system libraries which are fragile to install (especially on macOS). The profiler will use `psutil` + direct OS API parsing as the primary backend, with `pyhwloc` as an optional enrichment layer if available.

---

## 7. Module Specifications

### 7.1 Directory Structure

```
argus/                           # Repository root
├── pyproject.toml               # Project metadata, deps, scripts
├── LICENSE                      # MIT
├── README.md                    # Hackathon-grade documentation
├── ARCHITECTURE.md              # System design overview
├── argus/                       # Python package
│   ├── __init__.py              # Version, package metadata
│   ├── __main__.py              # python -m argus entry point
│   ├── cli.py                   # Click CLI dispatcher
│   ├── core/                    # Shared business logic
│   │   ├── __init__.py
│   │   ├── profiler.py          # F1: Arm hardware detection
│   │   ├── stresser.py          # F2-F4: CPU/memory/thermal stress
│   │   ├── ram_sampler.py       # F5: Per-process + system RAM
│   │   ├── assess.py            # F6: 5-tier scorecard
│   │   ├── optimizer.py         # F7-F12: Config generation
│   │   ├── models.py            # Pydantic data models
│   │   └── toolbox.py           # Tool registry + dispatcher
│   ├── safety/                  # Permission & safety layer
│   │   ├── __init__.py
│   │   ├── gatekeeper.py        # F19: Permission gate — Deny→Ask→Allow
│   │   ├── blast_radius.py      # F20: Tool classification (none/low/med/high/critical)
│   │   └── blocklist.py         # F21: Blocked command patterns
│   ├── mcp/                     # MCP server implementation
│   │   ├── __init__.py
│   │   ├── server.py            # F13-F14: FastMCP server
│   │   ├── transports.py        # Transport configuration
│   │   ├── auth.py              # Bearer token middleware
│   │   └── resources.py         # F15-F16: Resource URIs + prompts
├── configs/                     # Generated output directory
│   └── {soc_model}/
│       ├── metadata.yaml
│       ├── cyclonedds.xml
│       ├── fastdds.xml
│       ├── zenoh_advice.md
│       ├── sysctl.conf
│       ├── build_flags.json
│       └── install.sh
└── tests/
    ├── __init__.py
    ├── test_profiler.py
    ├── test_stresser.py
    ├── test_ram_sampler.py
    ├── test_assess.py
    ├── test_optimizer.py
    ├── test_mcp_server.py
    ├── test_gatekeeper.py
    └── fixtures/                # Mock sysctl/proc outputs
        ├── sysctl_m3pro.txt
        ├── sysctl_m1.txt
        ├── cpuinfo_pi5.txt
        ├── cpuinfo_jetson.txt
        └── thermal_zones/
```

### 7.2 `core/profiler.py` — Arm Hardware Detection

**Purpose**: Detect the full hardware capability of the current Arm SoC. This is the foundation that everything else depends on.

```python
def detect_arm_soc(detailed: bool = False) -> dict:
    """Detect Arm SoC capabilities.
    
    Platform-specific backends:
      macOS: sysctl hw.*, platform module, psutil
      Linux: /proc/cpuinfo, /sys/devices/system/cpu/, psutil, optional pyhwloc
    
    Returns:
        {
            "os": "darwin" | "linux",
            "arch": "arm64" | "aarch64",
            "model": str,               # "Apple M3 Pro", "BCM2712", "Jetson Orin"
            "p_cores": int,             # Performance cores
            "e_cores": int,             # Efficiency cores
            "total_cores": int,         # Total logical cores
            "total_ram_gb": float,
            "available_ram_gb": float,
            "neon": bool,               # NEON SIMD support
            "sve": bool,                # Scalable Vector Extension
            "sve2": bool,               # SVE2
            "lse": bool,               # Large System Extensions (atomics)
            "cache_line_size": int,     # 64 (standard Arm) or 128 (Apple Silicon)
            "l1d_cache": str | None,    # Per-core, e.g., "128KB"
            "l2_cache": str | None,     # Per-cluster, e.g., "16MB"
            "l3_cache": str | None,     # System-level if present
            "has_preempt_rt": bool,     # Linux only
            "compiler_target": str,     # "apple-m3", "cortex-a76", "neoverse-v2"
            "fingerprint": str,         # SHA-256 of identifying fields
        }
    """

def get_cache_line_size() -> int:
    """Detect CPU cache line size.
    macOS: sysctl hw.cachelinesize → typically 128 on Apple Silicon
    Linux: /sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size → typically 64
    Fallback: 64
    """

def get_compiler_target() -> str:
    """Return the -mcpu target for the current CPU.
    macOS: Map sysctl machdep.cpu.brand_string → apple-m1, apple-m2, apple-m3, apple-m4
    Linux: Map /proc/cpuinfo CPU part → cortex-a76, cortex-a78, neoverse-v2, etc.
    Fallback: 'native'
    """
```

**macOS detection strategy**:
```python
# Key sysctl queries:
# hw.cachelinesize                → cache line size
# hw.perflevel0.logicalcpu        → P-core count
# hw.perflevel1.logicalcpu        → E-core count
# hw.memsize                      → total RAM bytes
# hw.optional.neon                → NEON support (always 1 on arm64)
# machdep.cpu.brand_string        → "Apple M3 Pro"
# hw.l1dcachesize, hw.l2cachesize → cache sizes
```

**Linux detection strategy**:
```python
# /proc/cpuinfo            → CPU implementer, part, variant, revision, features
# /sys/devices/system/cpu/ → online CPUs, frequencies, cache topology
# /sys/class/thermal/      → thermal zones
# /proc/device-tree/model  → board model (Pi, Jetson, etc.)
# psutil                   → RAM, CPU count
```

### 7.3 `core/stresser.py` — Stress Testing

```python
def stress_cpu(duration_s: int = 10, workers: int | None = None) -> dict:
    """CPU stress via multiprocessing + numpy float/integer ops.
    Returns: { "bogo_ops_s": float, "avg_temp_c": float | None, 
               "workers": int, "duration_s": int }
    """

def stress_memory(duration_s: int = 10, array_size_mb: int = 256) -> dict:
    """STREAM-like memory bandwidth via numpy array operations.
    Operations: copy, scale (*3.0), add (a+b), triad (a + 3.0*b)
    Returns: { "copy_mbps": float, "scale_mbps": float,
               "add_mbps": float, "triad_mbps": float }
    """

def stress_thermal(duration_s: int = 30) -> dict:
    """Combined CPU+memory load with continuous thermal monitoring.
    macOS: powermetrics (requires sudo) or IOKit thermal sensors
    Linux: /sys/class/thermal/thermal_zone*/temp
    Returns: { "peak_temp_c": float, "thermal_throttled": bool,
               "avg_temp_c": float, "samples": [...] }
    """
```

### 7.4 `core/ram_sampler.py` — RAM Measurement

```python
def sample_ram(pid: int | None = None, interval_s: float = 1.0,
               duration_s: int = 10) -> dict:
    """Sample RAM usage over time using psutil.
    If pid is None, samples system-wide available memory.
    macOS: psutil wraps mach_task_info
    Linux: psutil wraps /proc/pid/status + getrusage
    Returns: {
        "samples": [{"rss_kb": int, "vms_kb": int, "timestamp": float}],
        "avg_rss_kb": float,
        "peak_rss_kb": int,
        "system_total_kb": int,
        "system_available_kb": int,
    }
    """
```

### 7.5 `core/assess.py` — Hardware Assessment

```python
def assess_hardware(profile: dict, stress_results: dict | None = None) -> dict:
    """Generate ROS 2 efficiency scorecard with tier recommendation.
    
    Tier thresholds (RAM-primary, compute-secondary):
      > 4GB RAM, >= 4 cores:     ros-desktop     (full ROS 2 desktop)
      2-4GB RAM, >= 2 cores:     ros-base-full   (ros-base + key extras)
      512MB-2GB RAM:             ros-base        (minimal ROS 2)
      256-512MB RAM:             micro-ros       (micro-ROS agent)
      < 256MB RAM or MCU:        zenoh-pico      (Zenoh-pico only)
    
    Score breakdown (0-100):
      - RAM capacity:      30 pts
      - Compute (cores):   20 pts
      - ISA features:      15 pts (NEON, SVE2, LSE)
      - Cache:             10 pts
      - Thermal headroom:  10 pts (if stress results available)
      - RT capability:     15 pts (PREEMPT_RT, isolated cores)
    
    Returns: {
        "tier": str,
        "score": int,
        "breakdown": {"ram": float, "compute": float, ...},
        "rationale": str,           # Human-readable explanation
        "recommended_rmw": str,     # "cyclonedds" | "fastdds" | "zenoh"
        "dds_profile": str,         # "low-latency" | "high-throughput" | "balanced" | "low-memory"
        "ros2_distro": str,         # Recommended ROS 2 distro
        "warnings": [str],          # Any concerns (low RAM, thermal, etc.)
    }
    """
```

### 7.6 `core/optimizer.py` — Config Generation

```python
def generate_cyclonedds_xml(profile: dict, dds_profile: str = "balanced") -> str:
    """Generate CycloneDDS XML tuned to hardware profile.
    
    Parameters scaled by RAM and core count:
      MaxMessageSize:            scaled by available RAM
      SocketReceiveBufferSize:   scaled by RAM (64KB–2MB)
      WhcHigh/WhcLow:            scaled by RAM
      FragmentSize:              aligned to cache line size (64 or 128)
      MaxAutoParticipantIndex:   scaled by core count
    
    Profiles:
      balanced:        Default, works for most ROS 2 nodes
      low-latency:     Smaller buffers, faster flush, for control loops
      high-throughput:  Larger buffers, for sensor streams (cameras, lidar)
      low-memory:      Minimal buffers for constrained devices
    """

def generate_fastdds_xml(profile: dict, dds_profile: str = "balanced") -> str:
    """Generate Fast DDS XML profile tuned to hardware.
    Parameters: sendBufferSize, receiveBufferSize, maxMessageSize,
    PublishModeQosPolicy, HistoryMemoryPolicy
    """

def generate_zenoh_advice(profile: dict) -> str:
    """Generate Zenoh adoption guidance markdown.
    Covers: when Zenoh > DDS, config templates, multi-device setup, 
    Zenoh-pico for MCU, rmw_zenoh for ROS 2
    """

def generate_sysctl_config(profile: dict) -> str:
    """Generate sysctl tuning for ROS 2 networking.
    Parameters: net.core.rmem_max, net.core.wmem_max,
    net.ipv4.ipfrag_time, net.ipv4.ipfrag_high_thresh
    """

def generate_build_flags(profile: dict) -> dict:
    """Generate Arm-optimized colcon build flags.
    Returns: { "cmake_args": str, "cc_flags": str, "cxx_flags": str,
               "mcpu": str, "march": str, "lto": bool }
    """

def generate_install_script(profile: dict, tier: str, rmw: str) -> str:
    """Generate apt install shell script for recommended ROS 2 tier.
    Based on Arm Learning Path: learn.arm.com/install-guides/ros2/
    Includes ROS 2 repo setup, tier-specific package install, RMW setup
    """

def generate_all_configs(profile: dict, scorecard: dict, output_dir: str) -> dict:
    """Generate all config artifacts and write to output_dir/{soc_model}/.
    Returns: { "output_dir": str, "files": [{"name": str, "path": str, "size": int}] }
    """
```

### 7.7 `core/toolbox.py` — Tool Registry

```python
@dataclass
class ToolSpec:
    name: str                    # snake_case, verb-prefixed
    description: str             # One-sentence LLM-readable description
    category: str                # discover | profile | tune | verify | system
    blast_radius: str            # none | low | medium | high | critical
    timeout_s: int               # Max execution time
    parameters: type[BaseModel]  # Pydantic model for input validation
    handler: Callable            # Implementation function

TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tool(spec: ToolSpec) -> None:
    """Register a tool in the global registry."""

def execute_tool(name: str, args: dict) -> Any:
    """Execute a tool by name with validated args.
    Routes through Permission Gatekeeper before execution.
    """
    spec = TOOL_REGISTRY[name]
    validated = spec.parameters(**args)
    
    # Permission gate: check blast radius before execution
    from argus.safety.gatekeeper import check_permission
    decision = check_permission(spec)
    if decision == "denied":
        return {"error": "Permission denied", "tool": name,
                "blast_radius": spec.blast_radius}
    if decision == "ask":
        # In CLI mode: prompt user with rich formatted confirmation
        # In MCP mode: return permission_required response to client
        approved = request_user_approval(spec)
        if not approved:
            return {"error": "User declined", "tool": name}
    
    return spec.handler(**validated.model_dump())

def get_mcp_tool_definitions() -> list[dict]:
    """Return tools in FastMCP decorator format."""

def get_tool_list() -> list[dict]:
    """Return human-readable tool listing."""
```

### 7.8 `safety/gatekeeper.py` — Permission Gatekeeper

**Purpose**: Enforce user consent before any system-modifying operation. This is a core safety principle — Argus reads freely but writes only with permission.

```python
from enum import Enum
from typing import Literal

class BlastRadius(str, Enum):
    """Classification of potential impact for each tool."""
    NONE = "none"           # Pure read/compute — no side effects
    LOW = "low"             # Consumes resources (CPU/RAM) but no persistent changes
    MEDIUM = "medium"       # Writes files, creates directories
    HIGH = "high"           # Shell execution, package installation, kernel params
    CRITICAL = "critical"   # Destructive operations — always denied

# Approval policy per blast radius
APPROVAL_POLICY: dict[BlastRadius, Literal["auto", "ask", "deny"]] = {
    BlastRadius.NONE:     "auto",    # Auto-approved, no prompt
    BlastRadius.LOW:      "auto",    # Auto-approved (stress tests, RAM sampling)
    BlastRadius.MEDIUM:   "ask",     # Prompt user: "Write configs to disk? [y/N]"
    BlastRadius.HIGH:     "ask",     # Prompt user with WARNING: "Run shell command? [y/N]"
    BlastRadius.CRITICAL: "deny",    # Always denied, logged
}

# Tool → Blast Radius mapping
TOOL_CLASSIFICATIONS: dict[str, BlastRadius] = {
    # NONE — pure read/compute
    "detect_arm_soc":              BlastRadius.NONE,
    "detect_os":                   BlastRadius.NONE,
    "assess_hardware":             BlastRadius.NONE,
    "generate_cyclonedds_config":  BlastRadius.NONE,   # Returns string, doesn't write
    "generate_fastdds_config":     BlastRadius.NONE,   # Returns string, doesn't write
    "generate_zenoh_advice":       BlastRadius.NONE,   # Returns string, doesn't write
    "generate_sysctl_config":      BlastRadius.NONE,   # Returns string, doesn't write
    "generate_build_flags":        BlastRadius.NONE,   # Returns string, doesn't write
    "generate_install_script":     BlastRadius.NONE,   # Returns string, doesn't write
    
    # LOW — consumes resources, no persistent changes
    "stress_cpu":                  BlastRadius.LOW,
    "stress_memory":               BlastRadius.LOW,
    "measure_thermal":             BlastRadius.LOW,
    "measure_ram":                 BlastRadius.LOW,
    
    # MEDIUM — writes files or creates directories
    "generate_all_configs":        BlastRadius.MEDIUM,  # Writes to configs/{soc}/
    "write_config":                BlastRadius.MEDIUM,  # Writes a single config file
    "scaffold_ros2_package":       BlastRadius.MEDIUM,  # Creates package directory
    
    # HIGH — shell execution, system modification
    "run_command":                 BlastRadius.HIGH,
    "colcon_build":                BlastRadius.HIGH,
    "apply_sysctl":                BlastRadius.HIGH,    # Modifies kernel parameters
    "git_commit":                  BlastRadius.HIGH,
}

def check_permission(tool_spec) -> Literal["approved", "ask", "denied"]:
    """Check if a tool call is permitted based on blast radius.
    
    Evaluation order:
      1. Blocklist check → DENY (hard block, logged)
      2. Blast radius lookup → APPROVAL_POLICY
      3. Default → ASK (unknown tools require permission)
    """
    from argus.safety.blocklist import is_blocked
    
    # Step 1: Hard deny for blocklisted patterns
    if is_blocked(tool_spec):
        log_denial(tool_spec, reason="blocklist")
        return "denied"
    
    # Step 2: Classify by blast radius
    radius = TOOL_CLASSIFICATIONS.get(
        tool_spec.name, BlastRadius.HIGH  # Unknown tools default to HIGH
    )
    policy = APPROVAL_POLICY[radius]
    
    if policy == "auto":
        return "approved"
    elif policy == "deny":
        log_denial(tool_spec, reason="critical_blast_radius")
        return "denied"
    else:
        return "ask"

def request_user_approval(tool_spec) -> bool:
    """Prompt user for approval in CLI mode.
    
    CLI mode: Rich-formatted prompt with tool name, blast radius,
              description of what will be modified, and [y/N] confirmation.
    MCP mode: Return a structured permission_required response so the
              MCP client (Claude Code, etc.) can ask the user.
    """
    # Example CLI output:
    # ┌─────────────────────────────────────────────┐
    # │ 🛡️  Permission Required (blast radius: MEDIUM) │
    # │                                               │
    # │ Tool: generate_all_configs                     │
    # │ Action: Write 6 config files to configs/apple-m3-pro/ │
    # │                                               │
    # │ Files to be created:                           │
    # │   • cyclonedds.xml                             │
    # │   • fastdds.xml                                │
    # │   • zenoh_advice.md                            │
    # │   • sysctl.conf                                │
    # │   • build_flags.json                           │
    # │   • install.sh                                 │
    # └─────────────────────────────────────────────┘
    # Proceed? [y/N]:
```

### 7.9 `safety/blocklist.py` — Command Blocklist

```python
import re

# Patterns that are ALWAYS denied, regardless of blast radius
BLOCKLIST_PATTERNS: list[str] = [
    r"rm\s+-rf\s+/",               # Root deletion
    r"sudo\s+.*",                   # Sudo elevation (unless explicitly needed)
    r">\s+/dev/",                   # Device overwrite
    r"dd\s+if=.*of=.*",            # Raw disk operations
    r"mkfs\.*\s+",                 # Filesystem creation
    r":\(\)\{\s*:\s*\|\|:\s*&\s*\};:",  # Fork bomb
    r"curl.*\|\s*(bash|sh)",       # Pipe to shell
    r"wget.*\|\s*(bash|sh)",       # Pipe to shell
]

# Commands that are blocked by name (interactive / dangerous)
BLOCKLIST_COMMANDS: list[str] = [
    "vim", "vi", "nano", "emacs",    # Interactive editors
    "nohup",                          # Background processes
    "gdb", "lldb", "valgrind",        # Debuggers
    "tmux", "screen",                 # Session managers
    "reboot", "shutdown", "halt",     # System control
]

def is_blocked(tool_spec) -> bool:
    """Check if a tool call matches any blocklist pattern.
    Only applies to tools that execute shell commands (run_command).
    """
    if tool_spec.name != "run_command":
        return False
    
    command = tool_spec.args.get("command", "")
    
    # Check pattern blocklist
    for pattern in BLOCKLIST_PATTERNS:
        if re.search(pattern, command):
            return True
    
    # Check command name blocklist
    cmd_name = command.strip().split()[0] if command.strip() else ""
    if cmd_name in BLOCKLIST_COMMANDS:
        return True
    
    return False
```

---

## 8. Tool Catalog

### 8.1 Discover Tools (Blast Radius: None)

| Tool | Description | Parameters | Returns |
|---|---|---|---|
| `detect_arm_soc` | Probe Arm SoC for cores, cache, ISA, RAM | `{detailed: bool = false}` | HardwareProfile JSON |
| `detect_os` | Detect OS, kernel, PREEMPT_RT, architecture | `{}` | OS info JSON |

### 8.2 Profile Tools (Blast Radius: Low)

| Tool | Description | Parameters | Returns |
|---|---|---|---|
| `stress_cpu` | CPU stress — bogo-ops/s + thermal impact | `{duration_s: 10, workers: null}` | Performance JSON |
| `stress_memory` | STREAM-like memory bandwidth | `{duration_s: 10, array_size_mb: 256}` | Bandwidth JSON |
| `measure_thermal` | Current temperature + throttling status | `{}` | Thermal JSON |
| `measure_ram` | Sample process/system RAM over time | `{pid: null, interval_s: 1.0, duration_s: 10}` | RAM profile JSON |

### 8.3 Tune Tools (Blast Radius: None–Low)

| Tool | Description | Parameters | Returns |
|---|---|---|---|
| `assess_hardware` | Generate ROS 2 scorecard + tier recommendation | `{}` | Scorecard JSON |
| `generate_cyclonedds_config` | Tuned CycloneDDS XML | `{profile: "balanced"}` | XML string |
| `generate_fastdds_config` | Tuned Fast DDS XML | `{profile: "balanced"}` | XML string |
| `generate_zenoh_advice` | Zenoh adoption guidance | `{}` | Markdown string |
| `generate_sysctl_config` | Network sysctl tuning | `{}` | Config string |
| `generate_build_flags` | Arm build flags for colcon | `{}` | Flags JSON |
| `generate_install_script` | ROS 2 apt install commands | `{}` | Shell script string |
| `generate_all_configs` | Generate all artifacts to disk | `{output_dir: "./configs"}` | File list JSON |

---

## 9. MCP Server Design

### 9.1 Transport Configuration

| Transport | Default | Auth | Use Case |
|---|---|---|---|
| **stdio** | ✅ enabled | None (process isolation) | Claude Code, Gemini CLI, Cline |
| **Streamable HTTP** | ✅ enabled | Bearer token (`ARGUS_MCP_TOKEN`) | Antigravity 2.0, web browsers, MCP Inspector |

```python
# mcp/transports.py
class TransportConfig:
    mode: Literal["stdio", "http", "both"] = "both"
    host: str = "127.0.0.1"        # Localhost only by default
    port: int = 8765
    auth_token: str | None = None   # From ARGUS_MCP_TOKEN env var
```

### 9.2 Resource URIs

```python
RESOURCE_URIS = {
    "argus://system/info":            "Full hardware profile (JSON)",
    "argus://system/cpu":             "CPU topology + frequency",
    "argus://system/memory":          "RAM info (total, available, swap)",
    "argus://sensors/temperature":    "Live thermal reading",
    "argus://stress/latest":          "Most recent stress test results",
    "argus://configs/cyclonedds":     "Generated CycloneDDS XML",
    "argus://configs/fastdds":        "Generated Fast DDS XML",
    "argus://configs/sysctl":         "Generated sysctl config",
    "argus://scorecard/latest":       "Most recent hardware scorecard",
}
```

### 9.3 Prompt Templates

```python
PROMPTS = {
    "tune-ros2": {
        "description": "Full ROS 2 optimization workflow: profile → assess → generate configs",
        "arguments": []
    },
    "profile-arm": {
        "description": "Profile this Arm SoC and explain the results",
        "arguments": [{"name": "detailed", "required": False}]
    },
    "optimize-dds": {
        "description": "Analyze hardware and generate optimal DDS configuration",
        "arguments": [{"name": "rmw", "description": "cyclonedds or fastdds", "required": False}]
    },
    "debug-thermal": {
        "description": "Run thermal stress test and analyze throttling risk",
        "arguments": []
    },
}
```

### 9.4 MCP Client Configuration Examples

**Claude Code** (`claude_code_config.json`):
```json
{
  "mcpServers": {
    "argus": {
      "command": "argus",
      "args": ["mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

**Antigravity 2.0 / HTTP clients**:
```bash
export ARGUS_MCP_TOKEN="your-secret-token"
argus mcp serve --transport http --port 8765
# Client connects to http://127.0.0.1:8765/mcp with Bearer token
```

### 9.5 Gemini CLI Integration

A standalone Python script (`scripts/argus_mcp_gemini.py`) connects Gemini directly to Argus tools without running an MCP server. Tools are called in-process via `argus.core.toolbox`, converted to Gemini function declarations.

**System prompt**:
```
You are Argus — an Arm-native diagnostic and optimization tool.
Argus optimizes the Arm platform layer that Physical AI systems
depend on — ROS 2 middleware, DDS communication, and real-time
configuration — all derived from the real, detected capability
of the device.
```

**Usage**:
```bash
export ARGUS_GEMINI_KEY="your-gemini-api-key"
python scripts/argus_mcp_gemini.py "profile this machine and generate a cyclonedds config"
```

**Flow**: Single prompt → Gemini decides tool sequence → executes tools via `execute_tool()` → returns natural language result. No MCP subprocess, no gatekeeper (operator is the user).

**Fallback**: If Gemini API is unavailable, use `argus mcp serve` with MCP Inspector or Claude Code native MCP.

---

## 10. Data Models

### 10.1 Pydantic Models (`core/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class HardwareProfile(BaseModel):
    os: str
    arch: str
    model: str
    p_cores: int
    e_cores: int
    total_cores: int
    total_ram_gb: float
    available_ram_gb: float
    neon: bool
    sve: bool = False
    sve2: bool = False
    lse: bool = False
    cache_line_size: int
    l1d_cache: str | None = None
    l2_cache: str | None = None
    l3_cache: str | None = None
    has_preempt_rt: bool = False
    compiler_target: str
    fingerprint: str

class StressResults(BaseModel):
    cpu_bogo_ops_s: float | None = None
    memory_copy_mbps: float | None = None
    memory_scale_mbps: float | None = None
    memory_add_mbps: float | None = None
    memory_triad_mbps: float | None = None
    peak_temp_c: float | None = None
    thermal_throttled: bool | None = None

class Scorecard(BaseModel):
    tier: Literal["ros-desktop", "ros-base-full", "ros-base",
                  "micro-ros", "zenoh-pico"]
    score: int = Field(ge=0, le=100)
    breakdown: dict[str, float]
    rationale: str
    recommended_rmw: Literal["cyclonedds", "fastdds", "zenoh"]
    dds_profile: Literal["low-latency", "high-throughput",
                         "balanced", "low-memory"]
    ros2_distro: str = "jazzy"
    warnings: list[str] = []

class ConfigFile(BaseModel):
    name: str
    path: str
    content: str
    size_bytes: int

class ConfigArtifact(BaseModel):
    soc_model: str
    fingerprint: str
    argus_version: str
    generated_at: datetime
    tier: str
    scorecard: Scorecard
    files: list[ConfigFile]

class HardwareFingerprint(BaseModel):
    """Deterministic hash of hardware-identifying fields."""
    model: str
    total_ram_gb: float
    total_cores: int
    cache_line_size: int
    arch: str
    hash: str  # SHA-256
```

---

## 12. Production Build Plan

### 12.1 Overview

| Week | Focus | Gate Criteria |
|---|---|---|
| **Week 1** (Jul 10-16) | Foundation: profiler + scorecard + configs | `argus diagnose` and `argus assess` produce real output on Mac |
| **Week 2** (Jul 17-23) | Complete core: stress + RAM + report + MCP + CLI | Full MVP operational, all CLI commands work, MCP responds |
| **Week 3** (Jul 24-30) | Polish: testing + README + MCP demo | End-to-end tests pass, README complete, MCP demo working |
| **Week 4** (Jul 31-Aug 6) | Harden: cross-platform + pre-gen configs + edge cases | Linux aarch64 tested (QEMU or real), code cleanup done |
| **Week 5** (Aug 7-14) | Submit: video + Devpost + final review | Video uploaded, Devpost submitted, repo public |

### 12.2 Week 1 — Foundation (Jul 10-16)

> **Gate**: `argus diagnose` and `argus assess` work on Apple Silicon Mac and produce real, correct output.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 1** (Jul 10) | **M1: Scaffold** | `pyproject.toml`, package structure (`argus/core/`, `argus/mcp/`, `argus/safety/`, `argus/state/`, `tests/`), `__init__.py` files, `__main__.py`, dev environment (`pip install -e .`), `.gitignore`, initial `README.md` skeleton | None |
| **Day 2** (Jul 11) | **M2a: profiler.py (macOS)** | `detect_arm_soc()` with all macOS sysctl backends, `get_cache_line_size()`, `get_compiler_target()`, Apple Silicon model detection (M1/M2/M3/M4 family mapping) | M1 |
| **Day 3** (Jul 12) | **M2b: profiler.py (Linux)** | Linux backends (`/proc/cpuinfo`, `/sys/devices/system/cpu/`), PREEMPT_RT detection, Cortex/Neoverse CPU part mapping, `compute_fingerprint()` | M2a |
| **Day 4** (Jul 13) | **M5: models.py + assess.py** | All Pydantic models, 5-tier classification logic, score computation with weighted breakdown, rationale generation, RMW recommendation | M2 |
| **Day 5** (Jul 14) | **M6a: optimizer.py (configs)** | CycloneDDS XML generation, Fast DDS XML generation, Zenoh advice markdown, sysctl config — all parameterized by hardware profile | M5 |
| **Day 6** (Jul 15) | **M6b: optimizer.py (build/install)** | `generate_build_flags()`, `generate_install_script()`, `generate_all_configs()` orchestrator, `configs/{soc}/` output directory structure with `metadata.yaml` | M6a |
| **Day 7** (Jul 16) | **M8a: CLI (partial)** | `argus diagnose`, `argus assess` working with Click, pretty-printed JSON/table output, `argus --version` | M2, M5, M6 |

### 12.3 Week 2 — Complete Core (Jul 17-23)

> **Gate**: Full Phase 1 MVP operational. All CLI commands work. MCP server starts and responds to tool calls via both transports.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 8** (Jul 17) | **M4a: stresser.py** | `stress_cpu()` with multiprocessing + numpy, `stress_memory()` with STREAM-like numpy ops, temperature sampling integration | M2 |
| **Day 9** (Jul 18) | **M4b: stresser.py + ram_sampler.py** | `stress_thermal()` with combined load, `sample_ram()` with psutil, thermal backend for macOS (IOKit/powermetrics) and Linux (/sys/class/thermal) | M4a |
| **Day 10** (Jul 19) | **M7a: toolbox.py + gatekeeper + MCP server** | `ToolSpec` class, `TOOL_REGISTRY`, all tools registered, `execute_tool()` dispatcher with **Permission Gatekeeper integration** (`safety/gatekeeper.py`, `safety/blast_radius.py`, `safety/blocklist.py`). FastMCP server factory, tool registration loop. Gatekeeper routes all tool calls through Deny→Ask→Allow evaluation | M2-M6 |
| **Day 11** (Jul 20) | **M7b: MCP transports + resources + reporting** | Stdio + HTTP transport with Bearer auth, `TransportConfig`, resource URIs, prompt templates. **Reporting module**: `state/report.py` models, `state/report_store.py` persistence, `state/knowledge.py` lesson extraction | M7a |
| **Day 12** (Jul 21) | **M8b: CLI (complete)** | `argus stress`, `argus ram`, `argus report`, `argus mcp serve` all wired up. Full CLI with help text. Integration between stress → assess → report pipeline | M4, M7 |

### 12.4 Week 3 — Polish (Jul 24-30)

> **Gate**: End-to-end tests pass on macOS. README is submission-ready. MCP demo with Claude Code or Gemini CLI is recorded.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 15-16** (Jul 24-25) | **Testing** | Unit tests for all core modules. E2E test: `diagnose → stress → assess → generate configs`. MCP client test: connect stdio, call tools, verify results. Mock fixtures for Pi 5 and Jetson Orin hardware profiles | M8b |
| **Day 17-18** (Jul 26-27) | **README + Documentation** | Complete README.md with: project overview, architecture diagram, installation (`pip install -e .`), usage examples with sample output, MCP setup instructions for Claude Code, contributing guide. ARCHITECTURE.md with system design | Tests passing |
| **Day 19** (Jul 28) | **MCP Demo Prep** | Test with real MCP client (Claude Code or Gemini CLI). Verify: connect → call `detect_arm_soc` → call `assess_hardware` → call `generate_cyclonedds_config`. Fix any protocol issues | M7b, README |
| **Day 20-21** (Jul 29-30) | **Demo Video Draft** | Script the 3-min video. Record first draft: problem → CLI demo → config output → MCP agent demo. Identify weak spots | MCP demo working |

### 12.5 Week 4 — Harden (Jul 31-Aug 6)

> **Gate**: Linux aarch64 validated. Code cleanup complete. Pre-generated configs for major boards shipped.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 22-23** (Jul 31-Aug 1) | **Cross-Platform Validation** | Test on Linux aarch64 (QEMU Ubuntu or real Pi/Jetson). Fix any platform-specific bugs. Verify profiler detects correct CPU on Linux | MVP complete |
| **Day 24-25** (Aug 2-3) | **Pre-Generated Configs** | Ship configs for: Apple M1, Apple M3 Pro, Apple M4, Raspberry Pi 5 (BCM2712), Raspberry Pi 4 (BCM2711), Jetson Orin Nano, Generic Cortex-A76. Each with metadata.yaml | Cross-platform |
| **Day 26-27** (Aug 4-5) | **Code Cleanup** | Type hints on all public APIs. Docstrings on all modules. Remove dead code. Format with `black`/`ruff`. Ensure consistent error handling | All features |
| **Day 28** (Aug 6) | **Final README + ARCHITECTURE** | Final pass on README: verify all instructions work from clean install. Add sample output screenshots. Link to demo video | Code cleanup |

### 12.6 Week 5 — Submit (Aug 7-14)

> **Gate**: Devpost submission complete. Video uploaded. Repo public with MIT license visible.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 29-30** (Aug 7-8) | **Demo Video Final** | Re-record with polished script. Edit for timing (< 3 min). Upload to YouTube (public). Verify playback | Draft video |
| **Day 31-32** (Aug 9-10) | **Devpost Submission Text** | Project overview, functionality description, setup instructions, track selection (Track 1), video link, repo link | Video uploaded |
| **Day 33-34** (Aug 11-12) | **Buffer** | Fix any last-minute bugs. Handle edge cases from testing. Final repo cleanup | Submission draft |
| **Day 35** (Aug 13) | **Final Review** | Verify: repo public, MIT license visible in About, README complete, video accessible, Devpost text proofread | All done |
| **Day 36** (Aug 14) | **Submit** | Submit on Devpost before 4:00 PM Pacific. Verify submission appears. Breathe | Everything |

### 12.7 Critical Path

```
M1 (scaffold) 
  → M2 (profiler) ← CRITICAL: everything depends on this
    → M5 (models + assess)
      → M6 (optimizer)
        → M7 (MCP server + gatekeeper + report) ← needs all tools + models
          → M8 (CLI) ← wires everything together
    → M4 (stress + RAM)
```

> [!WARNING]
> **`profiler.py` is the single point of failure.** If hardware detection doesn't work correctly, nothing downstream is useful. Allocate extra time here and test on real hardware early.

---

## 13. Submission Strategy

### 13.1 Demo Video Arc (< 3 minutes)

| Time | Segment | Content |
|---|---|---|
| 0:00-0:25 | **Problem** | "Deploying ROS 2 on Arm is a guessing game. Developers don't know which variant fits their board, DDS configs are left at defaults, and build flags ignore Arm capabilities." |
| 0:25-0:50 | **Argus Diagnose** | Run `argus diagnose --detailed` on Apple Silicon. Show detected: M3 Pro, 6P+6E cores, 36GB RAM, NEON, cache line 128B. |
| 0:50-1:15 | **Argus Stress** | Run `argus stress`. Show CPU bogo-ops/s, memory bandwidth (copy/scale/add/triad MB/s), thermal headroom. |
| 1:15-1:50 | **Argus Assess** | Run `argus assess`. Show scorecard: tier=ros-desktop, score=92/100, recommended RMW=CycloneDDS, DDS profile=balanced. Show generated config files. |
| 1:50-2:15 | **Config Walkthrough** | Open `configs/apple-m3-pro/cyclonedds.xml`. Highlight hardware-derived values: `MaxMessageSize`, `SocketReceiveBufferSize` scaled to 36GB RAM, `FragmentSize` aligned to 128B cache line. |
| 2:15-2:50 | **Gemini Agent Demo** | Run `python scripts/argus_mcp_gemini.py "Profile this machine and generate a CycloneDDS config for low-latency robotics"`. Watch Gemini call Argus tools step-by-step and explain each result. |
| 2:50-3:00 | **Wrap** | "Every optimization derived from real, detected capability. Argus — Arm-native diagnostics for Physical AI." |

### 13.2 Devpost Submission Structure

#### Project Overview
> Argus is an Arm-native diagnostic tool and MCP server that profiles Arm SoCs, stress-tests CPU/memory/thermal performance, and generates device-specific, optimized configurations for ROS 2 — the dominant middleware for robotics and Physical AI. Every optimization is derived from the real, detected capability of the device: P/E core counts, NEON/SVE2 ISA features, cache line sizes, RAM capacity, and thermal headroom. Argus also exposes all capabilities as MCP tools, enabling any AI agent (Claude Code, Gemini CLI, Antigravity 2.0) to become hardware-aware on Arm.

#### Why It Should Win
> 1. **Directly addresses the missing layer**: No tool today connects Arm SoC profiling to ROS 2 optimization. Argus fills this gap.
> 2. **Builds on Arm's own learning paths**: Automates the ROS 2 install guide, CycloneDDS tuning, and Zenoh deployment that Arm recommends.
> 3. **Reusable artifacts**: Generated DDS configs, sysctl tuning, and install scripts are immediately usable by any ROS 2 developer on Arm.
> 4. **MCP-first architecture**: Unique in the Physical AI space — any AI agent gains Arm hardware awareness by connecting to Argus.
> 5. **Demonstrable Arm-specific optimization**: Auto-detected `-mcpu` flags, cache-line-aligned DDS fragment sizes, RAM-scaled buffer configurations.

#### Functionality / Output
> - Hardware profile JSON with 20+ detected Arm SoC attributes
> - CPU stress results (bogo-ops/s) and STREAM memory bandwidth (MB/s)
> - ROS 2 efficiency scorecard (0-100) with 5-tier recommendation
> - CycloneDDS XML, Fast DDS XML, Zenoh guidance, sysctl config, build flags, install script — all derived from hardware detection
> - MCP server exposing all tools + resources for AI agent integration

#### Setup Instructions
> ```bash
> # Clone and install
> git clone https://github.com/{user}/argus.git
> cd argus
> pip install -e .
> 
> # Run on any Arm device (Apple Silicon Mac, Raspberry Pi, Jetson)
> argus diagnose --detailed
> argus stress --duration 10
> argus assess --output-dir ./my-configs
> 
> # Start MCP server for AI agent integration
> argus mcp serve
> ```

### 13.3 README.md Structure

```markdown
# 🛡️ Argus — Arm-Native ROS 2 Diagnostic & Optimization Platform

> Every optimization derived from real, detected capability.

[Badges: Python 3.11+, MIT License, Arm64, MCP, Track 1: Physical AI]

## What is Argus?

[One paragraph: problem + solution]

## Quick Start

[pip install + basic commands]

## Features

[Feature list with brief descriptions]

## Demo

[Screenshot/GIF of CLI output + link to demo video]

## Architecture

[Simplified diagram]

## MCP Integration

[How to connect Claude Code / Gemini CLI]

## Generated Configs

[Example output files]

## Supported Platforms

[Apple Silicon, Raspberry Pi 4/5, Jetson Orin, generic aarch64]

## Development

[Contributing, testing, building]

## License

MIT
```

---

## 14. Verification & Testing

### 14.1 Unit Tests

| Module | Test File | Key Tests |
|---|---|---|
| `profiler.py` | `test_profiler.py` | macOS sysctl parsing, Linux /proc parsing, fingerprint determinism, cache line detection, compiler target mapping |
| `stresser.py` | `test_stresser.py` | CPU stress returns valid bogo-ops, memory stress returns positive MB/s, thermal doesn't crash on missing sensors |
| `ram_sampler.py` | `test_ram_sampler.py` | Samples contain expected fields, peak >= avg, system_available > 0 |
| `assess.py` | `test_assess.py` | Tier thresholds correct (8GB→desktop, 1GB→base, 128MB→zenoh-pico), score in 0-100, rationale non-empty |
| `optimizer.py` | `test_optimizer.py` | CycloneDDS XML is valid XML, Fast DDS XML is valid XML, sysctl values are positive integers, install script contains apt |
| `mcp/server.py` | `test_mcp_server.py` | Server starts, tools listed, tool call returns valid response, resource URIs resolve |

### 14.2 Integration Tests

| Test | Description |
|---|---|
| **E2E Pipeline** | `diagnose → stress → assess → generate_configs` — verify all stages produce valid output |
| **MCP Stdio** | Connect via stdio transport, call `detect_arm_soc`, verify JSON response |
| **MCP HTTP** | Connect via HTTP with Bearer token, call tools, verify auth rejection without token |
| **Config Validity** | Parse generated CycloneDDS XML with `xml.etree`, verify schema |
| **Cross-Platform** | Run profiler on macOS and Linux (QEMU), verify both produce valid HardwareProfile |

### 14.3 Mock Fixtures

Pre-recorded outputs for testing without real hardware:
- `sysctl_m3pro.txt` — Apple M3 Pro sysctl output
- `sysctl_m1.txt` — Apple M1 sysctl output
- `cpuinfo_pi5.txt` — Raspberry Pi 5 /proc/cpuinfo
- `cpuinfo_jetson.txt` — Jetson Orin /proc/cpuinfo
- `thermal_zones/` — Mock /sys/class/thermal data

---

## 15. Risk Register

### 15.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| `pyhwloc` won't install on macOS | Blocks profiler | Medium | **Already mitigated**: demoted to optional, using psutil + sysctl as primary |
| FastMCP v3 API breaking changes | Blocks MCP server | Low | Pin version in `pyproject.toml`, test early (Day 12) |
| `powermetrics` requires sudo for thermal on macOS | Incomplete thermal data | Medium | Fall back to IOKit sensors or report "unavailable" gracefully |
| numpy STREAM benchmark doesn't saturate memory bandwidth | Lower-than-expected numbers | Low | Acceptable for profiling purposes; document methodology |


### 15.2 Strategic Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| Judges see "developer tool" as not Physical AI enough | Stage One fail | Low | Framing: "optimizes the Arm platform layer for Physical AI." Track explicitly includes ROS 2 middleware |
| No measurable model/inference speed improvement | Lower tech score | Medium | Lean into "Developer experience" + "Arm-specific optimization" categories. DDS tuning does improve node latency |
| Stronger robotics + ML projects in Track 1 | Lost to visual demos | Medium | MCP angle is the differentiator. No other submission will have AI agent integration for Arm diagnostics |
| No access to real Pi/Jetson for demo | Weaker cross-platform claim | Medium | QEMU aarch64 Ubuntu for validation. Pre-generated configs from known hardware specs |

### 15.3 Submission Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| README incomplete at deadline | Major DX score loss | Low | Write skeleton Day 1, iterate throughout. Final pass Day 28 |
| Demo video too long or unclear | WOW factor loss | Medium | Script in advance. Practice. Time each segment. Edit ruthlessly |
| Repo not public at submission time | Disqualification | Low | Set public on Day 35. Verify visibility |
| MIT license not visible in GitHub About | Submission requirement fail | Low | Add to About section explicitly. Verify |

---

## 16. Scoring Projections

### 16.1 Judging Criteria Breakdown

#### Technological Implementation — 40 points

| Factor | Score | Rationale |
|---|---|---|
| Quality software development | 8-9/10 | Pydantic models, typed APIs, clean architecture, tests |
| Arm platform leverage | 9-10/10 | Entire project is Arm-specific detection + optimization |
| Technical approach | 7-8/10 | Sound architecture, dual-mode CLI+MCP, well-designed tool catalog |
| Well executed | 6-8/10 | Depends on code quality, edge case handling, cross-platform robustness |
| **Subtotal** | **30-35/40** | |

#### User Experience / Developer Experience — 15 points

| Factor | Score | Rationale |
|---|---|---|
| Clear to use/run/validate | 4-5/5 | One-command CLI, clear output, step-by-step README |
| Documentation quality | 3-4/5 | README + ARCHITECTURE + inline docstrings |
| Reusability potential | 4-5/5 | MCP tools usable by any agent; configs reusable across projects |
| **Subtotal** | **11-13/15** | |

#### Potential Impact — 20 points

| Factor | Score | Rationale |
|---|---|---|
| Community utility | 7-8/10 | Every ROS 2 dev on Arm benefits |
| Reusable artifacts | 8-9/10 | DDS configs, install scripts, build flags — all reusable |
| **Subtotal** | **15-18/20** | |

#### WOW Factor — 25 points

| Factor | Score | Rationale |
|---|---|---|
| Creative approach | 7-8/10 | MCP for Arm diagnostics is novel |
| Stand out quality | 6-7/10 | Not a visual robotics demo, but technically compelling |
| Quick attention capture | 5-7/5 | Demo video arc: problem → one command → results → AI agent using it |
| **Subtotal** | **18-22/25** | |

### 16.2 Total Projected Range

| Criterion | Weight | Low | High |
|---|---|---|---|
| Technical Implementation | 40 | 30 | 35 |
| UX / DX | 15 | 11 | 13 |
| Potential Impact | 20 | 15 | 18 |
| WOW Factor | 25 | 18 | 22 |
| **Total** | **100** | **74** | **88** |

> [!NOTE]
> 74-88 is competitive for **Best in Physical AI** and within striking range for **Overall Winner** depending on field strength. The high end requires excellent execution on code quality, documentation, and demo video.

---

## 17. Post-Hackathon Roadmap

### Phase 2 — Agentic (Post-Hackathon, 4-6 weeks)

**Goal**: Standalone autonomous agent with Gemini integration, pipeline orchestrator, and MCP client mode.

| Feature | Description | Priority |
|---|---|---|
| **ToolLoopAgent** | REASON→PARSE→EXECUTE→FEEDBACK loop with Google Gemini via `google-genai` SDK | P0 |
| **Governor** | Max steps (20), timeouts (600s), cost limits ($0.50), per-tool quotas | P0 |
| **Pipeline Orchestrator** | DISCOVER→PROFILE→TUNE→BUILD→VERIFY phase pipeline with iteration support | P1 |
| **HeuristicDiagnosticEngine** | Rule-based fallback when no Gemini API key — pattern matches common ROS 2 errors | P1 |
| **MCP Client Mode** | Agent connects to external MCP servers (filesystem, git, web search) | P2 |
| **Permission Gatekeeper** | Blast radius classification, deny/ask/allow evaluation, command blocklist | P1 |
| **Workspace Manager** | ROS 2 package discovery, scoped file ops, git auto-commit (Aider-style) | P2 |
| **Multi-Strategy Code Editor** | SEARCH/REPLACE → whole file → unified diff fallback chain | P2 |

**Key milestones**:
- `argus agent "diagnose why my ROS 2 build fails on Pi 5"` → Gemini-powered diagnosis
- `argus agent "create a minimal pub/sub ROS 2 package optimized for this board"` → full project scaffolding
- Agent connects to external MCP servers for web search during debugging

### Phase 3 — Production (Post-Hackathon, 2-3 months)

**Goal**: Production-ready MCP server with OAuth, pre-built configs, and community adoption.

| Feature | Description | Priority |
|---|---|---|
| **OAuth 2.1 + PKCE** | Full authorization code flow for HTTP transport, JWKS, per-tool scopes | P1 |
| **Pre-Generated Config Library** | Ship configs for 20+ Arm boards (Pi 3/4/5, Jetson Nano/Xavier/Orin, RK3588, i.MX8, etc.) | P0 |
| **Performance Benchmark Integration** | Wrap `performance_test` and `ros2_benchmark` for latency/jitter/throughput measurement | P1 |
| **Sub-Agent Spawning** | Agent spawns child agents for parallel investigation (DDS tuning + memory profiling + docs search) | P2 |
| **CI/CD Integration** | GitHub Actions for automated testing on QEMU aarch64 + macOS ARM64 | P1 |
| **PyPI Distribution** | Publish to PyPI as `argus-arm` or `argus-ros2` | P0 |

### Phase 4 — Ecosystem (6+ months)

**Goal**: Become the standard Arm diagnostic layer for the ROS 2 ecosystem.

| Feature | Description |
|---|---|
| **Web Dashboard** | Browser-based UI for hardware profiles, scorecards, and config management |
| **Fleet Management** | Profile and optimize multiple Arm devices from a central MCP server |
| **ROS 2 Package Index Integration** | Recommend packages based on hardware capability |
| **Community Config Sharing** | Upload/download device-specific configs contributed by community |
| **Arm Performix Integration** | Direct integration with Arm's benchmarking tool for official performance numbers |
| **RISC-V Support** | Extend profiler beyond Arm to RISC-V SoCs |

---

## 18. Dependencies & Licensing

### 18.1 Python Dependencies (MVP)

| Package | Version | License | Purpose |
|---|---|---|---|
| `click` | >=8.0 | BSD-3 | CLI framework |
| `psutil` | >=5.9 | BSD-3 | System monitoring (CPU, RAM, thermal) |
| `numpy` | >=1.24 | BSD-3 | Stress test computations |
| `pydantic` | >=2.0 | MIT | Data model validation |
| `fastmcp` | >=3.0 | MIT | MCP server framework |
| `rich` | >=13.0 | MIT | Terminal output formatting |
| `pyyaml` | >=6.0 | MIT | YAML config output |

### 18.2 Optional Dependencies

| Package | Version | License | Purpose |
|---|---|---|---|
| `pyhwloc` | >=2.0 | BSD-3 | Hardware topology (optional enrichment) |
| `stress-ng` | (system) | GPL-2 | External stress tool (not bundled, detected at runtime) |
| `google-genai` | >=1.0 | Apache 2.0 | Gemini CLI wrapper (`scripts/argus_mcp_gemini.py`) |

### 18.3 License Compliance

All required dependencies are **MIT, BSD-3, or Apache 2.0** — fully compatible with MIT licensing. `stress-ng` (GPL) is never bundled, only detected and invoked if already installed.

---

## 19. References

### Arm Learning Paths (Track 1: Physical AI)
- [ROS 2 install guide for Arm](https://learn.arm.com/install-guides/ros2/)
- [Cyclone DDS install guide](https://learn.arm.com/install-guides/cyclonedds/)
- [Deploy multi-node Zenoh on Raspberry Pi](https://learn.arm.com/learning-paths/)
- [Robot Simulation and RL Workflows on Arm](https://learn.arm.com/learning-paths/)

### ROS 2 / DDS
- [ROS 2 DDS Tuning Guide](https://docs.ros.org/en/rolling/How-To-Guides/DDS-tuning.html)
- [CycloneDDS Configuration](https://cyclonedds.io/docs/cyclonedds/latest/)
- [Fast DDS XML Profiles](https://fast-dds.docs.eprosima.com/)
- [rmw_zenoh for ROS 2](https://github.com/ros2/rmw_zenoh)
- [micro-ROS](https://micro.ros.org)
- [Zenoh-pico](https://github.com/eclipse-zenoh/zenoh-pico)

### MCP
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [FastMCP Python SDK](https://github.com/jlowin/fastmcp)

### Hardware Detection
- Apple `sysctl` keys: `hw.perflevel0/1`, `machdep.cpu.brand_string`, `hw.cachelinesize`
- Linux `/proc/cpuinfo`, `/sys/devices/system/cpu/`, `/sys/class/thermal/`
- [psutil documentation](https://psutil.readthedocs.io/)

### Build & Compilation
- [Arm compiler flags reference](https://developer.arm.com/documentation/101754/latest)
- `-mcpu` targets: `apple-m1`, `apple-m2`, `apple-m3`, `apple-m4`, `cortex-a76`, `cortex-a78`, `neoverse-v2`

### Hackathon
- [Arm Create AI Optimization Challenge 2026](https://arm-ai-optimization-challenge.devpost.com)
- [Arm Developer Program](https://developer.arm.com)
- [Arm Performix](https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Studio)

---

*This document supersedes the original PRD v2. It incorporates hackathon strategy, judging criteria alignment, and a production build plan optimized for the Aug 14, 2026 deadline.*
