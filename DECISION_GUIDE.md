# Argus + Pi 4 — Decision Guide & Architecture

**Target:** Raspberry Pi 4 Model B @ `ssh armcreate@192.168.1.43`  
**Goal:** Finalize all architectural decisions before implementation

---

## 1. Auto-Detection (No Manual Answers Needed)

Run this on the Pi — it detects **everything**:

```bash
# Option A: Direct SSH execution
ssh armcreate@192.168.1.43 'bash -s' < scripts/pi4_profile_collector.sh

# Option B: Copy first, then run
scp scripts/pi4_profile_collector.sh armcreate@192.168.1.43:~/
ssh armcreate@192.168.1.43 'bash ~/pi4_profile_collector.sh'

# Result: ~/pi4_profile.json with all answers
scp armcreate@192.168.1.43:~/pi4_profile.json ./tests/fixtures/
```

**What it detects automatically:**
| Category | Detected Fields |
|----------|-----------------|
| **Hardware** | CPU part (0xd08=Cortex-A72), cores, RAM (2/4/8 GB), cache line (64), thermal zones, vcgencmd |
| **OS** | Distro (Pi OS/Ubuntu), version, kernel, 64-bit userland? |
| **Kernel** | PREEMPT type (none/voluntary/rt/full) |
| **ROS 2** | Installed? Distro (humble/iron/jazzy/rolling)? RMW? Packages? |
| **Network** | Hostname, IPs, SSH port |
| **Tools** | stress-ng available? Python packages? |

---

## 2. Real-Time (PREEMPT_RT) — Do You Need It?

### What It Is
| Config | Latency | Use Case |
|--------|---------|----------|
| **Standard (PREEMPT_NONE)** | ~50-200 μs | General robotics, navigation, perception |
| **PREEMPT_VOLUNTARY** | ~20-50 μs | Better responsiveness |
| **PREEMPT_RT (Full)** | **~5-15 μs** | **Hard real-time: motor control, safety loops, ROS 2 Control** |

### Pi 4 Specifics
- **Standard kernel:** No RT, fine for most ROS 2
- **RT kernel:** Requires custom build or Ubuntu RT PPA (`linux-image-rt-raspi`)
- **Trade-off:** RT kernel = slightly lower throughput, higher CPU overhead

### Decision Matrix
| Your Project | Recommendation |
|--------------|----------------|
| Mobile robot (Nav2, SLAM, perception) | **Standard kernel** — RT not needed |
| Arm manipulation (MoveIt, ros2_control) | **PREEMPT_RT** — needed for control loops |
| Safety-critical (ISO 13849, emergency stop) | **PREEMPT_RT + isolated CPUs** |
| Learning/experimentation | **Standard** — simpler |

**Argus handles both:** `has_preempt_rt` field → affects RT score (15 pts) → tier recommendation

---

## 3. MCP Remote Access Architecture

### Your Setup
```
┌─────────────────────────────────────────────────────────────────┐
│  Mac Mini (OpenCode / Claude Code)                              │
│  ─────────────────────────────────────────────────────────────  │
│  MCP Client (stdio over SSH)                                    │
│                                                                 │
│  ssh armcreate@192.168.1.43 "argus mcp serve --transport stdio" │
└──────────────────────────────┬──────────────────────────────────┘
                               │ SSH Tunnel (stdio forwarded)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Raspberry Pi 4 (Argus MCP Server)                              │
│  ─────────────────────────────────────────────────────────────  │
│  FastMCP Server (stdio transport)                               │
│  ─────────────────────────────────────────────────────────────  │
│  Tools: detect_arm_soc, stress_cpu, assess_hardware,            │
│         generate_cyclonedds_config, generate_all_configs, etc.  │
│  ─────────────────────────────────────────────────────────────  │
│  Hardware: BCM2711, 4×A72, 4/8GB RAM, /sys/class/thermal       │
└─────────────────────────────────────────────────────────────────┘
```

### Why stdio over SSH?
| Transport | Pros | Cons |
|-----------|------|------|
| **stdio over SSH** | No open ports, uses existing SSH auth, works through firewalls | Single client at a time |
| **HTTP + Bearer token** | Multiple clients, web access, MCP Inspector | Need port forwarding, token management |

**Recommendation:** Start with **stdio over SSH** — simplest, secure, works with Claude Code/OpenCode natively.

### Claude Code Config (`~/.claude/claude_code_config.json`)
```json
{
  "mcpServers": {
    "argus-pi4": {
      "command": "ssh",
      "args": [
        "armcreate@192.168.1.43",
        "argus",
        "mcp",
        "serve",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### OpenCode Config (similar)
```json
{
  "mcp": {
    "servers": {
      "argus-pi4": {
        "command": "ssh",
        "args": ["armcreate@192.168.1.43", "argus", "mcp", "serve", "--transport", "stdio"]
      }
    }
  }
}
```

### How It Works
1. You type in OpenCode/Claude: *"Profile my Pi 4 and generate CycloneDDS config"*
2. LLM calls `detect_arm_soc` → runs **on Pi** via SSH → returns hardware JSON
3. LLM calls `assess_hardware` → runs **on Pi** → returns tier/scorecard
4. LLM calls `generate_cyclonedds_config` → runs **on Pi** → returns XML tuned for Pi 4
5. LLM calls `generate_all_configs` → writes files to `configs/raspberry-pi-4/` **on Pi**
6. You get natural language summary + file paths

---

## 4. MCP Clients Explained

| Client | What It Is | How It Connects to Argus |
|--------|------------|--------------------------|
| **Claude Code** | Anthropic's CLI coding agent | Native MCP via stdio/HTTP config |
| **OpenCode (opencode.ai)** | Open-source AI coding agent | Native MCP, similar config to Claude Code |
| **Gemini CLI** | Google's CLI with Gemini | Can use MCP via stdio or HTTP |
| **MCP Inspector** | Web UI at `http://localhost:5173` | Connects to HTTP transport (`argus mcp serve --transport http --port 8765`) |
| **Antigravity 2.0** | Arm's web-based AI IDE | HTTP + Bearer token auth |

### For Your Setup (Mac Mini → Pi 4)
| Use This | For |
|----------|-----|
| **Claude Code / OpenCode** | Daily coding — "optimize my Pi 4 for ROS 2" |
| **MCP Inspector** | Debugging — visually browse tools, resources, prompts |
| **Gemini CLI** | Alternative LLM — same tools, different brain |

---

## 5. Benchmarks — What to Run

### Argus Built-in Stress (Python, no deps)
```bash
argus stress --duration 30        # CPU + memory + thermal
argus ram --duration 20           # Memory sampling
```

### ROS 2 Specific (requires `ros2_benchmark` or `ros2_benchmark`)
```bash
# Latency (talker/listener)
ros2 run ros2_benchmark benchmark_latency --topic /chatter --duration 60s

# Throughput (large messages)
ros2 run ros2_benchmark benchmark_throughput --topic /scan --duration 60s

# Memory footprint
# Monitor RSS of: ros2 daemon, talker, listener, cyclonedds/fastrtps
```

### System-Level
```bash
# stress-ng (if installed)
stress-ng --cpu 4 --vm 2 --vm-bytes 512M --timeout 60s --metrics-brief

# Thermal soak
stress-ng --cpu 4 --timeout 300s &
watch -n 5 'vcgencmd measure_temp; cat /sys/class/thermal/thermal_zone0/temp'
```

---

## 6. Decisions to Confirm

| # | Decision | Options | My Lean | Your Call |
|---|----------|---------|---------|-----------|
| D1 | **RT Kernel?** | Standard / PREEMPT_RT | Standard (unless arm control) | ☐ |
| D2 | **ROS 2 Distro** | Humble (22.04) / Jazzy (24.04) | Jazzy (newer, Pi OS Bookworm base) | ☐ |
| D3 | **MCP Transport** | stdio over SSH / HTTP + token | stdio over SSH (simplest) | ☐ |
| D4 | **Primary MCP Client** | Claude Code / OpenCode / Both | OpenCode (you're using it) | ☐ |
| D5 | **Config Output Location** | On Pi (`~/configs/`) / Synced to Mac | On Pi, then `scp` back | ☐ |
| D6 | **Pre-generated Configs** | Ship in repo for Pi 4? | Yes — Week 4 deliverable | ☐ |
| D7 | **Gemini Wrapper** | Include in MVP? | Defer to Phase 2 (post-hackathon) | ☐ |

---

## 7. Next Steps (After You Confirm)

1. **Run collector** on Pi → get `pi4_profile.json`
2. **Confirm D1-D7** above
3. **Start Day 0 implementation** — fixtures + scaffold
4. **Day 1-2:** Profiler Linux backend (uses your Pi 4 fixtures)
5. **Day 3:** Assessment + tier logic (validates against Pi 4 profile)
6. **Day 4-5:** Optimizer (generates Pi 4 tuned configs)
7. **Week 2:** Full pipeline on Pi, MCP server, benchmarks

---

## 8. Quick Test — Run Collector Now

```bash
# From your Mac:
ssh armcreate@192.168.1.43 'bash -s' < /Users/mindflow/Projects/Hackathon/Arm\ Create/argus/scripts/pi4_profile_collector.sh

# Or copy and run:
scp /Users/mindflow/Projects/Hackathon/Arm\ Create/argus/scripts/pi4_profile_collector.sh armcreate@192.168.1.43:~/
ssh armcreate@192.168.1.43 'bash ~/pi4_profile_collector.sh'
scp armcreate@192.168.1.43:~/pi4_profile.json /Users/mindflow/Projects/Hackathon/Arm\ Create/argus/tests/fixtures/pi4_profile.json
```

**This single script answers Q1-Q6 from your list automatically.**

---

**Ready to run the collector and confirm D1-D7?**