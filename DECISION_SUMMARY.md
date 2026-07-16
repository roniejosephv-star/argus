# Argus + Pi 4 — Complete Decision Summary

**Generated:** 2026-07-16  
**Target:** Raspberry Pi 4 Model B @ `ssh armcreate@192.168.1.43`  
**Status:** Ready for implementation

---

## 1. Auto-Detected (Run Collector Script)

| Item | Detection Method | Script |
|------|------------------|--------|
| **RAM Variant** (2/4/8 GB) | `/proc/meminfo` | `pi4_profile_collector.sh` |
| **OS & Version** | `/etc/os-release`, `uname` | `pi4_profile_collector.sh` |
| **ROS 2 Distro/Install** | `apt list`, `ros2 --version` | `pi4_profile_collector.sh` |
| **Kernel PREEMPT Type** | `/proc/config.gz`, `/boot/config-*` | `pi4_profile_collector.sh` |
| **CPU/ISA/Cache/Thermal** | `/proc/cpuinfo`, `/sys/`, `vcgencmd` | `pi4_profile_collector.sh` |
| **64-bit Userland** | `file /bin/bash` | `pi4_profile_collector.sh` |

**Run once:**
```bash
ssh armcreate@192.168.1.43 'bash -s' < scripts/pi4_profile_collector.sh
scp armcreate@192.168.1.43:~/pi4_profile.json tests/fixtures/
```

---

## 2. Decisions Requiring Your Input (D1-D7)

| # | Decision | Options | Recommendation | Your Choice |
|---|----------|---------|----------------|-------------|
| **D1** | **Real-Time Kernel** | Standard / PREEMPT_RT | **Standard** (unless motor control/ros2_control) | ☐ |
| **D2** | **ROS 2 Distro** | Humble (22.04) / Jazzy (24.04) / Rolling | **Jazzy** (newer, Pi OS Bookworm base) | ☐ |
| **D3** | **MCP Transport** | stdio over SSH / HTTP + Bearer | **stdio over SSH** (simplest, secure) | ☐ |
| **D4** | **Primary MCP Client** | OpenCode / Claude Code / Both | **OpenCode** (you're using it) | ☐ |
| **D5** | **Config Output Location** | On Pi (`~/configs/`) / Synced to Mac | **On Pi**, then `scp` back | ☐ |
| **D6** | **Pre-Generated Configs in Repo** | Yes / No | **Yes** (Week 4 deliverable) | ☐ |
| **D7** | **Gemini Wrapper in MVP** | Include / Defer | **Defer** to Phase 2 (post-hackathon) | ☐ |

---

## 3. Architecture Decisions (Already Finalized)

| Area | Decision | Rationale |
|------|----------|-----------|
| **Language** | Python 3.11+ | FastMCP requirement, ROS 2 ecosystem |
| **MCP Framework** | FastMCP v3+ | Dual transport (stdio + HTTP), decorator tools |
| **CLI Framework** | Click | Type hints, composable commands |
| **Validation** | Pydantic v2 | Structured I/O, JSON serialization |
| **HW Detection** | psutil + OS-native | No fragile compiled deps; pyhwloc optional |
| **Stress Engine** | Python (numpy + multiprocessing) | Zero-compile install, ~85-95% native perf |
| **Safety** | Permission Gatekeeper | All tool calls pass through blast-radius gate |
| **Config Templates** | F-strings | Simple, no external template engine |
| **State Storage** | `./configs/{soc}/` + `./argus-reports/` | Project-local, reproducible |

---

## 4. Implementation Priority Order

### Phase 0: Foundation (Week 1 - Days 0-3)
| Day | Task | Dependencies |
|-----|------|--------------|
| 0 | **Fixtures + Scaffold** — `pyproject.toml`, package structure, test fixtures from collector | Collector output |
| 1 | **Profiler Linux Backend** — `/proc/cpuinfo`, `/sys/`, `/proc/meminfo`, fingerprint | Fixtures |
| 2 | **Profiler macOS Backend** — `sysctl` (for your Mac Mini) | Fixtures |
| 3 | **Models + Assessment** — Pydantic models, 5-tier logic, Pi 4 tier validation | Profiler |

### Phase 1: Core Engine (Week 1 - Days 4-7)
| Day | Task | Dependencies |
|-----|------|--------------|
| 4 | **Optimizer** — CycloneDDS, FastDDS, Zenoh, sysctl, build flags, install script | Models + Assessment |
| 5 | **Stresser + RAM Sampler** — CPU/memory/thermal stress, RAM sampling | Profiler |
| 6 | **Gatekeeper + Safety** — Blast radius, blocklist, CLI prompts | Tool registry |
| 7 | **Toolbox + CLI** — Tool registry, dispatcher, `argus diagnose/assess/stress/ram` | All core modules |

### Phase 2: MCP + Polish (Week 2)
| Day | Task | Dependencies |
|-----|------|--------------|
| 8 | **MCP Server (stdio)** — FastMCP factory, tool registration, resource URIs | Toolbox + Safety |
| 9 | **MCP HTTP + Auth** — Bearer token, transport config | MCP stdio |
| 10 | **Reporting + E2E** — Report store, lessons, full pipeline test | All above |
| 11 | **Pi 4 Deployment** — Install on Pi, run full pipeline, benchmark | Collector data |

### Phase 3: Harden + Submit (Weeks 3-4)
| Week | Focus |
|------|-------|
| 3 | Testing, README, MCP Inspector demo, cross-platform validation |
| 4 | Pre-generated configs (Pi 4, Pi 5, Jetson, Apple M1/M3/M4), code cleanup, demo video |

---

## 5. Discussion Priority — What to Decide First?

### 🥇 **HIGHEST PRIORITY** — Run Collector + Confirm D1, D2
These affect **everything downstream**:
- **D1 (RT Kernel)** → Changes kernel install, affects RT score (15 pts), may change tier
- **D2 (ROS 2 Distro)** → Determines install script, package names, RMW defaults

### 🥈 **HIGH PRIORITY** — Confirm D3, D4, D5
These affect **MCP integration architecture**:
- **D3 (Transport)** → stdio over SSH is simplest for your Mac Mini → Pi setup
- **D4 (Client)** → OpenCode config differs slightly from Claude Code
- **D5 (Config Location)** → Affects file paths in generated scripts

### 🥉 **MEDIUM PRIORITY** — Confirm D6, D7
These are **Week 4/Phase 2** decisions:
- **D6 (Pre-gen configs)** → Just adds files to repo, no code change
- **D7 (Gemini wrapper)** → Separate script, can add later

---

## 6. Recommended Discussion Order

```
1. RUN COLLECTOR SCRIPT (5 min) → Get actual Pi 4 specs
2. D1: Real-time needed? (motor control vs navigation)
3. D2: ROS 2 distro? (Jazzy recommended)
4. D3: MCP transport? (stdio over SSH recommended)
5. D4: Primary client? (OpenCode)
6. D5: Config location? (On Pi, scp back)
7. D6: Pre-gen configs? (Yes)
8. D7: Gemini wrapper? (Defer)
```

---

## 7. Quick Validation Commands (Run After Collector)

```bash
# Verify collector output
cat tests/fixtures/pi4_profile.json | python3 -m json.tool

# Check key fields
jq '.hardware.memory.total_gb' tests/fixtures/pi4_profile.json
jq '.os.id, .os.version_id' tests/fixtures/pi4_profile.json
jq '.kernel.preempt_type' tests/fixtures/pi4_profile.json
jq '.ros2.installed, .ros2.distro' tests/fixtures/pi4_profile.json
```

---

## 8. Next Action

**Run the collector now**, then we'll have actual data to finalize D1-D2 immediately.

```bash
ssh armcreate@192.168.1.43 'bash -s' < /Users/mindflow/Projects/Hackathon/Arm\ Create/argus/scripts/pi4_profile_collector.sh
scp armcreate@192.168.1.43:~/pi4_profile.json /Users/mindflow/Projects/Hackathon/Arm\ Create/argus/tests/fixtures/pi4_profile.json
```

**Then confirm:** D1 (RT?), D2 (Jazzy OK?), D3-D5 (stdio/SSH/OpenCode/On-Pi OK?)

Once D1-D5 confirmed → **Start Day 0 implementation**.