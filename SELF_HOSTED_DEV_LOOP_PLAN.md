# Argus Self-Hosted Development Loop — Architecture & Implementation Plan

**Target:** Raspberry Pi 4 Model B @ `ssh armcreate@192.168.1.43`  
**Controller:** Mac Mini (OpenCode / Claude Code)  
**Goal:** Full self-hosted development loop — OpenCode on Mac drives Argus on Pi via MCP over SSH

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    SELF-HOSTED ARGUS DEVELOPMENT LOOP                                                    │
│                                                                                                           │
│   ┌─────────────────────────────────────────────┐         SSH + MCP stdio         ┌──────────────────┐   │
│   │           OPENCODE / CLAUDE CODE             │  ◄─────────────────────────────► │  RASPBERRY PI 4   │   │
│   │          (Mac Mini Controller)               │                                    │  (Target)       │   │
│   │                                              │         14 MCP Tools                │                 │   │
│   │  • Project Inspection                        │  detect_arm_soc     generate_cyclonedds_config  │   │
│   │  • Build Orchestration                       │  detect_os          generate_fastdds_config       │   │
│   │  • Failure Analysis                          │  stress_cpu         generate_zenoh_advice         │   │
│   │  • Fix Application                           │  stress_memory      generate_sysctl_config        │   │
│   │                                              │  measure_thermal    generate_build_flags            │   │
│   │                                              │  measure_ram        generate_install_script         │   │
│   │                                              │  assess_hardware    generate_all_configs            │   │
│   │                                              │  + 7 Project Inspection Tools                       │   │
│   └─────────────────────────────────────────────┘                                    └──────────────────┘   │
│                                                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Pi-Side Architecture

```
~/argus/ (Argus Project Directory)
├── argus/
│   ├── core/           # profiler, assess, optimizer, stresser, ram_sampler, toolbox, models
│   ├── safety/         # gatekeeper, blast_radius, blocklist
│   ├── mcp/            # server, resources, auth, transports
│   └── state/          # report, report_store, knowledge
├── tests/              # test_core.py, fixtures/
├── configs/            # Pre-generated: raspberry-pi-4/, raspberry-pi-5/, apple-m4/
├── pyproject.toml      # Dependencies + entry points
├── .gitignore
└── README.md

~/argus/argus-reports/{fingerprint}/    # Failure logs, build logs, test logs
├── mcp_errors.jsonl        # Structured MCP tool errors
├── gatekeeper.log          # Permission decisions
├── cli_errors.log          # CLI failures
├── build_*.log             # pip install outputs
├── pytest_*.log            # Test results (JSON)
└── mcp_protocol.log        # JSON-RPC protocol logs
```

---

## 2. Self-Hosted Development Loop Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE SELF-HOSTED LOOP                                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    OPENCODE (Mac)                                              RASPBERRY PI
    ──────────────                                              ───────────
         │                                                          │
         │ 1. SSH + MCP Handshake                                   │
         │ ──────────────────────────────────────────────────────► │
         │                                                          │
         │ 2. Tool Discovery (21 tools: 14 core + 7 project)       │
         │ ◄────────────────────────────────────────────────────── │
         │                                                          │
         │ 3. "Run full assessment on Pi"                          │
         │ ──────────────────────────────────────────────────────► │
         │     Pi: assess_hardware()                               │
         │     Pi: stress_cpu(30s) + stress_memory(30s)            │
         │     Pi: generates scorecard (tier + RMW + DDS profile)  │
         │     Pi: generates 7 configs to ~/argus/configs/pi4/     │
         │                                                          │
         │ 4. Results returned via MCP                             │
         │ ◄────────────────────────────────────────────────────── │
         │     {tier: "micro-ros", score: 33, configs: [...]}      │
         │                                                          │
         │ 5. "Build Argus on Pi"                                  │
         │ ──────────────────────────────────────────────────────► │
         │     Pi: project_pip_install() → pip install -e .        │
         │     Pi: project_pytest() → pytest tests/                │
         │     Pi: captures structured results                     │
         │                                                          │
         │ 6. Build/test results                                   │
         │ ◄────────────────────────────────────────────────────── │
         │     {exit_code: 0, duration: 45s, tests: {passed: 9}}   │
         │                                                          │
         │ 7. IF FAILURE: OpenCode inspects logs                   │
         │    ─────────────────────────────────────────────────►   │
         │    Pi: project_read_file("argus-reports/.../build.log") │
         │    ◄──────────────────────────────────────────────────  │
         │                                                          │
         │ 8. OpenCode fixes bug → writes file                     │
         │    ─────────────────────────────────────────────────►   │
         │    Pi: project_write_file(path, content)                │
         │                                                          │
         │ 9. Repeat from step 5 until tests pass                  │
         │                                                          │
         ▼                                                          ▼
```

---

## 3. Failure Logging Architecture

### 3.1 Capture Points & Log Locations

| Failure Point | Mechanism | Log File |
|--------------|-----------|----------|
| **MCP Tool Execution** | try/except wrapper + structured error response | `argus-reports/{fp}/mcp_errors.jsonl` |
| **Safety Gatekeeper** | PermissionDecision with reason + blast_radius | `argus-reports/{fp}/gatekeeper.log` |
| **CLI Command** | Click error handler + structured output | `argus-reports/{fp}/cli_errors.log` |
| **Build (pip install)** | subprocess capture stdout/stderr | `argus-reports/{fp}/build_*.log` |
| **Tests (pytest)** | pytest --json-report + custom handler | `argus-reports/{fp}/pytest_*.log` |
| **MCP Protocol** | FastMCP error handling + JSON-RPC codes | `argus-reports/{fp}/mcp_protocol.log` |
| **SSH/Transport** | SSH client retry + connection state | `~/.argus/ssh_connection.log` |

### 3.2 Log Format (JSONL — One JSON Per Line)

```json
// argus-reports/{fp}/mcp_errors.jsonl
{"timestamp":"2026-07-16T10:30:00Z","tool":"generate_all_configs","error":"PermissionError: [Errno 13] Permission denied: './configs/pi4'","blast_radius":"MEDIUM","stack_trace":"...","args":{"output_dir":"./configs"}}

// argus-reports/{fp}/build_20260716_103000.log
{"timestamp":"2026-07-16T10:30:05Z","phase":"pip_install","exit_code":1,"stderr":"error: Multiple top-level packages discovered...","command":"pip install -e . --break-system-packages","duration_ms":12500}

// argus-reports/{fp}/pytest_20260716_103015.log
{"timestamp":"2026-07-16T10:30:15Z","phase":"pytest","tests_run":9,"passed":8,"failed":1,"failed_tests":[{"name":"test_pi5_cpu_part_mapping","traceback":"..."}],"duration_ms":3400}
```

### 3.3 Log Rotation

- Max 100MB per fingerprint directory
- Max 10 log files per type
- Auto-cleanup on new fingerprint creation

---

## 4. Project Inspection MCP Tools (7 New Tools)

| Tool | Description | Blast Radius | Parameters |
|------|-------------|--------------|------------|
| `project_list_files` | List files in ~/argus with glob, recursive, size, mtime | NONE | `pattern?: string, recursive?: bool, max_depth?: int` |
| `project_read_file` | Read file with line range, encoding detection | NONE | `path: string, start_line?: int, end_line?: int` |
| `project_write_file` | Atomic write with backup | MEDIUM | `path: string, content: string, create_dirs?: bool` |
| `project_git_status` | Git status (staged, unstaged, untracked) | NONE | `{}` |
| `project_git_diff` | Git diff (staged/unstaged/all) | NONE | `staged?: bool` |
| `project_run_command` | Run arbitrary command in ~/argus with timeout | HIGH | `command: string, timeout?: int, cwd?: string` |
| `project_pip_install` | Run `pip install -e .` in virtualenv | HIGH | `editable?: bool, extras?: string[]` |
| `project_pytest` | Run pytest with JSON report | LOW | `args?: string[], coverage?: bool` |

---

## 5. Phase-by-Phase Implementation Plan

### Phase 1: SSH + MCP Transport Hardening (Days 1-2)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 1.1 | Fix Pi SSH stability | `iwconfig wlan0 power off` + systemd `ssh-hardening.service` |
| 1.2 | MCP stdio over SSH keepalive | SSH `ServerAliveInterval=30`, `ClientAliveInterval=30` |
| 1.3 | MCP reconnection logic | Auto-reconnect on SSH disconnect with exponential backoff |
| 1.4 | MCP heartbeat/ping | Periodic `tools/list` every 60s to detect stale connections |
| 1.5 | Structured error responses | All tools return `{"error": "...", "structured": true, "code": "..."}` |

### Phase 2: Failure Logging Infrastructure (Days 2-4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 2.1 | Centralized log directory | `~/argus/argus-reports/{fingerprint}/` auto-created |
| 2.2 | JSONL log format | Standardized schema across all capture points |
| 2.3 | MCP tool error wrapper | Decorator catching all exceptions → structured response |
| 2.4 | CLI error capture | Click error handler → structured JSON output |
| 2.5 | Build/test log capture | `pytest --json-report` + `pip` stderr capture to JSONL |
| 2.6 | Log rotation + retention | Max 100MB per fingerprint, 10 files max per type |

### Phase 3: Project Inspection MCP Tools (Days 4-7)

| Task | Tool | Blast Radius | Description |
|------|------|--------------|-------------|
| 3.1 | `project_list_files` | NONE | Glob patterns, recursive, size, mtime |
| 3.2 | `project_read_file` | NONE | Line range, encoding detection (utf-8/utf-16/latin1) |
| 3.3 | `project_write_file` | MEDIUM | Atomic write with `.bak`, creates parent dirs |
| 3.4 | `project_git_status` | NONE | GitPython: staged/unstaged/untracked |
| 3.5 | `project_git_diff` | NONE | Staged/unstaged/all with context lines |
| 3.6 | `project_run_command` | HIGH | subprocess with timeout, cwd, env, capture |
| 3.7 | `project_pip_install` | HIGH | venv creation + `pip install -e .[full]` |
| 3.8 | `project_pytest` | LOW | `pytest --json-report` + custom summary |

### Phase 4: Self-Hosted Build Loop (Days 7-10)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | `argus self-build` command | Orchestrates: clean → venv → pip install → pytest |
| 4.2 | Build result capture | Structured JSON: `{exit_code, duration, artifacts, venv_path}` |
| 4.3 | Test result capture | JSON with per-test status, duration, traceback |
| 4.4 | Watch mode (optional) | File change → rebuild → test (via `watchdog` or `inotify`) |
| 4.5 | Failure → OpenCode notification | MCP `notifications/message` on build/test failure |

### Phase 5: OpenCode Integration Polish (Days 10-14)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 5.1 | OpenCode MCP config template | `.opencode/mcp.json` with SSH transport |
| 5.2 | Prompt templates | `debug-build`, `rebuild-argus`, `run-tests`, `fix-failure` |
| 5.3 | Resource subscriptions | Auto-refresh `argus://build/latest`, `argus://test/latest` |
| 5.4 | Failure notification to OpenCode | MCP `notifications/message` on build/test failure |

---

## 6. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **MCP Transport** | stdio over SSH | No open ports, uses existing SSH auth, works through NAT/firewall |
| **SSH Key** | Ed25519 key pair | Modern, fast, no passphrase for automation |
| **Log Format** | JSONL (one JSON per line) | Streaming parseable, grep-friendly, structured |
| **Project Access** | MCP tools (not SFTP) | Unified interface, safety gatekeeper applies |
| **Build Isolation** | Virtualenv in `~/argus/.venv` | Cleaner than `--break-system-packages`, reproducible |
| **Failure Propagation** | MCP error responses + notifications | OpenCode sees failures immediately |
| **State Persistence** | `argus-reports/` on Pi disk | Survives reboots, accessible via MCP |
| **Pi Hostname** | mDNS `raspberrypi.local` | More resilient than static IP |

---

## 7. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pi WiFi drops during build | High | Build fails, logs lost | Ethernet cable; SSH keepalive; log to disk before network call |
| MCP stdio hangs on large output | Medium | OpenCode blocks | Chunked streaming; 30s timeout per tool |
| Pip install breaks system Python | Medium | Pi unbootable | Virtualenv in `~/argus/.venv` |
| SSH key management | Low | Access lost | Authorized keys + backup key; `ssh-copy-id` |
| Disk space fills with logs | Low | Pi unusable | Log rotation (100MB max); `/tmp` for build artifacts |
| Race condition: concurrent MCP | Low | Corrupted state | Single-client stdio; queue requests |

---

## 8. Success Criteria (Definition of Done)

- [ ] OpenCode on Mac connects to `argus mcp serve` on Pi via SSH
- [ ] All 21 MCP tools (14 core + 7 project) discoverable and callable
- [ ] `argus assess` runs on Pi, returns scorecard + generates 7 configs
- [ ] `argus self-build` runs: `venv` → `pip install -e .` → `pytest` → structured results
- [ ] Build failure → logs in `argus-reports/` → OpenCode reads via MCP
- [ ] OpenCode can read/write files in `~/argus` via MCP tools
- [ ] Full loop: OpenCode detects bug → edits file → triggers rebuild → tests pass
- [ ] Pi survives 24h continuous operation (SSH keepalive, log rotation)

---

## 9. Questions for Decision

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| Q1 | Use existing `argus-reports/` for failure logs or new `~/.argus/logs/`? | Existing / New | **Existing** (`argus-reports/`) |
| Q2 | Virtualenv for build isolation or `--break-system-packages`? | venv / system | **venv** (cleaner, safer) |
| Q3 | OpenCode reads logs via MCP resources or SSH cat? | MCP / SSH | **MCP resources** (unified) |
| Q4 | Auto-rebuild on file change (watch mode) or manual trigger? | Auto / Manual | **Manual** first, auto later |
| Q5 | Store Pi SSH key in OpenCode config or macOS keychain? | Config / Keychain | **Keychain** (more secure) |
| Q6 | Pi hostname: IP or mDNS? | IP / mDNS | **mDNS** (`raspberrypi.local`) |

---

## 10. Immediate Next Steps

1. **Flash Pi with Ubuntu 24.04** (see earlier instructions)
2. **Fix Pi WiFi stability** (disable power management, or use Ethernet)
3. **Deploy Argus to Pi** with fixed `pyproject.toml` (see below)
4. **Test SSH + MCP connection** from Mac
5. **Implement Phase 1-2** (SSH hardening + failure logging)
6. **Implement Phase 3** (project inspection tools)
7. **Implement Phase 4** (self-build loop)
8. **Test full OpenCode → Pi → Argus → OpenCode loop**

### Fixed `pyproject.toml` for Pi Deployment

```toml
[project]
name = "argus"
version = "0.1.0"
description = "Arm-native ROS 2 diagnostic & optimization platform"
readme = "README.md"
license = "MIT"
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
    "gitpython>=3.1",    # For project_git_* tools
    "watchdog>=3.0",     # For optional watch mode
]

[project.optional-dependencies]
full = [
    "pyhwloc>=2.0",
    "stress-ng>=0.1",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "pytest-json-report>=1.5",
    "ruff>=0.4",
    "mypy>=1.10",
    "black>=24.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["argus*"]

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

**Ready to proceed with Phase 1 once Pi is flashed and network-stable.**
