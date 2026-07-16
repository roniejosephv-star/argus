# Argus — Implementation Specification v1.0

**Consolidated from:** PRD v3, PRS v3, Architecture, API Reference, Data Schema, Phase Build Plan  
**Status:** Implementation Reference (Single Source of Truth)  
**Date:** 2026-07-10

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Directory Structure](#2-directory-structure)
3. [Dependencies](#3-dependencies)
4. [Core Data Models](#4-core-data-models)
5. [Module Specifications](#5-module-specifications)
6. [Tool Registry & Safety](#6-tool-registry--safety)
7. [MCP Server](#7-mcp-server)
8. [Reporting System](#8-reporting-system)
9. [CLI Reference](#9-cli-reference)
10. [File & Data Formats](#10-file--data-formats)
11. [Cross-Platform Strategy](#11-cross-platform-strategy)
12. [Build Plan & Milestones](#12-build-plan--milestones)
13. [Testing Strategy](#13-testing-strategy)

---

## 1. Project Overview

### 1.1 Purpose

Argus is an **Arm-native MCP-enabled diagnostic and optimization platform for ROS 2**. It profiles Arm hardware (CPU, memory, thermal, ISA features), assesses suitability across 5 ROS 2 variant tiers, generates optimized configuration artifacts (DDS, sysctl, build flags), and exposes all capabilities via MCP for AI agent integration.

### 1.2 Modes of Operation

| Mode | Entry Point | Transport | Use Case |
|------|-------------|-----------|----------|
| **CLI** | `argus <cmd>` | Local process | Interactive diagnostics & optimization |
| **MCP Server** | `argus mcp serve` | stdio + HTTP | AI agent integration (Claude Code, Antigravity, etc.) |
| **Gemini Wrapper** | `scripts/argus_mcp_gemini.py` | In-process | Standalone Gemini optimization agent |

### 1.3 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | ROS 2 ecosystem, FastMCP requirement |
| MCP Framework | FastMCP v3+ | Dual transport, decorator-based tools |
| CLI Framework | Click | Type hints, composable commands |
| Validation | Pydantic v2 | Structured I/O, JSON serialization |
| HW Detection | psutil + OS-native (sysctl/proc) | No fragile compiled deps; pyhwloc optional |
| Stress Engine | Python (numpy + multiprocessing) | Zero-compile install, ~85-95% native perf |
| Safety | Permission Gatekeeper in toolbox | All tool calls pass through blast-radius gate |
| Config Templates | F-strings / string formatting | Simple, no external template engine |
| State | `./configs/{soc}/` + `./argus-reports/` | Reproducible artifacts, project-local |

---

## 2. Directory Structure

```
argus/
├── pyproject.toml
├── LICENSE
├── README.md
├── IMPLEMENTATION_SPEC.md     # THIS FILE
├── scripts/
│   └── argus_mcp_gemini.py    # Gemini CLI wrapper
├── argus/
│   ├── __init__.py            # __version__ = "0.1.0"
│   ├── __main__.py            # python -m argus entry
│   ├── cli.py                 # Click CLI dispatcher
│   ├── core/
│   │   ├── __init__.py
│   │   ├── profiler.py        # Arm hardware detection
│   │   ├── stresser.py        # CPU/memory/thermal stress
│   │   ├── ram_sampler.py     # Per-process + system RAM
│   │   ├── assess.py          # 5-tier scorecard
│   │   ├── optimizer.py       # Config generation (7 artifacts)
│   │   ├── models.py          # Pydantic data models
│   │   └── toolbox.py         # Tool registry + dispatcher
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── gatekeeper.py      # Permission gate: Deny->Ask->Allow
│   │   ├── blast_radius.py    # Classification: none/low/med/high/critical
│   │   └── blocklist.py       # Blocked command patterns
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # FastMCP server factory
│   │   ├── transports.py      # Stdio + HTTP config
│   │   ├── auth.py            # Bearer token middleware
│   │   └── resources.py       # Resource URIs + prompts
│   └── state/
│       ├── __init__.py
│       ├── report.py          # Report/Diff/Lesson models
│       ├── report_store.py    # Persistence
│       └── knowledge.py       # Lesson extraction
├── configs/                   # Generated output (git-ignored)
│   └── {soc_model}/
│       ├── metadata.yaml
│       ├── cyclonedds.xml
│       ├── fastdds.xml
│       ├── zenoh_advice.yaml
│       ├── sysctl.conf
│       ├── build_flags.json
│       └── install_ros2.sh
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

## 3. Dependencies

### 3.1 pyproject.toml

```toml
[project]
name = "argus"
version = "0.1.0"
description = "Arm-native ROS 2 diagnostic & optimization platform"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "psutil>=5.9",
    "numpy>=1.26",
    "fastmcp>=3.0",
    "httpx>=0.27",
    "rich>=13.7",
    "pyyaml>=6.0",
    "google-genai>=1.0",        # Optional: for Gemini wrapper
]
[project.optional-dependencies]
full = [
    "pyhwloc>=2.0",             # Optional NUMA/cache topology
    "stress-ng>=0.1",           # Optional native stress backend
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "ruff>=0.4",
    "mypy>=1.10",
    "black>=24.0",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
```

---

## 4. Core Data Models

All models in `argus/core/models.py` (Pydantic v2 `BaseModel`).

### 4.1 HardwareProfile

```python
class HardwareProfile(BaseModel):
    os: str                     # "darwin" | "linux"
    arch: str                   # "arm64" | "aarch64"
    model: str                  # "Apple M3 Pro", "BCM2712", "Jetson Orin"
    p_cores: int                # Performance cores
    e_cores: int                # Efficiency cores
    total_cores: int            # Logical cores
    total_ram_gb: float
    available_ram_gb: float
    neon: bool = True           # Always true on arm64
    sve: bool = False
    sve2: bool = False
    lse: bool = False           # Large System Extensions (atomics)
    cache_line_size: int        # 64 (standard) or 128 (Apple)
    l1d_cache: str | None = None
    l2_cache: str | None = None
    l3_cache: str | None = None
    has_preempt_rt: bool = False
    compiler_target: str        # "apple-m3", "cortex-a76", "neoverse-v2", "native"
    fingerprint: str            # SHA-256 hex (64 chars)
```

### 4.2 StressResults

```python
class StressResults(BaseModel):
    cpu_bogo_ops_s: float | None = None
    memory_copy_mbps: float | None = None
    memory_scale_mbps: float | None = None
    memory_add_mbps: float | None = None
    memory_triad_mbps: float | None = None
    peak_temp_c: float | None = None
    thermal_throttled: bool | None = None
    avg_temp_c: float | None = None
    samples: list[dict] = []
```

### 4.3 Scorecard

```python
class Scorecard(BaseModel):
    tier: Literal["ros-desktop", "ros-base-full", "ros-base", "micro-ros", "zenoh-pico"]
    score: int = Field(ge=0, le=100)
    breakdown: dict[str, float]       # ram, compute, isa, cache, thermal, rt
    rationale: str
    recommended_rmw: Literal["cyclonedds", "fastdds", "zenoh"]
    dds_profile: Literal["low-latency", "high-throughput", "balanced", "low-memory"]
    ros2_distro: str = "jazzy"
    warnings: list[str] = []
```

### 4.4 Config Artifacts

```python
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
```

### 4.5 Report Models (`argus/state/report.py`)

```python
class Report(BaseModel):
    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: Literal["assess", "diagnose", "stress", "manual"]
    hardware: HardwareSnapshot
    os: OSSnapshot
    ros2: ROS2Snapshot
    performance: PerformanceSnapshot | None = None
    disk: DiskSnapshot | None = None
    configs: ConfigSnapshot
    scorecard: Scorecard | None = None
    lessons: list[Lesson] = []
    pre_report_id: str | None = None
    diff: ReportDiff | None = None

class Lesson(BaseModel):
    lesson_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=datetime.now)
    fingerprint: str
    hardware_model: str
    description: str
    category: Literal["dds", "sysctl", "build_flags", "rmw", "tier", "general"]
    benefit: str
    tradeoff: str
    confidence: float = Field(ge=0, le=100, default=50)
    tags: list[str] = []
    diff_summary: str = ""
```

---

## 5. Module Specifications

### 5.1 `core/profiler.py` — Arm Hardware Detection

#### Public API

```python
def detect_arm_soc(detailed: bool = False) -> HardwareProfile:
    """Main entry: detects SoC capabilities on macOS or Linux."""

def get_cache_line_size() -> int:
    """macOS: sysctl hw.cachelinesize (128 on Apple Silicon)
    Linux: /sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size (64)"""

def get_compiler_target() -> str:
    """macOS: map machdep.cpu.brand_string -> apple-m1/2/3/4
    Linux: map /proc/cpuinfo CPU part -> cortex-a76, neoverse-v2, etc.
    Fallback: 'native'"""
```

#### macOS Backend (Day 2 - M2a)

```python
# Key sysctl queries
SYSCTL_QUERIES = {
    "model": "machdep.cpu.brand_string",
    "p_cores": "hw.perflevel0.logicalcpu",
    "e_cores": "hw.perflevel1.logicalcpu",
    "total_cores": "hw.ncpu",
    "total_ram": "hw.memsize",
    "cache_line": "hw.cachelinesize",
    "l1d_cache": "hw.l1dcachesize",
    "l2_cache": "hw.l2cachesize",
    "neon": "hw.optional.neon",
    "lse": "hw.optional.arm.FEAT_LSE",
}
```

#### Linux Backend (Day 3 - M2b)

```python
# Sources:
# - /proc/cpuinfo          -> CPU implementer, part, variant, revision, features
# - /sys/devices/system/cpu/ -> online CPUs, frequencies, cache topology
# - /sys/class/thermal/    -> thermal zones
# - /proc/device-tree/model -> board model (Pi, Jetson)
# - /proc/meminfo          -> RAM
# - uname -r + /proc/config.gz -> PREEMPT_RT detection
```

#### CPU Part -> Compiler Target Mapping

| CPU Part | Implementer | Target |
|----------|-------------|--------|
| 0xD03-0xD08 | 0x41 (ARM) | cortex-a76 |
| 0xD0A-0xD0C | 0x41 | cortex-a78 |
| 0xD40-0xD4F | 0x41 | neoverse-v2 |
| 0xD80-0xD8F | 0x41 | neoverse-v3 |
| 0xD47 | 0x41 | cortex-a78ae |
| 0xD0D | 0x41 | cortex-x1 |
| Custom | Apple | apple-m1/2/3/4 |

#### Fingerprint Algorithm

```python
def compute_fingerprint(profile: HardwareProfile) -> str:
    data = {
        "implementer": profile.get("implementer", ""),
        "part": profile.get("part", ""),
        "variant": profile.get("variant", 0),
        "revision": profile.get("revision", 0),
        "total_ram_kb": int(profile.total_ram_gb * 1024 * 1024),
        "board_model": profile.get("board_model", ""),
        "cache_line_size": profile.cache_line_size,
    }
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode()).hexdigest()
```

---

### 5.2 `core/stresser.py` — Stress Testing

```python
def stress_cpu(duration_s: int = 10, workers: int | None = None) -> StressResults:
    """multiprocessing.Pool + numpy float64 matmul/prime sieve.
    Returns: bogo_ops_s, avg_temp_c, peak_temp_c, workers, duration_s"""

def stress_memory(duration_s: int = 10, array_size_mb: int = 256) -> StressResults:
    """STREAM-like: copy, scale(*3), add(a+b), triad(a+3*b) via numpy.
    Returns: copy/scale/add/triad_mbps"""

def stress_thermal(duration_s: int = 30) -> StressResults:
    """Combined CPU+mem load + thermal polling.
    macOS: powermetrics (sudo) or IOKit
    Linux: /sys/class/thermal/thermal_zone*/temp
    Returns: peak_temp_c, thermal_throttled, avg_temp_c, samples[]"""

def measure_thermal() -> dict:
    """Single thermal reading.
    Returns: temp_c, sensor_count, sensors[{name, temp_c}]"""
```

**Thermal Backend Priority:**
1. macOS: `powermetrics --samplers smc` (requires sudo) -> fallback: IOKit HID
2. Linux: `/sys/class/thermal/thermal_zone*/temp`
3. None: return `None` for thermal fields, continue

---

### 5.3 `core/ram_sampler.py` — RAM Measurement

```python
def sample_ram(pid: int | None = None, interval_s: float = 1.0, duration_s: int = 10) -> dict:
    """psutil.Process(pid).memory_info() or psutil.virtual_memory()
    Returns: samples[{rss_kb, vms_kb, timestamp}], avg_rss_kb, peak_rss_kb,
             system_total_kb, system_available_kb"""
```

---

### 5.4 `core/assess.py` — Hardware Assessment

```python
def assess_hardware(profile: HardwareProfile, stress: StressResults | None = None) -> Scorecard:
    """5-tier scorecard (0-100).
    
    Tier thresholds (RAM-primary, compute-secondary):
      > 4GB RAM, >= 8 cores:     ros-desktop     (full ROS 2 desktop)
      2-4GB RAM, >= 4 cores:     ros-base-full   (ros-base + key extras)
      512MB-2GB RAM:             ros-base        (minimal ROS 2)
      256-512MB RAM:             micro-ros       (micro-ROS agent)
      < 256MB RAM or MCU:        zenoh-pico      (Zenoh-pico only)
    
    Score breakdown (100 pts):
      RAM capacity:      30 pts  (linear 128MB->0, 8GB->30)
      Compute (cores):   20 pts  (cores + ISA)
      ISA features:      15 pts  (NEON=5, SVE=5, LSE=5)
      Cache:             10 pts  (L2/L3 size)
      Thermal headroom:  10 pts  (from stress or estimated)
      RT capability:     15 pts  (PREEMPT_RT + isolated cores)
    
    Returns Scorecard with tier, score, rationale, recommended_rmw, dds_profile"""
```

**RMW Selection Logic:**
- RAM >= 4GB, cores >= 4 -> `cyclonedds` (balanced)
- RAM < 2GB -> `zenoh` (lower overhead)
- RT required -> `fastdds` (better RT support)

**DDS Profile Selection:**
- Low latency (control loops) -> `low-latency`
- High throughput (sensors) -> `high-throughput`
- Default -> `balanced`
- Low memory -> `low-memory`

---

### 5.5 `core/optimizer.py` — Config Generation

```python
def generate_cyclonedds_xml(profile: HardwareProfile, dds_profile: str = "balanced") -> str:
    """Parameters scaled by RAM & cores:
    - MaxMessageSize: scaled by available RAM
    - SocketReceiveBufferSize: 64KB-2MB based on RAM
    - WhcHigh/WhcLow: scaled by RAM
    - FragmentSize: aligned to cache_line_size (64 or 128)
    - MaxAutoParticipantIndex: scaled by core count
    Profiles: balanced, low-latency, high-throughput, low-memory"""

def generate_fastdds_xml(profile: HardwareProfile, dds_profile: str = "balanced") -> str:
    """Parameters: sendBufferSize, receiveBufferSize, maxMessageSize,
    PublishModeQosPolicy, HistoryMemoryPolicy"""

def generate_zenoh_advice(profile: HardwareProfile) -> str:
    """Markdown: when Zenoh > DDS, config templates, multi-device setup,
    Zenoh-pico for MCU, rmw_zenoh for ROS 2"""

def generate_sysctl_config(profile: HardwareProfile) -> str:
    """net.core.rmem_max, net.core.wmem_max, net.ipv4.ipfrag_time,
    net.ipv4.ipfrag_high_thresh, vm.dirty_ratio, kernel.sched_autogroup_enabled"""

def generate_build_flags(profile: HardwareProfile) -> dict:
    """Returns: {cmake_args[], mcpu, march, lto, vectorization}"""

def generate_install_script(profile: HardwareProfile, tier: str, rmw: str) -> str:
    """OS-specific apt/brew install for ROS 2 tier + RMW.
    Based on Arm Learning Path: learn.arm.com/install-guides/ros2/"""

def generate_all_configs(profile: HardwareProfile, scorecard: Scorecard, output_dir: str) -> ConfigArtifact:
    """Writes all 6 configs to configs/{soc_model}/ + metadata.yaml
    Returns ConfigArtifact with file list"""
```

**Output Directory Structure:**
```
configs/{normalized_soc_model}/
├── metadata.yaml        # fingerprint, tier, score, timestamp, artifact list
├── cyclonedds.xml
├── fastdds.xml
├── zenoh_advice.yaml
├── sysctl.conf
├── build_flags.json
└── install_ros2.sh
```

**SOC Model Normalization:** `"Apple M3 Pro"` -> `apple-m3-pro` (lowercase, hyphens)

---

### 5.6 `core/toolbox.py` — Tool Registry & Dispatcher

```python
@dataclass
class ToolSpec:
    name: str                    # snake_case, verb-prefixed
    description: str             # One-sentence LLM-readable
    category: str                # discover | profile | tune | verify | system | report
    blast_radius: BlastRadius    # NONE | LOW | MEDIUM | HIGH | CRITICAL
    timeout_s: int
    parameters: type[BaseModel]  # Pydantic model for validation
    handler: Callable

TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tool(spec: ToolSpec) -> None: ...
def execute_tool(name: str, args: dict) -> Any:
    """1. Validate args against Pydantic model
    2. Route through Permission Gatekeeper
    3. Execute handler
    4. Return result"""
def get_mcp_tool_definitions() -> list[dict]: ...  # FastMCP format
def get_tool_list() -> list[dict]: ...             # Human-readable
```

#### Complete Tool Catalog (18 Tools)

| Tool | Category | Blast Radius | Parameters | Returns |
|------|----------|--------------|------------|---------|
| `detect_arm_soc` | discover | NONE | `{detailed?: bool}` | `HardwareProfile` |
| `detect_os` | discover | NONE | `{}` | OS info |
| `stress_cpu` | profile | LOW | `{duration_s?: int, workers?: int}` | `StressResults` |
| `stress_memory` | profile | LOW | `{duration_s?: int, array_size_mb?: int}` | `StressResults` |
| `measure_thermal` | profile | NONE | `{}` | Thermal reading |
| `measure_ram` | profile | NONE | `{pid?: int, interval_s?: float, duration_s?: int}` | RAM profile |
| `assess_hardware` | tune | NONE | `{}` | `Scorecard` |
| `generate_cyclonedds_config` | tune | NONE | `{dds_profile?: str}` | XML string |
| `generate_fastdds_config` | tune | NONE | `{dds_profile?: str}` | XML string |
| `generate_zenoh_advice` | tune | NONE | `{}` | Markdown string |
| `generate_sysctl_config` | tune | NONE | `{}` | Config string |
| `generate_build_flags` | tune | NONE | `{}` | Flags JSON |
| `generate_install_script` | tune | NONE | `{os?: str, tier?: str}` | Shell script |
| `generate_all_configs` | tune | MEDIUM | `{output_dir?: str}` | `ConfigArtifact` |
| `generate_report` | report | LOW | `{reason?: str}` | `Report` |
| `diff_reports` | report | NONE | `{report_id_1: str, report_id_2: str}` | `ReportDiff` |
| `list_reports` | report | NONE | `{}` | `list[ReportSummary]` |
| `get_lessons` | report | NONE | `{}` | `list[Lesson]` |

---

### 5.7 `core/models.py` — All Pydantic Models

(See Section 4 for complete definitions)

---

## 6. Tool Registry & Safety Layer

### 6.1 Blast Radius Classification (`safety/blast_radius.py`)

```python
class BlastRadius(str, Enum):
    NONE = "none"           # Pure read/compute -- no side effects
    LOW = "low"             # Consumes resources (CPU/RAM) but no persistent changes
    MEDIUM = "medium"       # Writes files, creates directories
    HIGH = "high"           # Shell execution, package install, kernel params
    CRITICAL = "critical"   # Destructive -- always denied

APPROVAL_POLICY: dict[BlastRadius, Literal["auto", "ask", "deny"]] = {
    BlastRadius.NONE:     "auto",
    BlastRadius.LOW:      "auto",
    BlastRadius.MEDIUM:   "ask",
    BlastRadius.HIGH:     "ask",
    BlastRadius.CRITICAL: "deny",
}

TOOL_CLASSIFICATIONS: dict[str, BlastRadius] = {
    # NONE -- pure read/compute
    "detect_arm_soc":              BlastRadius.NONE,
    "detect_os":                   BlastRadius.NONE,
    "assess_hardware":             BlastRadius.NONE,
    "generate_cyclonedds_config":  BlastRadius.NONE,
    "generate_fastdds_config":     BlastRadius.NONE,
    "generate_zenoh_advice":       BlastRadius.NONE,
    "generate_sysctl_config":      BlastRadius.NONE,
    "generate_build_flags":        BlastRadius.NONE,
    "generate_install_script":     BlastRadius.NONE,
    "measure_thermal":             BlastRadius.NONE,
    "measure_ram":                 BlastRadius.NONE,
    "generate_report":             BlastRadius.NONE,
    "diff_reports":                BlastRadius.NONE,
    "list_reports":                BlastRadius.NONE,
    "get_lessons":                 BlastRadius.NONE,
    
    # LOW -- consumes resources
    "stress_cpu":                  BlastRadius.LOW,
    "stress_memory":               BlastRadius.LOW,
    
    # MEDIUM -- writes files
    "generate_all_configs":        BlastRadius.MEDIUM,
    "write_config":                BlastRadius.MEDIUM,
    "scaffold_ros2_package":       BlastRadius.MEDIUM,
    
    # HIGH -- shell execution, system modification
    "run_command":                 BlastRadius.HIGH,
    "colcon_build":                BlastRadius.HIGH,
    "apply_sysctl":                BlastRadius.HIGH,
    "git_commit":                  BlastRadius.HIGH,
}
```

### 6.2 Blocklist (`safety/blocklist.py`)

```python
BLOCKLIST_PATTERNS = [
    r"rm\s+-rf\s+/",           # Root deletion
    r"sudo\s+.*",              # Sudo elevation
    r">\s+/dev/",              # Device overwrite
    r"dd\s+if=.*of=.*",        # Raw disk ops
    r"mkfs\.*\s+",             # Filesystem creation
    r":\(\)\{\s*:\s*\|\|:\s*&\s*\};:",  # Fork bomb
    r"curl.*\|\s*(bash|sh)",   # Pipe to shell
    r"wget.*\|\s*(bash|sh)",
]

BLOCKLIST_COMMANDS = [
    "vim", "vi", "nano", "emacs",  # Interactive editors
    "nohup",                        # Background processes
    "gdb", "lldb", "valgrind",      # Debuggers
    "tmux", "screen",               # Session managers
    "reboot", "shutdown", "halt",   # System control
]

def is_blocked(tool_spec: ToolSpec) -> bool:
    if tool_spec.name != "run_command":
        return False
    command = tool_spec.args.get("command", "")
    for pattern in BLOCKLIST_PATTERNS:
        if re.search(pattern, command):
            return True
    cmd_name = command.strip().split()[0] if command.strip() else ""
    return cmd_name in BLOCKLIST_COMMANDS
```

### 6.3 Gatekeeper (`safety/gatekeeper.py`)

```python
def check_permission(tool_spec: ToolSpec) -> Literal["approved", "ask", "denied"]:
    """1. Blocklist check -> DENY
    2. Blast radius lookup -> APPROVAL_POLICY
    3. Unknown tool -> ASK (defaults to HIGH)"""

def request_user_approval(tool_spec: ToolSpec) -> bool:
    """CLI: Rich-formatted prompt with [y/n/v/a/q]
    MCP: Return permission_required response for client to handle"""
```

**CLI Prompt Format (MEDIUM):**
```
+-----------------------------------------------+
| 🛡️  Permission Required (blast radius: MEDIUM) |
|                                               |
| Tool: generate_all_configs                    |
| Action: Write 6 config files to configs/...   |
|                                               |
| Files to be created:                          |
|   * cyclonedds.xml                            |
|   * fastdds.xml                               |
|   * zenoh_advice.md                           |
|   * sysctl.conf                               |
|   * build_flags.json                          |
|   * install.sh                                |
+-----------------------------------------------+
Proceed? [y/n/v/a/q]:
  y = yes, n = no, v = view files, a = allow all this session, q = quit & show plan
```

**CLI Prompt Format (HIGH):**
```
+-----------------------------------------------+
| 🛡️  Permission Required (blast radius: HIGH)  |
| ⚠️  WARNING: This executes shell commands     |
|                                               |
| Tool: run_command                             |
| Command: sudo sysctl -w net.core.rmem_max=... |
+-----------------------------------------------+
Proceed? [y/n/d/q]:
  d = show detailed reason report
```

---

## 7. MCP Server

### 7.1 Server Factory (`mcp/server.py`)

```python
def create_server() -> FastMCP:
    mcp = FastMCP("argus")
    
    # Register all tools with gatekeeper wrapper
    for tool_spec in get_all_tools():
        @mcp.tool(name=tool_spec.name, description=tool_spec.description)
        async def tool_wrapper(**kwargs) -> Any:
            return execute_tool(tool_spec.name, kwargs)
    
    # Register resources
    for uri, handler in RESOURCE_HANDLERS.items():
        @mcp.resource(uri)
        async def resource_handler() -> str:
            return handler()
    
    # Register prompts
    for name, prompt in PROMPTS.items():
        @mcp.prompt(name=name)
        async def prompt_handler() -> str:
            return prompt
    
    return mcp
```

### 7.2 Transports (`mcp/transports.py`)

```python
class TransportConfig(BaseModel):
    mode: Literal["stdio", "http", "both"] = "both"
    host: str = "127.0.0.1"
    port: int = 8765
    auth_token: str | None = None  # From ARGUS_MCP_TOKEN env var

def run_server(config: TransportConfig):
    if config.mode in ("stdio", "both"):
        # Run stdio transport
    if config.mode in ("http", "both"):
        # Run HTTP with Bearer auth middleware
```

### 7.3 Auth (`mcp/auth.py`)

```python
# HTTP only: validate Authorization: Bearer <token>
# Token from ARGUS_MCP_TOKEN env var
# stdio: no auth (process isolation)
```

### 7.4 Resources (`mcp/resources.py`)

| URI | Returns |
|-----|---------|
| `argus://system/info` | HardwareProfile JSON |
| `argus://system/cpu` | CPU topology |
| `argus://system/memory` | RAM stats |
| `argus://sensors/temperature` | Thermal reading |
| `argus://stress/latest` | Last stress result |
| `argus://configs/cyclonedds` | Generated CycloneDDS XML |
| `argus://configs/fastdds` | Generated Fast DDS XML |
| `argus://configs/sysctl` | Generated sysctl config |
| `argus://scorecard/latest` | Latest Scorecard |
| `argus://reports/latest` | Latest Report |

### 7.5 Prompts (`mcp/resources.py`)

| Prompt | Description |
|--------|-------------|
| `tune-ros2` | Full workflow: profile -> assess -> generate configs |
| `profile-arm` | Profile Arm SoC and explain results |
| `optimize-dds` | Analyze hardware + generate optimal DDS config |
| `debug-thermal` | Run thermal stress + analyze throttling risk |

### 7.6 Client Config Examples

**Claude Code:**
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

**Antigravity / HTTP:**
```bash
export ARGUS_MCP_TOKEN="your-secret-token"
argus mcp serve --transport http --port 8765
# Client connects to http://127.0.0.1:8765/mcp with Bearer token
```

---

## 8. Reporting System (`argus/state/`)

### 8.1 Data Flow

```
start project
  -> generate_report(reason="pre_assess")  <- full baseline
  -> make changes (configs, install, tune)
  -> generate_report(reason="post_assess") <- post-change state
  -> diff_reports(pre, post)
    -> "Before: MaxMessageSize=65535 -> After: 262144"
    -> "Before: NO DDS config -> After: cyclonedds.xml"
  -> extract_lessons(pre, post, diff)
    -> Lesson("M3 Pro 36GB benefits from 256KB MaxMessageSize")
    -> Lesson("RAM overhead of tuned config is <5%")
  -> store in knowledge base (lessons.json)
  -> next project on similar HW references past lessons
```

### 8.2 Storage Layout

```
./argus-reports/
└── {fingerprint[:12]}/
    ├── {YYYYMMDD}-{HHMMSS}-{reason}.json   # Report
    └── lessons.json                         # Append-only lesson store
```

### 8.3 Lesson Extraction Heuristics (`knowledge.py`)

```python
def extract_lessons(pre: Report, post: Report, diff: ReportDiff) -> list[Lesson]:
    lessons = []
    
    # DDS config changes
    if diff.configs_modified:
        for change in diff.configs_modified:
            if "FragmentSize" in change.param:
                lessons.append(Lesson(
                    category="dds",
                    description=f"FragmentSize {change.old}->{change.new} on {pre.hardware.model}",
                    benefit="Reduced DDS latency via cache-line alignment",
                    tradeoff="Slightly higher memory per fragment",
                    confidence=85,
                    tags=["cyclonedds", "cache-line", "latency"],
                ))
    
    # Sysctl changes
    if "vm.dirty_ratio" in diff.changed_params:
        lessons.append(Lesson(...))
    
    # Tier changes
    if pre.scorecard.tier != post.scorecard.tier:
        lessons.append(Lesson(category="tier", ...))
    
    return lessons
```

---

## 9. CLI Reference (`cli.py`)

### 9.1 Command Tree

```
argus
├── diagnose [--detailed] [--json]
├── stress [--duration N] [--workers N] [--json]
├── ram [--pid N] [--interval N] [--duration N] [--json]
├── assess [--output-dir PATH] [--report] [--no-configs] [--json]
├── report
│   ├── --diff ID1 ID2
│   ├── --list
│   ├── --lessons
│   ├── --lesson ID
│   ├── --delete-lesson ID
│   ├── --export-lessons FILE
│   └── --import-lessons FILE
├── mcp serve [--transport stdio|http] [--port N] [--host HOST]
└── --version
```

### 9.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid args, missing deps) |
| 2 | Execution error (tool failed, timeout) |
| 3 | Permission denied (gatekeeper) |
| 4 | Platform unsupported |

### 9.3 Output Formats

- **Default:** Rich tables, progress bars, colored output
- **`--json`:** Machine-readable JSON on stdout

---

## 10. File & Data Formats

### 10.1 `configs/{soc}/metadata.yaml`

```yaml
soc_model: Apple M3 Pro
fingerprint: a1b2c3d4e5f6789012345678abcdef01abcdef01abcdef01abcdef01abcdef01
argus_version: 0.1.0
generated_at: "2026-07-10T14:30:00Z"
tier: ros-desktop
tier_score: 92
artifacts:
  - cyclonedds.xml
  - fastdds.xml
  - zenoh_advice.yaml
  - sysctl.conf
  - build_flags.json
  - install_ros2.sh
```

### 10.2 `configs/{soc}/cyclonedds.xml` (Key Params)

```xml
<CycloneDDS>
  <Domain id="0">
    <Internal>
      <FragmentSize>131072</FragmentSize>        <!-- cache_line * 1024 -->
      <Watermarks>
        <WhcHigh>250000</WhcHigh>                 <!-- scaled by RAM -->
      </Watermarks>
      <AssumeMulticastCapable>true</AssumeMulticastCapable>
    </Internal>
    <Discovery>
      <MaxAutoParticipantIndex>1</MaxAutoParticipantIndex>  <!-- scaled by cores -->
    </Discovery>
  </Domain>
</CycloneDDS>
```

### 10.3 `configs/{soc}/build_flags.json`

```json
{
  "mcpu": "apple-m3",
  "march": "armv8.5-a",
  "lto": true,
  "lto_mode": "auto",
  "vectorization": true,
  "cmake_args": [
    "-DCMAKE_CXX_FLAGS=-mcpu=apple-m3 -O3 -flto=auto",
    "-DCMAKE_C_FLAGS=-mcpu=apple-m3 -O3 -flto=auto"
  ],
  "env": {
    "CFLAGS": "-mcpu=apple-m3 -O3 -flto=auto",
    "CXXFLAGS": "-mcpu=apple-m3 -O3 -flto=auto"
  }
}
```

### 10.4 Report File Naming

```
{YYYYMMDD}-{HHMMSS}-{reason}.json
# e.g., 20260710-143000-assess.json
```

### 10.5 Lessons Storage (`lessons.json`)

```json
{
  "version": 1,
  "count": 3,
  "lessons": [
    {
      "lesson_id": "f1a2b3c4d5e6",
      "timestamp": "2026-07-10T14:31:00Z",
      "fingerprint": "a1b2c3d4e5f6789012345678abcdef01...",
      "hardware_model": "Apple M3 Pro",
      "category": "dds",
      "description": "CycloneDDS fragment size = 128KB for M3 cache line alignment",
      "benefit": "~22% lower DDS latency",
      "tradeoff": "+8% memory usage",
      "confidence": 92,
      "tags": ["cyclonedds", "latency", "cache-line"],
      "diff_summary": "FragmentSize: 65536 -> 131072"
    }
  ]
}
```

---

## 11. Cross-Platform Strategy

### 11.1 Platform Detection

```python
import sys
if sys.platform == "darwin":
    from .profiler_macos import detect_arm_soc_macos
elif sys.platform == "linux":
    from .profiler_linux import detect_arm_soc_linux
else:
    raise NotImplementedError(f"Unsupported platform: {sys.platform}")
```

### 11.2 Detection Backends

| Feature | macOS | Linux |
|---------|-------|-------|
| SoC Model | `sysctl machdep.cpu.brand_string` | `/proc/device-tree/model` or `/proc/cpuinfo` |
| Core Count | `sysctl hw.ncpu` | `nproc` / `/proc/cpuinfo` |
| P/E Cores | `sysctl hw.perflevel0/1.logicalcpu` | `/sys/devices/system/cpu/cpu*/topology/` |
| RAM | `sysctl hw.memsize` | `/proc/meminfo MemTotal` |
| Cache Line | `sysctl hw.cachelinesize` (128) | `getconf LEVEL1_DCACHE_LINESIZE` (64) |
| Thermal | IOKit / `powermetrics` | `/sys/class/thermal/*/temp` |
| ISA Features | `sysctl hw.optional.*` | `/proc/cpuinfo Features` |
| Board Model | `sysctl hw.model` | `/proc/device-tree/model` |
| PREEMPT_RT | N/A | `uname -r` + `/proc/config.gz` |

### 11.3 Optional pyhwloc Enrichment

```python
try:
    import hwloc
    topology = hwloc.Topology()
    # Enrich with NUMA nodes, cache hierarchy depth
except ImportError:
    pass  # Graceful fallback
```

### 11.4 Pre-Generated Configs (Week 4)

Ship in `configs/` for:
- Apple M1, M3 Pro, M4
- Raspberry Pi 4 (BCM2711), Pi 5 (BCM2712)
- Jetson Orin Nano
- Generic Cortex-A76, Neoverse-V2

---

## 12. Build Plan & Milestones

### Phase 1: Core MVP (Weeks 1-2)

| Week | Days | Focus | Gate Criteria |
|------|------|-------|---------------|
| **1** | 1-7 | Foundation | `argus diagnose` + `argus assess` work on Mac |
| **2** | 8-14 | Complete Core | All CLI commands + MCP server (stdio + HTTP) |

#### Week 1 Detail

| Day | Milestone | Deliverables |
|-----|-----------|--------------|
| 1 (Jul 10) | **M1: Scaffold** | `pyproject.toml`, package structure, `__init__.py`, `__main__.py`, `cli.py`, dev env, `.gitignore`, README skeleton |
| 2 (Jul 11) | **M2a: profiler.py (macOS)** | `detect_arm_soc()` with sysctl, `get_cache_line_size()`, `get_compiler_target()`, Apple M1-M4 mapping |
| 3 (Jul 12) | **M2b: profiler.py (Linux)** | Linux backends (`/proc/cpuinfo`, `/sys`), PREEMPT_RT, Cortex/Neoverse mapping, `compute_fingerprint()` |
| 4 (Jul 13) | **M5: models.py + assess.py** | All Pydantic models, 5-tier logic, score computation, rationale, RMW/DDS profile recommendation |
| 5 (Jul 14) | **M6a: optimizer.py (configs)** | CycloneDDS XML, Fast DDS XML, Zenoh advice, sysctl -- all parameterized by hardware |
| 6 (Jul 15) | **M6b: optimizer.py (build/install)** | `generate_build_flags()`, `generate_install_script()`, `generate_all_configs()` orchestrator, `configs/{soc}/` output + `metadata.yaml` |
| 7 (Jul 16) | **M8a: CLI (partial)** | `argus diagnose`, `argus assess` with Click, pretty JSON/table output, `argus --version` |

#### Week 2 Detail

| Day | Milestone | Deliverables |
|-----|-----------|--------------|
| 8 (Jul 17) | **M4a: stresser.py** | `stress_cpu()` (multiprocessing + numpy), `stress_memory()` (STREAM-like), thermal integration |
| 9 (Jul 18) | **M4b: stresser.py + ram_sampler.py** | `stress_thermal()`, `sample_ram()`, thermal backends (macOS IOKit/powermetrics, Linux `/sys/class/thermal`) |
| 10 (Jul 19) | **M7a: toolbox.py + gatekeeper + safety** | `ToolSpec`, `TOOL_REGISTRY`, all 18 tools registered, `execute_tool()` with gatekeeper, `gatekeeper.py`, `blast_radius.py`, `blocklist.py`, FastMCP server factory |
| 11 (Jul 20) | **M7b: MCP transports + reporting** | Stdio + HTTP with Bearer auth, `TransportConfig`, resource URIs, prompt templates, `state/report.py`, `report_store.py`, `knowledge.py` |
| 12 (Jul 21) | **M8b: CLI (complete) + pipeline** | `argus stress`, `argus ram`, `argus report`, `argus mcp serve`, full pipeline: diagnose -> stress -> assess -> report |

### Phase 1.5: Hardening (Weeks 3-4)

| Week | Days | Focus | Gate Criteria |
|------|------|-------|---------------|
| **3** | 15-21 | Polish | E2E tests pass, README complete, MCP Inspector + Gemini wrapper demo |
| **4** | 22-28 | Harden | Linux aarch64 validated (QEMU/real), pre-gen configs shipped, code cleanup |

### Phase 2: Agentic (Post-Hackathon)

- M13: ToolLoopAgent + Gemini
- M14: Pipeline Orchestrator
- M15: MCP Client (connect to external servers)
- M16: Heuristic Diagnostic Engine
- M17: Sub-Agent Spawning

### Phase 3: Production (Post-Hackathon)

- M18: Performance Benchmark Integration
- M19: OAuth 2.1 + PKCE
- M20: Pre-Generated Config Library (20+ boards)
- M21: Demo Video + Devpost Submission

---

## 13. Testing Strategy

### 13.1 Unit Tests

| Module | Test File | Key Tests |
|--------|-----------|-----------|
| `profiler.py` | `test_profiler.py` | macOS sysctl parsing, Linux `/proc` parsing, fingerprint determinism, cache line detection, compiler target mapping |
| `stresser.py` | `test_stresser.py` | CPU stress returns valid bogo-ops, memory stress returns positive MB/s, thermal doesn't crash on missing sensors |
| `ram_sampler.py` | `test_ram_sampler.py` | Samples contain expected fields, peak >= avg, system_available > 0 |
| `assess.py` | `test_assess.py` | Tier thresholds (8GB->desktop, 1GB->base, 128MB->zenoh-pico), score 0-100, rationale non-empty |
| `optimizer.py` | `test_optimizer.py` | CycloneDDS XML valid, Fast DDS XML valid, sysctl values positive, install script contains apt |
| `gatekeeper.py` | `test_gatekeeper.py` | Blast radius classification, blocklist matching, approval flow |

### 13.2 Integration Tests

| Test | Description |
|------|-------------|
| **E2E Pipeline** | `diagnose -> stress -> assess -> generate_configs` -- all stages produce valid output |
| **MCP Stdio** | Connect via stdio, call `detect_arm_soc`, verify JSON response |
| **MCP HTTP** | Connect via HTTP with Bearer token, call tools, verify auth rejection without token |
| **Config Validity** | Parse generated CycloneDDS XML with `xml.etree`, verify schema |
| **Cross-Platform** | Run profiler on macOS and Linux (QEMU), verify both produce valid profiles |

### 13.3 Fixtures

```
tests/fixtures/
├── sysctl_m3pro.txt
├── sysctl_m1.txt
├── cpuinfo_pi5.txt
├── cpuinfo_jetson.txt
└── thermal_zones/
    ├── m3pro_thermal.txt
    └── pi5_thermal.txt
```

---

## 14. Critical Path & Risks

### 14.1 Critical Path

```
M1 (scaffold)
  -> M2 (profiler) <- CRITICAL: everything depends on this
    -> M5 (models + assess)
      -> M6 (optimizer)
        -> M7 (MCP + gatekeeper + report) <- needs all tools + models
          -> M8 (CLI) <- wires everything together
    -> M4 (stress + RAM)
```

### 14.2 Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Profiler fails on real hardware** | Blocks all downstream work | Test on Mac Day 2; use fixtures for Linux CI |
| **FastMCP API changes** | MCP server broken | Pin `fastmcp>=3.0,<4.0`; test early |
| **Thermal sensors unavailable** | Stress results incomplete | Graceful `None` returns; don't crash |
| **pyhwloc install fails** | Optional enrichment lost | Make fully optional; never required |
| **Gatekeeper UX confusing** | Users bypass safety | Rich prompts with clear options; session allow |

---

## 15. Quick Reference: Tool -> Module Mapping

| Tool | Module | Handler Function |
|------|--------|------------------|
| `detect_arm_soc` | `profiler.py` | `detect_arm_soc()` |
| `detect_os` | `profiler.py` | `detect_os()` |
| `stress_cpu` | `stresser.py` | `stress_cpu()` |
| `stress_memory` | `stresser.py` | `stress_memory()` |
| `measure_thermal` | `stresser.py` | `measure_thermal()` |
| `measure_ram` | `ram_sampler.py` | `sample_ram()` |
| `assess_hardware` | `assess.py` | `assess_hardware()` |
| `generate_cyclonedds_config` | `optimizer.py` | `generate_cyclonedds_xml()` |
| `generate_fastdds_config` | `optimizer.py` | `generate_fastdds_xml()` |
| `generate_zenoh_advice` | `optimizer.py` | `generate_zenoh_advice()` |
| `generate_sysctl_config` | `optimizer.py` | `generate_sysctl_config()` |
| `generate_build_flags` | `optimizer.py` | `generate_build_flags()` |
| `generate_install_script` | `optimizer.py` | `generate_install_script()` |
| `generate_all_configs` | `optimizer.py` | `generate_all_configs()` |
| `generate_report` | `state/report.py` | `generate_report()` |
| `diff_reports` | `state/report_store.py` | `diff_reports()` |
| `list_reports` | `state/report_store.py` | `list_reports()` |
| `get_lessons` | `state/knowledge.py` | `get_lessons()` |

---

## 16. Appendix: Fingerprint Short ID

```python
def short_fingerprint(full: str) -> str:
    """First 12 hex chars for display/directory names."""
    return full[:12]
```

**Usage:** Report dirs, config dirs (via soc_model), diff CLI args, lesson linkage.

---

## 17. Appendix: Tier Score Thresholds

| Tier | Min Score | Min Cores | Min RAM | ISA Required |
|------|-----------|-----------|---------|--------------|
| ros-desktop | 80 | 8 | 8 GB | NEON + SVE + LSE |
| ros-base-full | 60 | 4 | 4 GB | NEON + LSE |
| ros-base | 40 | 2 | 2 GB | NEON |
| micro-ros | 20 | 1 | 256 MB | NEON |
| zenoh-pico | 0 | 1 | 128 MB | Any |

---

**End of Implementation Specification**

This document is the single source of truth for implementation. All code must conform to these specifications. Update this document if design decisions change during implementation.
