# Argus API Reference

**Version**: 1.0  
**Date**: 2026-07-10  
**Status**: Draft

---

## 1. CLI Reference

### 1.1 `argus diagnose`

Display hardware profile of the Arm system.

```
Usage: argus diagnose [OPTIONS]

Options:
  --detailed     Show extended hardware info (cache topology, ISA features)
  --help         Show this message and exit

Exit codes:
  0  Success
  4  Unsupported platform

Examples:
  argus diagnose
  argus diagnose --detailed
```

### 1.2 `argus stress`

Run CPU and memory stress tests.

```
Usage: argus stress [OPTIONS]

Options:
  --duration INTEGER   Test duration in seconds  [default: 10]
  --workers INTEGER    Number of stress workers  [default: auto]
  --help               Show this message and exit

Exit codes:
  0  Success
  2  Tool execution failed (e.g., no thermal sensor)

Examples:
  argus stress
  argus stress --duration 30 --workers 4
```

### 1.3 `argus ram`

Sample RAM usage of a process or system.

```
Usage: argus ram [OPTIONS]

Options:
  --pid INTEGER        Process ID to sample  [default: None = all]
  --interval FLOAT     Sampling interval in seconds  [default: 1.0]
  --duration INTEGER   Number of samples  [default: 10]
  --help               Show this message and exit

Exit codes:
  0  Success
  2  Invalid PID or sampling failure

Examples:
  argus ram
  argus ram --pid 4021 --interval 0.5 --duration 20
```

### 1.4 `argus assess`

Full hardware assessment with ROS 2 tier scoring.

```
Usage: argus assess [OPTIONS]

Options:
  --output-dir PATH   Custom output directory for configs  [default: auto]
  --report            Generate detailed report
  --no-configs        Skip config generation (assessment only)
  --help              Show this message and exit

Exit codes:
  0  Success
  3  Permission denied (gatekeeper)
  4  No Arm SoC detected

Examples:
  argus assess
  argus assess --report
  argus assess --no-configs
```

### 1.5 `argus report`

View, diff, and manage reports and lessons.

```
Usage: argus report [OPTIONS]

Options:
  --diff <id1> <id2>       Compare two reports by fingerprint ID
  --list                   List all reports
  --lessons                List all saved lessons
  --lesson <id>            Show details of a specific lesson
  --delete-lesson <id>     Delete a saved lesson
  --export-lessons <file>  Export lessons to JSON file
  --import-lessons <file>  Import lessons from JSON file
  --help                   Show this message and exit

Exit codes:
  0  Success
  2  Report/lesson not found

Examples:
  argus report
  argus report --diff a1b2c3 d4e5f6
  argus report --lessons
  argus report --lesson 3
```

### 1.6 `argus mcp serve`

Start the MCP server.

```
Usage: argus mcp serve [OPTIONS]

Options:
  --transport [stdio|http]  Transport protocol  [default: stdio]
  --port INTEGER            HTTP port  [default: 8080]
  --host TEXT               HTTP bind host  [default: localhost]
  --help                    Show this message and exit

Exit codes:
  0  Server stopped gracefully
  1  Failed to start

Examples:
  argus mcp serve
  argus mcp serve --transport http --port 8080
```

### 1.7 Gemini Wrapper

```
Usage: python scripts/argus_mcp_gemini.py "<prompt>"

Environment:
  ARGUS_GEMINI_KEY    Required. Gemini API key.

Exit codes:
  0  Success
  1  ARGUS_GEMINI_KEY not set
  2  Gemini API error

Examples:
  python scripts/argus_mcp_gemini.py "Optimize my M3 for ROS 2"
  python scripts/argus_mcp_gemini.py "Compare my Pi 4 and Pi 5 for ROS 2"
```

### 1.8 `argus --version`

```
Usage: argus --version
Exit code: 0
Output: Argus v0.1.0
```

### 1.9 CLI Exit Codes Summary

| Code | Meaning | When |
|---|---|---|
| 0 | Success | Command completed as intended |
| 1 | General error | Invalid args, missing deps, startup failure |
| 2 | Execution error | Tool failed, timeout, data not found |
| 3 | Permission denied | Gatekeeper blocked the operation |
| 4 | Platform unsupported | Feature not available on this OS/arch |

---

## 2. MCP Tool Signatures

### 2.1 `detect_arm_soc`

```json
{
    "name": "detect_arm_soc",
    "description": "Detect the Arm SoC model and capabilities of the current system",
    "parameters": {
        "properties": {
            "detailed": {
                "description": "Include extended cache topology and ISA features",
                "type": "boolean",
                "default": false
            }
        },
        "required": []
    }
}
```

**Returns**:
```json
{
    "model": "Apple M3 Pro",
    "arch": "arm64",
    "os": "macOS 15.2",
    "cores_physical": 12,
    "cores_performance": 6,
    "cores_efficiency": 6,
    "ram_gb": 36.0,
    "ram_available_gb": 32.4,
    "cache_line_size": 128,
    "isa_features": ["NEON", "SVE", "LSE", "FP16"],
    "compiler_target": "apple-m3",
    "board_model": "Mac15,9",
    "fingerprint": "a1b2c3d4e5f6789012345678abcdef01",
    "fingerprint_short": "a1b2c3d4e5f6"
}
```

**Errors**: None (read-only operation)

**Example request/response**:
```
Request:  {"method": "tools/call", "params": {"name": "detect_arm_soc", "arguments": {}}}
Response: {"result": {"content": [{"type": "text", "text": "{\"model\": \"Apple M3 Pro\", ...}"}]}}
```

### 2.2 `stress_cpu`

```json
{
    "name": "stress_cpu",
    "description": "Run CPU stress test using prime number computation",
    "parameters": {
        "properties": {
            "duration_s": {
                "description": "Test duration in seconds",
                "type": "integer",
                "default": 10
            },
            "workers": {
                "description": "Number of worker threads (auto = CPU count)",
                "type": "integer",
                "default": null
            }
        },
        "required": []
    }
}
```

**Returns**:
```json
{
    "bogo_ops_s": 4523,
    "avg_temp_c": 68.1,
    "peak_temp_c": 72.3,
    "workers": 12,
    "duration_s": 10.0
}
```

**Errors**: `{"error": "no_thermal_sensor", "message": "No thermal sensor found on this system"}`

### 2.3 `stress_memory`

```json
{
    "name": "stress_memory",
    "description": "Run memory bandwidth stress test (read/write/copy/latency)",
    "parameters": {
        "properties": {
            "duration_s": {
                "description": "Test duration in seconds",
                "type": "integer",
                "default": 10
            },
            "block_size_mb": {
                "description": "Memory block size in MB",
                "type": "integer",
                "default": 256
            }
        },
        "required": []
    }
}
```

**Returns**:
```json
{
    "read_mb_s": 42300,
    "write_mb_s": 28100,
    "copy_mb_s": 34700,
    "latency_ns": 89,
    "duration_s": 10.0
}
```

### 2.4 `measure_thermal`

```json
{
    "name": "measure_thermal",
    "description": "Measure current thermal state of the system",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "temp_c": 65.2,
    "sensor_count": 3,
    "sensors": [
        {"name": "CPU-0", "temp_c": 65.2},
        {"name": "GPU-0", "temp_c": 62.1},
        {"name": "PMU", "temp_c": 58.0}
    ]
}
```

**Errors**: `{"error": "no_thermal_sensor", "message": "No thermal sensors available"}`

### 2.5 `measure_ram`

```json
{
    "name": "measure_ram",
    "description": "Sample RAM usage of a specific process or all processes",
    "parameters": {
        "properties": {
            "pid": {
                "description": "Process ID to sample (None = system-wide)",
                "type": "integer",
                "default": null
            },
            "interval_s": {
                "description": "Sampling interval in seconds",
                "type": "number",
                "default": 1.0
            },
            "samples": {
                "description": "Number of samples to collect",
                "type": "integer",
                "default": 10
            }
        },
        "required": []
    }
}
```

**Returns**:
```json
{
    "pid": 4021,
    "process_name": "ros2_daemon",
    "peak_rss_kb": 131480,
    "avg_rss_kb": 118016,
    "samples": [
        {"rss_kb": 118000, "timestamp": "2026-07-10T14:30:00Z"},
        {"rss_kb": 118500, "timestamp": "2026-07-10T14:30:01Z"}
    ],
    "system_available_kb": 29784000,
    "system_total_kb": 37748736
}
```

### 2.6 `assess_hardware`

```json
{
    "name": "assess_hardware",
    "description": "Assess hardware for ROS 2 suitability, return score and tier",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "score": 92,
    "max_score": 100,
    "tier": "ros-desktop",
    "tier_label": "Full ROS 2 Desktop",
    "rationale": "8+ cores, 8+ GB RAM, full ISA support (NEON, SVE, LSE)",
    "subscores": {
        "compute": 95,
        "memory": 88,
        "thermal": 90,
        "isa": 95
    },
    "fingerprint": "a1b2c3d4e5f6"
}
```

**Tier table**:

| Tier | Min Score | Min Cores | Min RAM | ISA Required |
|---|---|---|---|---|
| ros-desktop | 80 | 8 | 8 GB | NEON + SVE + LSE |
| ros-base-full | 60 | 4 | 4 GB | NEON + LSE |
| ros-base | 40 | 2 | 2 GB | NEON |
| micro-ros | 20 | 1 | 256 MB | NEON |
| zenoh-pico | 0 | 1 | 128 MB | Any |

### 2.7 `generate_cyclonedds_config`

```json
{
    "name": "generate_cyclonedds_config",
    "description": "Generate optimized CycloneDDS XML configuration",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "xml": "<?xml version=\"1.0\"?>\n<CycloneDDS>\n  <Domain id=\"0\">\n    ...\n  </Domain>\n</CycloneDDS>",
    "file_path": "configs/apple-m3-pro/cyclonedds.xml",
    "summary": "FragmentSize=128KB, IntraSharedMemory=true, Watermarks optimized for throughput"
}
```

### 2.8 `generate_fastdds_config`

```json
{
    "name": "generate_fastdds_config",
    "description": "Generate optimized Fast DDS XML configuration",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "xml": "<?xml version=\"1.0\"?>\n<profiles xmlns=\"http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles\">\n  ...\n</profiles>",
    "file_path": "configs/apple-m3-pro/fastdds.xml",
    "summary": "DomainId=0, BuiltinTransports=SHM+UDPv4, HistoryQos policy set for low latency"
}
```

### 2.9 `generate_zenoh_advice`

```json
{
    "name": "generate_zenoh_advice",
    "description": "Generate advice on whether and how to use Zenoh instead of DDS",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "recommendation": "keep_dds",
    "advice": "This system has sufficient resources for full DDS. Zenoh recommended for < 1GB RAM or micro-ROS deployments.",
    "yaml": "..."  // Zenoh configuration if recommended
}
```

### 2.10 `generate_sysctl_config`

```json
{
    "name": "generate_sysctl_config",
    "description": "Generate optimized sysctl kernel parameters for ROS 2",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "config": "net.core.rmem_max=16777216\nnet.core.wmem_max=16777216\nvm.dirty_ratio=40\nvm.dirty_background_ratio=5\nkernel.sched_autogroup_enabled=0\nnet.core.somaxconn=1024",
    "file_path": "configs/apple-m3-pro/sysctl.conf",
    "summary": "8 parameters tuned for real-time ROS 2 networking and scheduling"
}
```

### 2.11 `generate_build_flags`

```json
{
    "name": "generate_build_flags",
    "description": "Generate optimized compiler build flags for ROS 2",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "flags": {
        "cmake_args": ["-DCMAKE_CXX_FLAGS=-mcpu=native -O3 -flto=auto"],
        "mcpu": "native",
        "march": "armv8.5-a",
        "lto": true,
        "vectorization": true
    },
    "file_path": "configs/apple-m3-pro/build_flags.json",
    "summary": "-mcpu=native -O3 -flto=auto detected from compiler target apple-m3"
}
```

### 2.12 `generate_install_script`

```json
{
    "name": "generate_install_script",
    "description": "Generate OS-specific ROS 2 install script based on tier",
    "parameters": {
        "properties": {
            "os": {
                "description": "Target OS (auto-detect by default)",
                "type": "string",
                "enum": ["ubuntu", "debian", "macos"],
                "default": null
            },
            "tier": {
                "description": "ROS 2 tier override (use assessed tier by default)",
                "type": "string",
                "default": null
            }
        },
        "required": []
    }
}
```

**Returns**:
```json
{
    "script": "#!/bin/bash\n# Argus-generated ROS 2 install script\n# Tier: ros-desktop\n# Target: ubuntu 24.04 (arm64)\n\nsudo apt update\nsudo apt install -y ros-jazzy-desktop\n...",
    "file_path": "configs/apple-m3-pro/install_ros2.sh",
    "summary": "Installs ros-jazzy-desktop (arm64) with optimized configs"
}
```

### 2.13 `generate_all_configs`

```json
{
    "name": "generate_all_configs",
    "description": "Generate all optimized configuration artifacts",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "artifacts": ["cyclonedds.xml", "fastdds.xml", "zenoh_advice.yaml", "sysctl.conf", "build_flags.json", "install_ros2.sh"],
    "output_dir": "configs/apple-m3-pro/",
    "count": 6,
    "total_bytes": 12600
}
```

### 2.14 `generate_report`

```json
{
    "name": "generate_report",
    "description": "Generate a full diagnostic and optimization report",
    "parameters": {
        "properties": {},
        "required": []
    }
}
```

**Returns**: `Report` JSON object (see DATA_SCHEMA.md §2)

### 2.15 `diff_reports`

```json
{
    "name": "diff_reports",
    "description": "Compare two reports and return the differences",
    "parameters": {
        "properties": {
            "report_id_1": {
                "description": "First report fingerprint ID",
                "type": "string"
            },
            "report_id_2": {
                "description": "Second report fingerprint ID",
                "type": "string"
            }
        },
        "required": ["report_id_1", "report_id_2"]
    }
}
```

**Returns**:
```json
{
    "id_1": "a1b2c3d4e5f6",
    "id_2": "d4e5f6789012",
    "added": [{"name": "cyclonedds.xml", "size_kb": 4.2}],
    "removed": [],
    "changed": [
        {"name": "sysctl.conf", "param": "vm.dirty_ratio", "old": 30, "new": 40}
    ],
    "score_diff": "+5",
    "summary": "2 configs added, 1 param changed. Score improved by 5 points."
}
```

### 2.16 `list_reports`

```json
{
    "name": "list_reports",
    "description": "List all saved reports",
    "parameters": {"properties": {}, "required": []}
}
```

**Returns**: `[{"fingerprint": "a1b2c3d4e5f6", "date": "2026-07-10", "score": 92, "tier": "ros-desktop"}, ...]`

### 2.17 `get_lessons`

```json
{
    "name": "get_lessons",
    "description": "Get all saved lessons",
    "parameters": {"properties": {}, "required": []}
}
```

**Returns**: `[{"id": "f1a2b3c4d5e6", "description": "...", "benefit": "...", "confidence": 92, "tags": ["cyclonedds"]}, ...]`

### 2.18 Blast Radius Classification

| Tool | Blast Radius | Mode |
|---|---|---|
| detect_arm_soc | NONE | Auto-approve |
| stress_cpu | LOW | Auto-approve |
| stress_memory | LOW | Auto-approve |
| measure_thermal | NONE | Auto-approve |
| measure_ram | NONE | Auto-approve |
| assess_hardware | NONE | Auto-approve |
| generate_*_config | LOW | Auto-approve |
| generate_all_configs | MEDIUM | Ask user |
| generate_report | LOW | Auto-approve |
| diff_reports | NONE | Auto-approve |
| list_reports | NONE | Auto-approve |
| get_lessons | NONE | Auto-approve |

---

## 3. MCP Resources

| URI | Description | Returns |
|---|---|---|
| `argus://system/info` | Basic system info | `{model, os, arch, fingerprint}` |
| `argus://system/cpu` | CPU details | `{cores, cache_line, isa}` |
| `argus://system/memory` | Memory stats | `{total_kb, available_kb}` |
| `argus://sensors/temperature` | Current thermal | `{temp_c, sensors}` |
| `argus://stress/latest` | Last stress result | `{bogo_ops_s, avg_temp_c}` |
| `argus://configs/cyclonedds` | Generated CycloneDDS XML | XML string |
| `argus://configs/fastdds` | Generated Fast DDS XML | XML string |
| `argus://configs/sysctl` | Generated sysctl config | Config string |
| `argus://scorecard/latest` | Latest assessment | `{score, tier, subscores}` |
| `argus://reports/latest` | Latest report | Full Report JSON |

---

## 4. MCP Prompts

| Prompt | Description |
|---|---|
| `tune-ros2` | "Tune this Arm system for ROS 2 performance" |
| `profile-arm` | "Profile this Arm system's hardware capabilities" |
| `optimize-dds` | "Optimize DDS configuration for this Arm platform" |
| `debug-thermal` | "Check thermal state and suggest mitigation" |

---

## 5. JSON-RPC Error Codes

| Code | Name | When |
|---|---|---|
| -32700 | Parse error | Invalid JSON in request |
| -32600 | Invalid request | JSON is not a valid request object |
| -32601 | Method not found | Unknown tool name |
| -32602 | Invalid params | Required param missing or type mismatch |
| -32603 | Internal error | Unexpected tool execution failure |
| -32000 | Permission denied | Gatekeeper blocked the tool |
| -32001 | Tool timeout | Tool exceeded execution time limit |
| -32002 | Blocked by gatekeeper | Pattern matched blocklist rules |
