# Argus — Phase-Wise Build Plan v3

## Hackathon Deadline: Aug 14, 2026 @ 4:00 PM Pacific
## Start Date: Jul 10, 2026 (~35 days)

---

## Overview

| Week | Focus | Gate Criteria |
|---|---|---|
| **Week 1** (Jul 10-16) | Foundation: profiler + scorecard + configs | `argus diagnose` and `argus assess` produce real output on Mac |
| **Week 2** (Jul 17-23) | Complete core: stress + RAM + report + MCP + CLI | Full MVP operational, all CLI commands work, MCP responds |
| **Week 3** (Jul 24-30) | Polish: testing + README + MCP demo | End-to-end tests pass, README complete, MCP demo working |
| **Week 4** (Jul 31-Aug 6) | Harden: cross-platform + pre-gen configs + edge cases | Linux aarch64 tested (QEMU or real), code cleanup done |
| **Week 5** (Aug 7-14) | Submit: video + Devpost + final review | Video uploaded, Devpost submitted, repo public |

---

## Phase 1: Core MVP (Weeks 1-2)

### Week 1 — Foundation (Jul 10-16)

**Gate**: `argus diagnose` and `argus assess` work on Apple Silicon Mac and produce real, correct output.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 1** (Jul 10) | **M1: Scaffold** | `pyproject.toml`, package structure (`argus/core/`, `argus/mcp/`, `argus/safety/`, `argus/state/`, `tests/`), `__init__.py` files, `__main__.py`, dev environment (`pip install -e .`), `.gitignore`, initial `README.md` skeleton | None |
| **Day 2** (Jul 11) | **M2a: profiler.py (macOS)** | `detect_arm_soc()` with macOS sysctl backends, `get_cache_line_size()`, `get_compiler_target()`, Apple Silicon model detection (M1-M4 mapping) | M1 |
| **Day 3** (Jul 12) | **M2b: profiler.py (Linux)** | Linux backends (`/proc/cpuinfo`, `/sys/devices/system/cpu/`), PREEMPT_RT detection, Cortex/Neoverse CPU part mapping, `compute_fingerprint()` | M2a |
| **Day 4** (Jul 13) | **M5: models.py + assess.py** | All Pydantic models (`HardwareProfile`, `Scorecard`, `StressResults`, `ConfigFile`, `ConfigArtifact`), 5-tier classification logic, score computation with weighted breakdown | M2 |
| **Day 5** (Jul 14) | **M6a: optimizer.py (configs)** | CycloneDDS XML, Fast DDS XML, Zenoh advice markdown, sysctl config — all parameterized by hardware profile | M5 |
| **Day 6** (Jul 15) | **M6b: optimizer.py (build/install)** | `generate_build_flags()`, `generate_install_script()`, `generate_all_configs()` orchestrator, `configs/{soc}/` output structure with `metadata.yaml` | M6a |
| **Day 7** (Jul 16) | **M8a: CLI (partial)** | `argus diagnose`, `argus assess` working with Click, pretty-printed JSON/table output, `argus --version` | M2, M5, M6 |

### Week 2 — Complete Core (Jul 17-23)

**Gate**: Full Phase 1 MVP operational. All CLI commands work. MCP server starts and responds to tool calls via both transports.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 8** (Jul 17) | **M4a: stresser.py** | `stress_cpu()` with multiprocessing + numpy, `stress_memory()` with STREAM-like numpy ops, temperature sampling integration | M2 |
| **Day 9** (Jul 18) | **M4b: stresser.py + ram_sampler.py** | `stress_thermal()` with combined load, `sample_ram()` with psutil, thermal backends (macOS IOKit/powermetrics, Linux /sys/class/thermal) | M4a |
| **Day 10** (Jul 19) | **M7a: toolbox.py + gatekeeper + safety** | `ToolSpec` class, `TOOL_REGISTRY`, all tools registered, `execute_tool()` dispatcher with Permission Gatekeeper (`gatekeeper.py`, `blast_radius.py`, `blocklist.py`). FastMCP server factory, tool registration loop | M2-M6 |
| **Day 11** (Jul 20) | **M7b: MCP transports + resources + reporting** | Stdio + HTTP transports with Bearer auth, `TransportConfig`, resource URIs, prompt templates. **Reporting module**: `state/report.py` models, `state/report_store.py` persistence, `state/knowledge.py` lesson extraction | M7a |
| **Day 12** (Jul 21) | **M8b: CLI (complete) + report** | `argus stress`, `argus ram`, `argus report`, `argus mcp serve` all wired up. Full CLI with help text. Pipeline: diagnose → stress → assess → report | M4, M7 |

---

## Phase 1.5: Hardening (Week 3-4)

### Week 3 — Polish (Jul 24-30)

**Gate**: End-to-end tests pass on macOS. README is submission-ready. MCP demo via MCP Inspector working. Gemini wrapper script tested.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 15-16** | **Testing** | Unit tests for all modules. E2E test: `diagnose → stress → assess → report → generate_configs`. MCP client test (stdio + HTTP). Mock fixtures for Pi 5 and Jetson Orin | M8b |
| **Day 17-18** | **README + Documentation** | Complete README.md: overview, architecture diagram, install, usage, MCP setup (MCP Inspector + Gemini CLI), config examples. `ARCHITECTURE.md` with system design | Tests passing |
| **Day 19** | **MCP Inspector + Gemini Wrapper** | **MCP Inspector**: verify `argus mcp serve --transport http` → browser at localhost:5173 discovers tools, calls work. **Gemini wrapper**: write `scripts/argus_mcp_gemini.py` — imports `argus.core.toolbox` directly (no MCP subprocess), converts tools to Gemini function declarations via `google-genai` SDK, runs single-prompt → tool loop → natural language response | M7b, README |
| **Day 20** | **MCP Demo Rehearsal** | Record dry run of both MCP paths. Fix any protocol/format issues. Verify Gemini wrapper handles tool responses correctly | Day 19 |
| **Day 21** | **Demo Video Draft** | Script the 3-min video. Record first draft: problem → CLI demo → config output → MCP demo (Inspector + Gemini) → report diff | MCP demo working |

### Week 4 — Harden (Jul 31-Aug 6)

**Gate**: Linux aarch64 validated. Code cleanup complete. Pre-generated configs for major boards shipped.

| Day | Milestone | Deliverables | Dependencies |
|---|---|---|---|
| **Day 22-23** | **Cross-Platform Validation** | Test on Linux aarch64 (QEMU Ubuntu or real Pi/Jetson). Fix platform-specific bugs. Verify profiler on real Arm CPU | MVP complete |
| **Day 24-25** | **Pre-Generated Configs** | Ship configs for: Apple M1, M3 Pro, M4, Raspberry Pi 5, Pi 4, Jetson Orin Nano, Generic Cortex-A76. Each with `metadata.yaml` | Cross-platform |
| **Day 26-27** | **Code Cleanup** | Type hints on all public APIs. Docstrings. Format with `ruff`. Consistent error handling | All features |
| **Day 28** | **Final README + ARCHITECTURE** | Final README pass from clean install. Add sample output screenshots. Link to demo video | Code cleanup |

---

## Phase 2: Agentic (Post-Hackathon)

### M13 — ToolLoopAgent + Gemini
- `agent/loop.py` — REASON → PARSE → EXECUTE → FEEDBACK loop
- `agent/reasoner.py` — Gemini via `google-genai` SDK; heuristic fallback
- `agent/governor.py` — Max steps (20), timeout (600s), cost limit ($0.50)

### M14 — Pipeline Orchestrator
- `agent/pipeline.py` — DISCOVER → PROFILE → TUNE → BUILD → VERIFY phases
- `PipelineContext` carries state between phases

### M15 — MCP Client
- `agent/mcp_client.py` — Connect to external MCP servers (stdio + HTTP)
- Merge external tools into agent's tool set

### M16 — HeuristicDiagnosticEngine
- Rule-based ROS 2 issue diagnosis (RMW mismatch, DDS port conflicts, QoS)

### M17 — Sub-Agent Spawning
- Task decomposition → parallel sub-agents → result merge

---

## Phase 3: Production & Demo (Post-Hackathon)

### M18 — Performance Benchmark Integration
- `performance_test` / `ros2_benchmark` wrappers for latency/jitter/throughput

### M19 — OAuth 2.1 + PKCE
- Full authorization code flow, JWKS, per-tool scopes

### M20 — Pre-Generated Config Library
- Ship configs for 20+ Arm boards (Pi 3/4/5, Jetson, RK3588, i.MX8, etc.)

### M21 — Demo Video + Devpost
- Record final demo, submit to Devpost, judges' walkthrough

---

## Critical Path

```
M1 (scaffold)
  → M2 (profiler) ← CRITICAL: everything depends on this
    → M5 (models + assess)
      → M6 (optimizer)
        → M7 (MCP + gatekeeper + report) ← needs all tools + models
          → M8 (CLI) ← wires everything together
    → M4 (stress + RAM)
```

> **`profiler.py` is the single point of failure.** Allocate extra time here and test on real hardware early.

---

## File Tree (Final)

```
argus/
├── pyproject.toml
├── LICENSE
├── README.md
├── scripts/
│   └── argus_mcp_gemini.py       # Gemini CLI MCP integration wrapper
├── argus/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── profiler.py
│   │   ├── stresser.py
│   │   ├── ram_sampler.py
│   │   ├── assess.py
│   │   ├── optimizer.py
│   │   ├── models.py
│   │   └── toolbox.py
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── gatekeeper.py
│   │   ├── blast_radius.py
│   │   └── blocklist.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── transports.py
│   │   ├── auth.py
│   │   └── resources.py
│   ├── state/
│   │   ├── __init__.py
│   │   ├── report.py
│   │   ├── report_store.py
│   │   └── knowledge.py
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
