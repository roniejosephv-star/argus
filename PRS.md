# PRS — Argus Project Requirement Specification v3

## Arm-Native MCP-Enabled ROS 2 Diagnostic & Optimization Platform

| | |
|---|---|
| **Project** | Argus |
| **Document** | Project Requirement Specification (PRS) |
| **Based on** | PRD v3 (2026-07-10) |
| **Status** | v3 — Production PRS (hackathon-aligned) |
| **Last updated** | 2026-07-10 |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Module Specifications](#2-module-specifications)
3. [Reporting Module](#3-reporting-module)
4. [Permission Gatekeeper](#4-permission-gatekeeper)
5. [Tool Specifications](#5-tool-specifications)
6. [MCP Server Specification](#6-mcp-server-specification)
7. [Data Models](#7-data-models)
8. [Directory Structure](#8-directory-structure)
9. [Dependencies](#9-dependencies)
10. [CLI Reference](#10-cli-reference)

---

## 1. System Architecture

### 1.1 High-Level Architecture

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
│  │   report                  │  │  │ HTTP  ← Antigravity/Web   │  │  │
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
│  │  │report  │  │        │  │_all*   │  │apply_  │  │dd/mkfs│  │     │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └───────┘  │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                          │                                            │
│                          ▼ (approved tools only)                      │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                      SHARED CORE ENGINE                         │ │
│  │                                                                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐       │ │
│  │  │profiler  │ │stresser  │ │ram_sampler│ │  assess      │       │ │
│  │  │.py       │ │.py       │ │.py        │ │  .py         │       │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘       │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │                    optimizer.py                           │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────┐ ┌──────────────┐ ┌───────────────────────────┐   │ │
│  │  │models.py │ │ toolbox.py   │ │  state/ (report module)   │   │ │
│  │  │Pydantic  │ │ TOOL_REGISTRY│ │  report.py, report_store  │   │ │
│  │  │schemas   │ │ execute()    │ │  knowledge.py             │   │ │
│  │  └──────────┘ └──────────────┘ └───────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Modes

| Mode | Entry | Purpose | LLM Required? |
|---|---|---|---|
| CLI | `argus <command>` | Direct hardware profiling, stress testing, assessment, config generation, reporting | No |
| MCP Server | `argus mcp serve` | Expose all tools via stdio + HTTP for any MCP client | No (client brings LLM) |
| Standalone Agent | `argus agent` | Autonomous agent with Gemini | Yes (deferred to Phase 2) |

### 1.3 Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | ROS 2 ecosystem, FastMCP, rapid development |
| MCP Framework | FastMCP v3+ | Dual transport, decorator tools, dominant Python MCP lib |
| CLI Framework | `click` | Battle-tested, type hints, composable commands |
| Data Validation | `pydantic` v2 | Structured I/O, JSON serialization, type safety |
| HW Detection | `psutil` + OS-native (`sysctl`/`/proc`) | No fragile compiled deps; `pyhwloc` optional |
| Stress Engine | Python-first (`numpy` + `multiprocessing`) | Zero-compile install, ~85-95% of C perf |
| Safety | Permission Gatekeeper in toolbox | All tool calls pass through blast-radius gate |
| Templating | F-strings / string formatting | Simple, no external engine needed |
| Report Storage | `./argus-reports/` dir (project-local) | Scoped to project, git-ignorable or committable |

---

## 2. Module Specifications

### 2.1 `core/profiler.py` — Arm Hardware Detection

```python
def detect_arm_soc(detailed: bool = False) -> dict:
    """Detect Arm SoC capabilities.

    macOS: sysctl hw.*, platform, psutil
    Linux: /proc/cpuinfo, /sys/devices/system/cpu/, psutil, optional pyhwloc

    Returns:
        os, arch, model, p_cores, e_cores, total_cores,
        total_ram_gb, available_ram_gb,
        neon, sve, sve2, lse,
        cache_line_size, l1d_cache, l2_cache, l3_cache,
        has_preempt_rt, compiler_target, fingerprint
    """

def get_cache_line_size() -> int:
    """macOS: sysctl hw.cachelinesize → 128 (Apple Silicon)
    Linux: /sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size → 64
    Fallback: 64"""

def get_compiler_target() -> str:
    """macOS: machdep.cpu.brand_string → apple-m1/2/3/4
    Linux: /proc/cpuinfo CPU part → cortex-a76, neoverse-v2
    Fallback: 'native'"""
```

### 2.2 `core/stresser.py` — Stress Testing

```python
def stress_cpu(duration_s: int = 10, workers: int | None = None) -> dict:
    """multiprocessing + numpy float ops.
    Returns: {bogo_ops_s, avg_temp_c, workers, duration_s}"""

def stress_memory(duration_s: int = 10, array_size_mb: int = 256) -> dict:
    """STREAM-like: copy, scale, add, triad via numpy.
    Returns: {copy_mbps, scale_mbps, add_mbps, triad_mbps}"""

def stress_thermal(duration_s: int = 30) -> dict:
    """Combined CPU+memory load with sensor polling.
    macOS: powermetrics/IOKit, Linux: /sys/class/thermal/
    Returns: {peak_temp_c, thermal_throttled, avg_temp_c, samples}"""
```

### 2.3 `core/ram_sampler.py` — RAM Measurement

```python
def sample_ram(pid: int | None = None, interval_s: float = 1.0,
               duration_s: int = 10) -> dict:
    """psutil-based per-process or system RAM sampling.
    Returns: {samples[{rss_kb, vms_kb, timestamp}],
              avg_rss_kb, peak_rss_kb,
              system_total_kb, system_available_kb}"""
```

### 2.4 `core/assess.py` — Hardware Assessment

```python
def assess_hardware(profile: dict, stress_results: dict | None = None) -> dict:
    """5-tier scorecard (0-100).

    Tiers: ros-desktop > ros-base-full > ros-base > micro-ros > zenoh-pico

    Score breakdown:
      RAM: 30pts, Compute: 20pts, ISA: 15pts,
      Cache: 10pts, Thermal: 10pts, RT: 15pts

    Returns: {tier, score, breakdown, rationale,
              recommended_rmw, dds_profile, ros2_distro, warnings}"""
```

### 2.5 `core/optimizer.py` — Config Generation

```python
def generate_cyclonedds_xml(profile: dict, dds_profile: str = "balanced") -> str
def generate_fastdds_xml(profile: dict, dds_profile: str = "balanced") -> str
def generate_zenoh_advice(profile: dict) -> str
def generate_sysctl_config(profile: dict) -> str
def generate_build_flags(profile: dict) -> dict
def generate_install_script(profile: dict, tier: str, rmw: str) -> str
def generate_all_configs(profile: dict, scorecard: dict, output_dir: str) -> dict
```

### 2.6 `core/toolbox.py` — Tool Registry

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    category: str                    # discover | profile | tune | verify | system | report
    blast_radius: str                # none | low | medium | high | critical
    timeout_s: int
    parameters: type[BaseModel]
    handler: Callable

TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tool(spec: ToolSpec) -> None
def execute_tool(name: str, args: dict) -> Any
    """Routes through Permission Gatekeeper before execution."""
def get_mcp_tool_definitions() -> list[dict]
def get_tool_list() -> list[dict]
```

### 2.7 `core/models.py` — Pydantic Data Models

See Section 7 for full model definitions.

### 2.8 `safety/gatekeeper.py` — Permission Gatekeeper

See Section 4.

### 2.9 `safety/blast_radius.py` — Blast Radius Classification

See Section 4.

### 2.10 `safety/blocklist.py` — Command Blocklist

See Section 4.

### 2.11 `mcp/server.py` — FastMCP Server

See Section 6.

### 2.12 `mcp/transports.py` — Transport Configuration

See Section 6.

### 2.13 `mcp/auth.py` — Bearer Token Auth

See Section 6.

### 2.14 `mcp/resources.py` — Resource URIs and Prompts

See Section 6.

### 2.15 `state/report.py`, `state/report_store.py`, `state/knowledge.py` — Reporting Module

See Section 3.

---

## 3. Reporting Module

### 3.1 Purpose

The reporting module captures a full device state baseline **before** any changes, and again **after** changes are applied. The agent (or user) diffs pre/post reports to see impact, and extracts lessons that make future recommendations better over time.

### 3.2 Data Flow

```
start project
  → generate_report(reason="pre_assess")  ← full baseline
  → make changes (generate configs, install, tune)
  → generate_report(reason="post_assess") ← post-change state
  → diff_reports(pre, post)
    → "Before: MaxMessageSize=65535 → After: 262144"
    → "Before: NO DDS config → After: cyclonedds.xml"
    → "Before: 1200MB RAM used → After: 1350MB (+150MB overhead)"
  → extract_lessons(pre, post, diff)
    → Lesson("M3 Pro 36GB benefits from 256KB MaxMessageSize")
    → Lesson("RAM overhead of tuned config is <5%, acceptable")
  → store in knowledge base (lessons.json)
  → next project on similar HW references past lessons
```

### 3.3 Module: `state/report.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
import uuid

class HardwareSnapshot(BaseModel):
    model: str
    p_cores: int
    e_cores: int
    total_ram_gb: float
    available_ram_gb: float
    cache_line_size: int
    compiler_target: str
    fingerprint: str

class OSSnapshot(BaseModel):
    os: str
    arch: str
    kernel_version: str
    distro: str | None = None
    has_preempt_rt: bool = False
    uptime_hours: float
    kernel_params: dict[str, str] = {}

class ROS2Snapshot(BaseModel):
    installed: bool = False
    distro: str | None = None
    rmw: str | None = None
    packages: list[str] = []
    workspace_path: str | None = None
    active_nodes: list[str] = []
    active_topics: list[str] = []
    domain_id: int | None = None

class ConfigSnapshot(BaseModel):
    has_cyclonedds_xml: bool = False
    cyclonedds_xml_path: str | None = None
    has_fastdds_xml: bool = False
    fastdds_xml_path: str | None = None
    has_zenoh_config: bool = False
    zenoh_config_path: str | None = None
    has_sysctl_ros_conf: bool = False
    rmw_implementation: str | None = None
    ros_domain_id: int | None = None

class PerformanceSnapshot(BaseModel):
    cpu_bogo_ops_s: float | None = None
    memory_copy_mbps: float | None = None
    memory_scale_mbps: float | None = None
    memory_add_mbps: float | None = None
    memory_triad_mbps: float | None = None
    peak_temp_c: float | None = None
    thermal_throttled: bool | None = None
    ram_used_kb: int | None = None
    ram_available_kb: int | None = None
    swap_used_kb: int | None = None

class DiskSnapshot(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    top_processes_ram: list[dict] = []
    top_processes_cpu: list[dict] = []

class Report(BaseModel):
    """Complete device state snapshot at a point in time."""
    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=datetime.now)
    argus_version: str = "unknown"
    reason: str = "manual"           # manual | pre_assess | post_assess | pre_tool | agent_project_start
    metadata: dict = {}

    hardware: HardwareSnapshot
    os: OSSnapshot
    ros2: ROS2Snapshot
    configs: ConfigSnapshot
    performance: PerformanceSnapshot | None = None
    disk: DiskSnapshot | None = None

class ReportDiff(BaseModel):
    """Structural diff between two reports."""
    report_before_id: str
    report_after_id: str
    timestamp_before: datetime
    timestamp_after: datetime
    fingerprint: str

    hardware_changed: bool = False
    os_changed: bool = False
    ros2_changed: bool = False
    configs_changed: bool = False
    performance_changed: bool = False

    configs_added: list[str] = []
    configs_removed: list[str] = []
    configs_modified: list[dict] = []
    ros2_packages_added: list[str] = []
    ros2_packages_removed: list[str] = []

    cpu_bogo_ops_delta_pct: float | None = None
    memory_bandwidth_delta_pct: float | None = None
    ram_usage_delta_kb: int | None = None
    temp_delta_c: float | None = None

    summary: str

class Lesson(BaseModel):
    """Learned insight from a pre/post diff cycle."""
    lesson_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    fingerprint: str
    hardware_model: str
    description: str
    category: Literal["dds", "sysctl", "build_flags", "rmw", "tier", "general"]
    confidence: float = 0.5
    tags: list[str] = []
```

### 3.4 Module: `state/report_store.py`

```python
REPORT_DIR = "./argus-reports/"
LESSONS_FILE = "./argus-reports/lessons.json"

def save_report(report: Report) -> str
    """Write JSON to ./argus-reports/<fingerprint>/<timestamp>.json"""

def load_report(report_id_or_path: str) -> Report
    """Load by ID (searches all fingerprints) or path."""

def list_reports(fingerprint: str | None = None) -> list[Report]
    """List reports, optionally filtered by fingerprint."""

def latest_report(fingerprint: str) -> Report | None
    """Most recent report for a device."""

def diff_reports(before: Report, after: Report) -> ReportDiff
    """Structural diff — computes all deltas."""

def save_lesson(lesson: Lesson) -> None
    """Append lesson to lessons.json."""

def get_lessons(fingerprint: str | None = None,
                category: str | None = None) -> list[Lesson]
```

### 3.5 Module: `state/knowledge.py`

```python
def extract_lessons(pre: Report, post: Report, diff: ReportDiff) -> list[Lesson]:
    """Analyze pre/post diff and extract structured lessons.

    Heuristics:
    - configs_added + CPU perf improved → lesson about config value
    - configs_added + RAM delta > 10% → lesson about RAM overhead
    - Any config written → lesson about what changed and why
    """

def apply_learned_knowledge(profile_fingerprint: str,
                            recommendations: dict) -> dict:
    """Augment config recommendations with past lessons.
    Returns modified recommendations with confidence scores."""
```

### 3.6 Integration Points

| Trigger | Action | Blast Radius |
|---|---|---|
| `argus assess --report` | Auto-generate PRE report before assessment | None (auto) |
| `argus assess --report` | Auto-generate POST report after configs written | None (auto) |
| `argus report` standalone | Single report for manual inspection | None (auto) |
| MEDIUM/HIGH tool via gatekeeper (optional) | Auto-report before execution | None (configurable) |
| Agent project start (Phase 2) | PRE, changes, POST, diff, lessons | None (auto) |

---

## 4. Permission Gatekeeper

### 4.1 Blast Radius Classification

| Radius | Color | Policy | Tools |
|---|---|---|---|
| None | Green | Auto-approved | `detect_*`, `assess_*`, `generate_*` (string return), `report` |
| Low | Yellow | Auto-approved | `stress_*`, `measure_*` |
| Medium | Orange | Ask user | `generate_all_configs`, `write_config`, `scaffold_*` |
| High | Red | Ask + WARNING | `run_command`, `colcon_build`, `apply_sysctl`, `git_commit` |
| Critical | Black | Always denied | `rm -rf /`, `sudo *`, `dd`, `mkfs`, pipe-to-shell |

### 4.2 Evaluation Order

```
1. Blocklist check → DENY (hard block, logged)
2. Blast radius lookup → APPROVAL_POLICY
3. Default → ASK (unknown tools default to HIGH)
```

### 4.3 Blocklist Patterns

```python
BLOCKLIST_PATTERNS = [
    r"rm\s+-rf\s+/",            # Root deletion
    r"sudo\s+.*",                # Sudo elevation
    r">\s+/dev/",                # Device overwrite
    r"dd\s+if=.*of=.*",         # Raw disk ops
    r"mkfs\.*\s+",              # Filesystem creation
    r":\(\)\{\s*:\s*\|\|:\s*&\s*\};:",  # Fork bomb
    r"curl.*\|\s*(bash|sh)",    # Pipe to shell
    r"wget.*\|\s*(bash|sh)",    # Pipe to shell
]

BLOCKLIST_COMMANDS = [
    "vim", "vi", "nano", "emacs",  # Interactive editors
    "nohup", "gdb", "lldb", "valgrind",  # Background/debug
    "tmux", "screen",               # Session managers
    "reboot", "shutdown", "halt",   # System control
]
```

---

## 5. Tool Specifications

### 5.1 Discover Tools (Blast Radius: None)

| Tool | Params | Returns |
|---|---|---|
| `detect_arm_soc` | `{detailed: bool = false}` | HardwareProfile JSON |
| `detect_os` | `{}` | OS info JSON |

### 5.2 Profile Tools (Blast Radius: Low)

| Tool | Params | Returns |
|---|---|---|
| `stress_cpu` | `{duration_s: 10, workers: null}` | Performance JSON |
| `stress_memory` | `{duration_s: 10, array_size_mb: 256}` | Bandwidth JSON |
| `measure_thermal` | `{}` | Thermal JSON |
| `measure_ram` | `{pid: null, interval_s: 1.0, duration_s: 10}` | RAM profile JSON |

### 5.3 Tune Tools (Blast Radius: None–Low)

| Tool | Params | Returns |
|---|---|---|
| `assess_hardware` | `{}` | Scorecard JSON |
| `generate_cyclonedds_config` | `{profile: "balanced"}` | XML string |
| `generate_fastdds_config` | `{profile: "balanced"}` | XML string |
| `generate_zenoh_advice` | `{}` | Markdown string |
| `generate_sysctl_config` | `{}` | Config string |
| `generate_build_flags` | `{}` | Flags JSON |
| `generate_install_script` | `{}` | Shell script string |
| `generate_all_configs` | `{output_dir: "./configs"}` | File list JSON |

### 5.4 Report Tools (Blast Radius: None)

| Tool | Params | Returns |
|---|---|---|
| `generate_report` | `{reason: str = "manual"}` | Report JSON |
| `diff_reports` | `{before_id: str, after_id: str}` | ReportDiff JSON |
| `list_reports` | `{fingerprint: str \| null}` | List of Report metadata |
| `get_lessons` | `{fingerprint: str \| null, category: str \| null}` | List of Lesson JSON |

---

## 6. MCP Server Specification

### 6.1 Transport Configuration

```python
class TransportConfig:
    mode: Literal["stdio", "http", "both"] = "both"
    host: str = "127.0.0.1"
    port: int = 8765
    auth_token: str | None = None   # From ARGUS_MCP_TOKEN env var
```

| Transport | Default | Auth | Use Case |
|---|---|---|---|
| stdio | ✅ | None (process isolation) | Claude Code, Gemini CLI, Cline |
| Streamable HTTP | ✅ | Bearer token | Antigravity 2.0, web, MCP Inspector |

### 6.2 Resource URIs

```
argus://system/info              → Hardware profile JSON
argus://system/cpu               → CPU topology
argus://system/memory            → RAM info
argus://sensors/temperature      → Live thermal reading
argus://stress/latest            → Most recent stress results
argus://configs/cyclonedds       → Generated CycloneDDS XML
argus://configs/fastdds          → Generated Fast DDS XML
argus://configs/sysctl           → Generated sysctl config
argus://scorecard/latest         → Most recent scorecard
argus://reports/latest           → Most recent report
```

### 6.3 Prompt Templates

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
        "arguments": [{"name": "rmw", "required": False}]
    },
    "debug-thermal": {
        "description": "Run thermal stress test and analyze throttling risk",
        "arguments": []
    },
}
```

### 6.4 Auth Strategy (3-Tier)

| Phase | Transport | Auth |
|---|---|---|
| MVP | stdio | None (process isolation) |
| MVP | HTTP | Bearer token (`ARGUS_MCP_TOKEN`) |
| Phase 3 | HTTP | OAuth 2.1 + PKCE |

### 6.5 Gemini CLI Integration

A standalone script (`scripts/argus_mcp_gemini.py`) connects Gemini directly to Argus tools in-process, bypassing the MCP server. Tools from `argus.core.toolbox` are converted to Gemini function declarations.

**System prompt**:
```text
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

**Flow**: Single prompt → Gemini selects tool sequence → `execute_tool()` called in-process → natural language response returned. No MCP subprocess. Gatekeeper bypassed (operator is the user).

**Fallback**: If Gemini API fails, use `argus mcp serve` with MCP Inspector or Claude Code native MCP.

---

## 7. Data Models

### 7.1 Pydantic Models (`core/models.py`)

```python
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
    model: str
    total_ram_gb: float
    total_cores: int
    cache_line_size: int
    arch: str
    hash: str
```

(Reporting models are defined in Section 3.3 — `state/report.py`.)

---

## 8. Directory Structure

```
argus/                           # Repository root
├── pyproject.toml               # Project metadata, deps, scripts
├── LICENSE                      # MIT
├── README.md                    # Hackathon-grade documentation
├── scripts/
│   └── argus_mcp_gemini.py      # Gemini CLI integration wrapper
├── argus/                       # Python package
│   ├── __init__.py              # Version, package metadata
│   ├── __main__.py              # python -m argus entry point
│   ├── cli.py                   # Click CLI dispatcher
│   ├── core/                    # Shared business logic
│   │   ├── __init__.py
│   │   ├── profiler.py          # Arm hardware detection
│   │   ├── stresser.py          # CPU/memory/thermal stress
│   │   ├── ram_sampler.py       # Per-process + system RAM
│   │   ├── assess.py            # 5-tier scorecard
│   │   ├── optimizer.py         # Config generation
│   │   ├── models.py            # Pydantic data models
│   │   └── toolbox.py           # Tool registry + dispatcher
│   ├── safety/                  # Permission & safety layer
│   │   ├── __init__.py
│   │   ├── gatekeeper.py        # Permission gate
│   │   ├── blast_radius.py      # Tool classification
│   │   └── blocklist.py         # Blocked command patterns
│   ├── mcp/                     # MCP server implementation
│   │   ├── __init__.py
│   │   ├── server.py            # FastMCP server
│   │   ├── transports.py        # Transport configuration
│   │   ├── auth.py              # Bearer token middleware
│   │   └── resources.py         # Resource URIs + prompts
│   ├── state/                   # Reporting module
│   │   ├── __init__.py
│   │   ├── report.py            # Report/ReportDiff/Lesson models
│   │   ├── report_store.py      # Save/load/list/diff reports
│   │   └── knowledge.py         # Extract lessons from diffs
├── configs/                     # Generated output
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
    ├── test_report.py
    └── fixtures/
        ├── sysctl_m3pro.txt
        ├── sysctl_m1.txt
        ├── cpuinfo_pi5.txt
        ├── cpuinfo_jetson.txt
        └── thermal_zones/
```

---

## 9. Dependencies

### 9.1 Required

| Package | Version | License | Purpose |
|---|---|---|---|
| `click` | >=8.0 | BSD-3 | CLI framework |
| `psutil` | >=5.9 | BSD-3 | System monitoring |
| `numpy` | >=1.24 | BSD-3 | Stress computations |
| `pydantic` | >=2.0 | MIT | Data validation |
| `fastmcp` | >=3.0 | MIT | MCP server |
| `rich` | >=13.0 | MIT | Terminal output formatting |
| `pyyaml` | >=6.0 | MIT | YAML config output |

### 9.2 Optional

| Package | Version | License | Purpose |
|---|---|---|---|
| `pyhwloc` | >=2.0 | BSD-3 | Hardware topology enrichment |
| `stress-ng` | (system) | GPL-2 | External stress tool (not bundled) |
| `google-genai` | >=1.0 | Apache 2.0 | Gemini CLI wrapper (`scripts/argus_mcp_gemini.py`) |

---

## 10. CLI Reference

```
argus diagnose [--detailed]
    Profile Arm SoC and print hardware capabilities.

argus stress [--duration N] [--workers N]
    Run CPU/memory/thermal stress tests.

argus ram [--pid N] [--interval N] [--duration N]
    Sample RAM usage of a process or system.

argus assess [--output-dir PATH] [--report]
    Generate ROS 2 scorecard and config artifacts.
    --report  Auto-generate pre/post baseline reports.

argus report [--diff <id1> <id2>] [--list] [--lessons]
    Generate or inspect device state reports.
    --diff     Show structural diff between two reports.
    --list     List all saved reports.
    --lessons  Show extracted lessons.

argus mcp serve [--transport stdio|http] [--port N] [--host HOST]
    Start MCP server exposing all tools.

argus agent "<prompt>"
    (Phase 2) Start autonomous agent with Gemini.

python scripts/argus_mcp_gemini.py "<prompt>"
    Run single-prompt Gemini session with all Argus tools available.
    Requires ARGUS_GEMINI_KEY environment variable.

argus --version
    Print version and build info.
```
