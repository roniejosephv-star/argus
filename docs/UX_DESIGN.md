# Argus UI/UX Design Document

**Version**: 1.0  
**Date**: 2026-07-10  
**Status**: Draft

---

## 1. CLI Design Principles

### 1.1 Color Palette

| Element | Color | ANSI Code | Usage |
|---|---|---|---|
| Success | Green | `\033[92m` | ✓ prefixes, completion messages |
| Error | Red | `\033[91m` | ✗ prefixes, failure messages |
| Warning | Yellow | `\033[93m` | ⚠ prefixes, caution notices |
| Info | Blue | `\033[94m` | ℹ prefixes, hints, metadata |
| Header | Cyan + Bold | `\033[96m\033[1m` | Section headers |
| Dim | Dim | `\033[2m` | File paths, secondary info |
| Reset | Default | `\033[0m` | End colored sequences |

### 1.2 Output Structure

Every command output follows a consistent three-part structure:

```
[command header]       → cyan bold: "Argus Hardware Diagnosis"
[data section]         → tables, key-value lists, formatted blocks
[summary footer]       → green: "Diagnosis complete. 6 files written to configs/apple-m3-pro/"
```

### 1.3 Formatting Conventions

- Tables use `rich` `Table` with `show_header=True`, `header_style="bold cyan"`
- Key-value pairs aligned with `rich` `Columns` or `Panel`
- File paths always in dim/gray text
- Timestamps: `2026-07-10 14:30:00` (ISO 8601 local)
- Duration: `5.2s` format
- Sizes: human-readable (KB, MB, GB)

---

## 2. Command Output Templates

### 2.1 `argus diagnose`

```
╭─ Arm SoC Profile ─────────────────────────╮
│ Model:        Apple M3 Pro                 │
│ OS:           macOS 15.2 (arm64)           │
│ Cores:        6P + 6E = 12 total, 12 LGC   │
│ RAM:          36 GB (32 GB available)      │
│ Cache:        128B line, L1 128KB, L2 16MB │
│ ISA:          NEON ✓  SVE ✓  LSE ✓        │
│ Compiler:     apple-m3                     │
│ Fingerprint:  a1b2c3d4e5f6...             │
╰────────────────────────────────────────────╯
```

### 2.2 `argus stress`

```
╭─ CPU Stress Test ──────────────────────────╮
│ Duration:     10.0s                        │
│ Workers:      auto (12)                     │
│ Bogo Ops/s:   4,523                        │
│ Peak Temp:    72.3°C                       │
│ Avg Temp:     68.1°C                       │
│ Clock:        3.78 GHz (avg)              │
╰────────────────────────────────────────────╯

╭─ Memory Bandwidth ─────────────────────────╮
│ Read:        42.3 GB/s                     │
│ Write:       28.1 GB/s                     │
│ Copy:        34.7 GB/s                     │
│ Latency:     89 ns                         │
╰────────────────────────────────────────────╯
```

### 2.3 `argus ram`

```
╭─ RAM Sampler ──────────────────────────────╮
│ Sampling interval:  1.0s                   │
│ Duration:           10                      │
│                                           │
│ Process:           ros2_daemon (PID 4021) │
│   Peak RSS:        128.4 MB               │
│   Avg RSS:         115.2 MB               │
│                                           │
│ System:                                   │
│   Available:       28.4 GB / 36.0 GB     │
│   Active:          4.2 GB                │
│   Wired:           3.4 GB                │
╰────────────────────────────────────────────╯
```

### 2.4 `argus assess`

```
╭─ Argus Assessment ─────────────────────────╮
│ Model:          Apple M3 Pro                │
│ Fingerprint:    a1b2c3d4e5f6              │
│ Score:          92 / 100                    │
│ ROS 2 Tier:     ros-desktop                 │
│ Rationale:      "8+ cores, 8+ GB RAM,      │
│                  full ISA support"           │
╰────────────────────────────────────────────╯

Generated Configurations:
  ✓ cyclonedds.xml      (4.2 KB)  configs/apple-m3-pro/
  ✓ fastdds.xml         (3.8 KB)  configs/apple-m3-pro/
  ✓ zenoh_advice.yaml   (0.8 KB)  configs/apple-m3-pro/
  ✓ sysctl.conf         (1.2 KB)  configs/apple-m3-pro/
  ✓ build_flags.json    (0.5 KB)  configs/apple-m3-pro/
  ✓ install_ros2.sh     (2.1 KB)  configs/apple-m3-pro/
```

### 2.5 `argus report`

```
╭─ Report: 20260710-143000-assess ───────────╮
│ Date:          2026-07-10 14:30:00          │
│ Hardware:      Apple M3 Pro                 │
│ Fingerprint:   a1b2c3d4e5f6               │
│ Score:         92/100                       │
│ Configs:       6 files (12.6 KB total)      │
╰────────────────────────────────────────────╯

╭─ Diff: a1b2c3 (before) → d4e5f6 (after) ───╮
│ Added:                                        │
│   + cyclonedds.xml    (4.2 KB, new)           │
│ Changed:                                      │
│   ~ sysctl.conf       (vm.dirty_ratio: 30→40) │
│ Removed:                                      │
│   - old_config.xml    (deleted)               │
╰──────────────────────────────────────────────╯

Lessons learned: 3
  [1] CPU governor to performance on AC power (92% conf)
  [2] CycloneDDS fragment size = 128KB for M3 (88% conf)
  [3] LTO + mcpu=native for build flags (95% conf)
```

---

## 3. Gatekeeper Prompt Designs

### 3.1 MEDIUM Prompt (`[y/n/v/a/q]`)

```
╭─ 🛡 Permission Required ───────────────────╮
│                                              │
│  Tool:     generate_all_configs              │
│  Radius:   MEDIUM                            │
│  Action:   Write 6 files to configs/         │
│            apple-m3-pro/                      │
│                                              │
│  Files:                                      │
│    • cyclonedds.xml      (4.2 KB)            │
│    • fastdds.xml         (3.8 KB)            │
│    • zenoh_advice.yaml   (0.8 KB)            │
│    • sysctl.conf         (1.2 KB)            │
│    • build_flags.json    (0.5 KB)            │
│    • install_ros2.sh     (2.1 KB)            │
│                                              │
│  [y] Proceed  [n] Cancel  [v] Preview        │
│  [a] Allow for session  [q] Quit             │
╰──────────────────────────────────────────────╯
```

### 3.2 HIGH Prompt (`[y/n/d/q]`)

```
╭─ 🛡 Permission Required ───────────────────╮
│                                              │
│  Tool:     apply_sysctl_config               │
│  Radius:   HIGH                              │
│  Action:   Modify kernel parameters via       │
│            sysctl -w                          │
│                                              │
│  ⚠ This may affect system stability.         │
│  Changes take effect immediately.             │
│                                              │
│  [y] Proceed  [n] Cancel                     │
│  [d] Why is this needed?                     │
│  [q] Quit                                    │
╰──────────────────────────────────────────────╯
```

### 3.3 BLOCKED Prompt (`[d/q]`)

```
╭─ 🛡 Permission Denied ─────────────────────╮
│                                              │
│  Tool:     run_command                       │
│  Radius:   CRITICAL                          │
│  Reason:   Blocked by rule "exec_shell_cmds" │
│            Pattern: rm -rf /                 │
│                                              │
│  [d] Details  [q] Quit                       │
╰──────────────────────────────────────────────╯
```

### 3.4 Preview Mode (`[v]`)

```
╭─ Preview: cyclonedds.xml (4.2 KB) ─────────╮
│                                              │
│ <?xml version="1.0" encoding="UTF-8" ?>     │
│ <CycloneDDS>                                 │
│   <Domain id="0">                             │
│     <Internal>                                │
│       <FragmentSize>131072</FragmentSize>     │
│       <Watermarks>                            │
│         <WhcHigh>250000</WhcHigh>             │
│       </Watermarks>                           │
│     </Internal>                               │
│     ...                                       │
│                                              │
│  [Enter] Back to prompt                      │
╰──────────────────────────────────────────────╯
```

### 3.5 Detail Mode (`[d]`)

```
╭─ Reason Report ─────────────────────────────╮
│                                              │
│  Why is generate_all_configs MEDIUM?          │
│                                              │
│  This tool:                                   │
│  1. Writes multiple files to disk             │
│  2. Suggests kernel parameter changes         │
│  3. Produces install scripts                  │
│                                              │
│  Blast radius: MEDIUM                         │
│  - Creates files but does not execute them    │
│  - No system state modification               │
│  - Changes are reviewable before applying     │
│                                              │
│  [Enter] Back to prompt                      │
╰──────────────────────────────────────────────╯
```

### 3.6 Quit Mode (`[q]`)

```
╭─ Planned Operations (cancelled) ────────────╮
│                                              │
│  The following operations were planned but    │
│  cancelled by user:                           │
│                                              │
│  generate_all_configs:                        │
│    • cyclonedds.xml      (4.2 KB)            │
│    • fastdds.xml         (3.8 KB)            │
│    • zenoh_advice.yaml   (0.8 KB)            │
│    • sysctl.conf         (1.2 KB)            │
│    • build_flags.json    (0.5 KB)            │
│    • install_ros2.sh     (2.1 KB)            │
│                                              │
│  No files were written. Exiting.              │
╰──────────────────────────────────────────────╯
```

---

## 4. Lesson Prompt Design

### 4.1 Lesson Save Prompt

```
╭─ Optimization Summary ─────────────────────╮
│                                              │
│  Benefit:  ~22% lower DDS latency            │
│  Tradeoff: +8% memory usage                   │
│                                              │
│  Key changes:                                 │
│    • FragmentSize: 65536 → 131072            │
│    • IntraSharedMemory: true                 │
│    • Watermarks adjusted for throughput       │
│                                              │
│  Save this as a lesson? [y/N]               │
╰──────────────────────────────────────────────╯
```

### 4.2 Lesson Detail View

```
╭─ Lesson #3 ─────────────────────────────────╮
│ ID:          f1a2b3c4d5e6                    │
│ Date:        2026-07-10 14:31:00             │
│ Hardware:    Apple M3 Pro                    │
│ Category:    DDS Configuration               │
│ Confidence:  92%                             │
│ Tags:        cyclonedds, latency, memory     │
│                                              │
│ Description:                                  │
│ CycloneDDS fragment size should be set to     │
│ 128KB on Apple M3 Pro to match cache line     │
│ alignment for optimal throughput.             │
│                                              │
│ Benefit:  ~22% lower DDS latency              │
│ Tradeoff: +8% memory usage                   │
╰──────────────────────────────────────────────╯
```

---

## 5. MCP Interaction Design

### 5.1 Tool Naming Conventions

- **Format**: `verb_noun` (snake_case)
- **Verbs**: `detect`, `stress`, `measure`, `assess`, `generate`, `diff`, `list`, `get`
- **Nouns**: `arm_soc`, `cpu`, `memory`, `hardware`, `cyclonedds_config`, `report`
- **Examples**: `detect_arm_soc`, `stress_cpu`, `generate_all_configs`

### 5.2 Parameter Naming Conventions

- All parameters in snake_case
- Required parameters listed first
- Optional parameters with sensible defaults
- Duration parameters in seconds (int)
- Path parameters as absolute paths (str)

### 5.3 Response Format Consistency

```json
{
    "success": true,
    "data": { ... },
    "meta": {
        "tool": "diagnose",
        "duration_ms": 234,
        "timestamp": "2026-07-10T14:30:00Z"
    }
}
```

### 5.4 Error Response Format

```json
{
    "success": false,
    "error": {
        "code": "PERMISSION_DENIED",
        "message": "Tool 'apply_sysctl' requires HIGH permission",
        "details": "Use 'argus apply --force' to override with interactive confirmation"
    }
}
```

---

## 6. Error Message Templates

| Scenario | Message | Type |
|---|---|---|
| No profile available | `"No hardware profile found. Run 'argus diagnose' first."` | Info |
| Blocked command | `"Permission denied: pattern matched 'rm -rf' (rule: exec_shell_cmds)"` | Error |
| Gemini key missing | `"Gemini API key not set. Export ARGUS_GEMINI_KEY=<your_key>"` | Warning |
| No reports found | `"No reports found for fingerprint a1b2c3d4. Run 'argus assess --report' first."` | Info |
| Tool timeout | `"Timed out after 30s. Try --duration < N or reduce workers."` | Error |
| Platform unsupported | `"This tool is not available on <platform>. Supported: macOS arm64, Linux aarch64"` | Error |
| Invalid tier | `"Unknown tier 'foxy'. Valid: ros-desktop, ros-base-full, ros-base, micro-ros, zenoh-pico"` | Error |
| No diff available | `"Need exactly 2 report IDs for diff. Usage: argus report --diff <id1> <id2>"` | Warning |
