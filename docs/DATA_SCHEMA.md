# Argus Data Schema Document

**Version**: 1.0  
**Date**: 2026-07-10  
**Status**: Draft

---

## 1. Directory Conventions

### 1.1 Workspace Layout

```
~/.argus/
├── reports/
│   ├── a1b2c3d4e5f6/            ← fingerprint (first 12 hex chars)
│   │   ├── 20260710-143000-assess.json   ← report file
│   │   └── lessons.json                  ← append-only lesson store
│   └── d4e5f6789012/
│       ├── 20260711-093000-assess.json
│       └── lessons.json
│
configs/
├── apple-m3-pro/                 ← normalized soc model name
│   ├── metadata.yaml
│   ├── cyclonedds.xml
│   ├── fastdds.xml
│   ├── zenoh_advice.yaml
│   ├── sysctl.conf
│   ├── build_flags.json
│   └── install_ros2.sh
└── raspberry-pi-5/
    ├── metadata.yaml
    └── ...
```

### 1.2 Config Directory Naming

- Lowercase, hyphens for spaces
- Match `HardwareProfile.model` normalized: `"Apple M3 Pro"` → `apple-m3-pro`
- Always contain `metadata.yaml` with generation info

### 1.3 Report Directory Naming

- Named by fingerprint (SHA-256, first 12 hex characters)
- Multiple report files per fingerprint (one timestamp per run)
- Single `lessons.json` per hardware fingerprint (append-only)

---

## 2. Report Schema

### 2.1 HardwareSnapshot

```json
{
    "type": "object",
    "required": ["model", "arch", "os", "cores", "ram_gb", "cache_line_size", "fingerprint"],
    "properties": {
        "model":           {"type": "string", "example": "Apple M3 Pro"},
        "arch":            {"type": "string", "example": "arm64"},
        "os":              {"type": "string", "example": "macOS 15.2"},
        "cores_physical":  {"type": "integer", "example": 12},
        "cores_performance": {"type": "integer", "example": 6},
        "cores_efficiency":  {"type": "integer", "example": 6},
        "ram_gb":          {"type": "number", "example": 36.0},
        "ram_available_gb": {"type": "number", "example": 32.4},
        "cache_line_size": {"type": "integer", "example": 128},
        "isa_features":    {"type": "array", "items": {"type": "string"}},
        "compiler_target": {"type": "string", "example": "apple-m3"},
        "board_model":     {"type": "string", "example": "Mac15,9"},
        "fingerprint":     {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    }
}
```

### 2.2 OSSnapshot

```json
{
    "type": "object",
    "properties": {
        "platform":      {"type": "string", "enum": ["darwin", "linux"]},
        "release":       {"type": "string", "example": "24.04"},
        "version":       {"type": "string", "example": "Ubuntu 24.04.1 LTS"},
        "kernel":        {"type": "string", "example": "6.8.0-1014-raspi"},
        "python":        {"type": "string", "example": "3.11.5"}
    }
}
```

### 2.3 ROS2Snapshot

```json
{
    "type": "object",
    "properties": {
        "installed":     {"type": "boolean", "example": true},
        "distributions": {"type": "array", "items": {"type": "string"}},
        "rmw_implementations": {"type": "array", "items": {"type": "string"}},
        "workspaces":    {"type": "array", "items": {"type": "string"}}
    }
}
```

### 2.4 ConfigSnapshot

```json
{
    "type": "object",
    "properties": {
        "count":      {"type": "integer", "example": 6},
        "total_bytes":{"type": "integer", "example": 12600},
        "files":      {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":     {"type": "string"},
                    "path":     {"type": "string"},
                    "size_kb":  {"type": "number"},
                    "hash":     {"type": "string"}
                }
            }
        },
        "output_dir": {"type": "string"}
    }
}
```

### 2.5 PerformanceSnapshot

```json
{
    "type": "object",
    "properties": {
        "bogo_ops_s":   {"type": "number", "example": 4523},
        "avg_temp_c":   {"type": "number", "example": 68.1},
        "peak_temp_c":  {"type": "number", "example": 72.3},
        "read_mb_s":    {"type": "number", "example": 42300},
        "write_mb_s":   {"type": "number", "example": 28100},
        "copy_mb_s":    {"type": "number", "example": 34700},
        "latency_ns":   {"type": "number", "example": 89},
        "peak_rss_kb":  {"type": "number", "example": 131480},
        "avg_rss_kb":   {"type": "number", "example": 118016}
    }
}
```

### 2.6 DiskSnapshot

```json
{
    "type": "object",
    "properties": {
        "total_gb":     {"type": "number"},
        "used_gb":      {"type": "number"},
        "free_gb":      {"type": "number"},
        "filesystem":   {"type": "string"}
    }
}
```

### 2.7 Root: Report

```json
{
    "type": "object",
    "required": ["report_id", "timestamp", "reason", "hardware"],
    "properties": {
        "report_id":   {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "timestamp":   {"type": "string", "format": "date-time"},
        "reason":      {"type": "string", "enum": ["assess", "diagnose", "stress", "manual"]},
        "hardware":    {"$ref": "#/definitions/HardwareSnapshot"},
        "os":          {"$ref": "#/definitions/OSSnapshot"},
        "ros2":        {"$ref": "#/definitions/ROS2Snapshot"},
        "performance": {"$ref": "#/definitions/PerformanceSnapshot"},
        "disk":        {"$ref": "#/definitions/DiskSnapshot"},
        "configs":     {"$ref": "#/definitions/ConfigSnapshot"},
        "scorecard":   {"$ref": "#/definitions/Scorecard"},
        "lessons":     {"type": "array", "items": {"$ref": "#/definitions/Lesson"}},
        "pre_report_id": {"type": "string", "description": "ID of prior report this replaces"},
        "diff":          {"$ref": "#/definitions/ReportDiff"}
    }
}
```

---

## 3. Lesson Schema

### 3.1 Lesson Object

```json
{
    "type": "object",
    "required": ["lesson_id", "timestamp", "fingerprint", "description", "benefit", "tradeoff", "confidence"],
    "properties": {
        "lesson_id":    {"type": "string", "pattern": "^[a-f0-9]{12}$"},
        "timestamp":    {"type": "string", "format": "date-time"},
        "fingerprint":  {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "hardware_model": {"type": "string"},
        "description":  {"type": "string"},
        "category":     {"type": "string", "enum": ["dds", "kernel", "build", "system", "general"]},
        "benefit":      {"type": "string"},
        "tradeoff":     {"type": "string"},
        "confidence":   {"type": "integer", "minimum": 0, "maximum": 100},
        "tags":         {"type": "array", "items": {"type": "string"}},
        "diff_summary": {"type": "string"}
    }
}
```

### 3.2 Storage Format (lessons.json)

Append-only array — new lessons appended, never removed (deleted lessons marked as `"deleted": true`).

```json
{
    "version": 1,
    "count": 3,
    "lessons": [
        {
            "lesson_id": "f1a2b3c4d5e6",
            "timestamp": "2026-07-10T14:31:00Z",
            "fingerprint": "a1b2c3d4e5f6789012345678abcdef01abcdef01abcdef01abcdef01abcdef01",
            "hardware_model": "Apple M3 Pro",
            "category": "dds",
            "description": "CycloneDDS fragment size = 128KB for M3 cache line alignment",
            "benefit": "~22% lower DDS latency",
            "tradeoff": "+8% memory usage",
            "confidence": 92,
            "tags": ["cyclonedds", "latency", "cache-line"],
            "diff_summary": "FragmentSize: 65536 → 131072"
        }
    ]
}
```

---

## 4. Config Artifact Schemas

### 4.1 metadata.yaml

```yaml
# Argus-generated configuration metadata
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

### 4.2 cyclonedds.xml

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS>
  <Domain id="0">
    <Internal>
      <FragmentSize>131072</FragmentSize>
      <Watermarks>
        <WhcHigh>250000</WhcHigh>
      </Watermarks>
      <AssumeMulticastCapable>true</AssumeMulticastCapable>
    </Internal>
    <Discovery>
      <MaxAutoParticipantIndex>1</MaxAutoParticipantIndex>
    </Discovery>
  </Domain>
</CycloneDDS>
```

**Key parameters**: FragmentSize (aligned to cache line * 1024), WhcHigh, IntraSharedMemory

### 4.3 fastdds.xml

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>shm_and_udp</transport_id>
      <type>SHM</type>
      <enable_udp>true</enable_udp>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="argus_optimized" is_default_profile="true">
    <rtps>
      <builtin>
        <metatrafficUnicastLocatorList/>
      </builtin>
    </rtps>
  </participant>
</profiles>
```

### 4.4 sysctl.conf

```
# Argus-generated sysctl configuration for Apple M3 Pro
# Generated: 2026-07-10T14:30:00Z
# Tier: ros-desktop

net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.core.somaxconn=1024
vm.dirty_ratio=40
vm.dirty_background_ratio=5
kernel.sched_autogroup_enabled=0
kernel.numa_balancing=0
```

### 4.5 build_flags.json

```json
{
    "mcpu": "native",
    "march": "armv8.5-a",
    "lto": true,
    "lto_mode": "auto",
    "vectorization": true,
    "cmake_args": [
        "-DCMAKE_CXX_FLAGS=-mcpu=native -O3 -flto=auto",
        "-DCMAKE_C_FLAGS=-mcpu=native -O3 -flto=auto"
    ],
    "env": {
        "CFLAGS": "-mcpu=native -O3 -flto=auto",
        "CXXFLAGS": "-mcpu=native -O3 -flto=auto"
    }
}
```

---

## 5. Fingerprint Specification

### 5.1 Algorithm

```
Input: {
    implementer:    str    # e.g., "Apple"
    part:           str    # e.g., "M3 Pro"
    variant:        int    # e.g., 0
    revision:       int    # e.g., 0
    total_ram_kb:   int    # e.g., 37748736
    board_model:    str    # e.g., "Mac15,9"
    cache_line_size: int   # e.g., 128
}

Process:
    1. Sort keys alphabetically
    2. Serialize to JSON (compact, no whitespace)
    3. Compute SHA-256
    4. Return hex digest

Output: a1b2c3d4e5f6789012345678abcdef01abcdef01abcdef01abcdef01abcdef01
Short:  a1b2c3d4e5f6  (first 12 hex characters)
```

### 5.2 Determinism Guarantee

- Same physical machine always produces the same fingerprint
- Changing RAM or OS version does NOT change fingerprint (uses physical properties)
- Only CPU model, cache, and board changes produce different fingerprints

### 5.3 Usage

- Report directory names
- Config directory names (via soc_model, not fingerprint)
- Lesson hardware linkage
- Diff matching (`--diff <short_fingerprint_1> <short_fingerprint_2>`)

---

## 6. File Naming Conventions

### 6.1 Report Files

```
{YYYYMMDD}-{HHMMSS}-{reason}.json

Examples:
  20260710-143000-assess.json
  20260711-093000-diagnose.json
```

- Timestamp in local time (24h format)
- Reason: one of `assess`, `diagnose`, `stress`, `manual`

### 6.2 Lesson Files

- Always `lessons.json` per fingerprint directory
- Append-only: new lessons pushed to array
- Deleted lessons: `{... lesson, "deleted": true, "deleted_at": "..."}`

### 6.3 Config Files

- Fixed names per artifact type (see §4)
- Always overwritten on regeneration (no versioning in filenames)
- Version history captured in metadata.yaml `generated_at` field
