# Argus Deployment & Operations Guide

**Version**: 1.0  
**Date**: 2026-07-10  
**Status**: Draft

---

## 1. Installation

### 1.1 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| pip | 23+ | Included with Python |
| git | Any | Only for source install |
| OS | macOS 14+ (arm64) or Linux aarch64 | x86 not supported |

### 1.2 Quick Install (from source)

```bash
# 1. Clone
git clone https://github.com/your-org/argus.git
cd argus

# 2. Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install
pip install -e .

# 4. Verify
argus --version
# → Argus v0.1.0
```

### 1.3 Optional Dependencies

```bash
# Gemini CLI wrapper
pip install google-genai

# Extended hardware topology (Linux only)
pip install pyhwloc

# Human-readable config diffing (MCP)
pip install mcp  # Included via FastMCP vendor
```

### 1.4 Verify Installation

```bash
argus diagnose
```

Expected output:

```
╭─ Arm SoC Profile ─────────────────────────╮
│ Model:        Apple M3 Pro                 │
│ OS:           macOS 15.2 (arm64)           │
│ ...                                         │
╰────────────────────────────────────────────╯
```

### 1.5 Clean Installation Test

```bash
# On a clean system (or Docker):
python3 -m venv /tmp/argus-test
source /tmp/argus-test/bin/activate
pip install -e /path/to/argus
argus --version
argus diagnose
argus assess --no-configs
deactivate
rm -rf /tmp/argus-test
```

---

## 2. Cross-Platform Setup

### 2.1 macOS (Apple Silicon)

```
Target: Mac with M1/M2/M3/M4 series chip
No additional tools required.

Native path: sysctl, IOKit, sw_vers
```

### 2.2 Raspberry Pi 4/5 (Linux aarch64)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3 python3-pip python3-venv build-essential

# Optional: stress-ng for extended stress testing
sudo apt install -y stress-ng

# Optional: pyhwloc
sudo apt install -y libhwloc-dev
pip install pyhwloc

# Clone and install
git clone https://github.com/your-org/argus.git
cd argus
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Test
argus diagnose
```

### 2.3 Jetson (Linux aarch64)

```bash
# Same as Pi setup
# Jetson-specific: check for thermal zones
ls /sys/class/thermal/
# Should show thermal_zone0..N
```

### 2.4 QEMU (for development/testing)

```bash
# Run Linux aarch64 in emulation for cross-platform testing
docker run --platform linux/arm64 -it --rm ubuntu:24.04
apt update && apt install -y python3 python3-pip python3-venv git
# Then install argus as above
```

Note: Stress testing inside QEMU will show degraded performance vs native. Use for functional testing only.

---

## 3. MCP Client Setup

### 3.1 Claude Code

Create `claude_code_config.json`:

```json
{
    "mcpServers": {
        "argus": {
            "command": "argus",
            "args": ["mcp", "serve"],
            "env": {}
        }
    }
}
```

Then in Claude Code:

```
/tools → Argus tools should appear in the tool list
```

### 3.2 Gemini CLI Wrapper

```bash
# 1. Set API key
export ARGUS_GEMINI_KEY="your-gemini-api-key-here"

# 2. Run
python scripts/argus_mcp_gemini.py "Optimize my M3 Pro for ROS 2"
```

### 3.3 MCP Inspector

```bash
# Start HTTP server
argus mcp serve --transport http --port 8080

# Open in browser:
# http://localhost:8080/mcp/inspector

# Or use npx:
npx @modelcontextprotocol/inspector
# → Enter URL: http://localhost:8080/mcp
```

### 3.4 Custom Python Client

```python
import httpx

response = httpx.post(
    "http://localhost:8080/mcp",
    json={"method": "tools/call", "params": {"name": "detect_arm_soc", "arguments": {}}},
    headers={"Authorization": "Bearer your-token"},
)
print(response.json())
```

---

## 4. CI/CD Pipeline

### 4.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=argus --cov-fail-under=85

  test-linux-arm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
      - name: Test in aarch64 container
        run: |
          docker run --platform linux/arm64 -v $PWD:/argus ubuntu:24.04 \
            bash -c "apt update && apt install -y python3 python3-pip python3-venv &&
                     cd /argus && pip install -e . && pytest tests/ -v"
```

### 4.2 Test Matrix

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
    os: [macos-latest, ubuntu-latest]
```

### 4.3 PyPI Publishing (Phase 3)

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
```

---

## 5. Versioning

### 5.1 Semantic Versioning

```
MAJOR.MINOR.PATCH

MAJOR: Breaking API changes (tool signature changes, config format changes)
MINOR: New features (new tools, new config types)
PATCH: Bug fixes, performance improvements
```

### 5.2 Version Source

```python
# argus/__init__.py
__version__ = "0.1.0"
```

Single source of truth. Updated via `argus --version`.

### 5.3 Changelog Convention

```
# Changelog

## [0.1.0] - 2026-07-10
### Added
- Hardware profiling (macOS + Linux)
- CPU/memory stress testing
- Hardware assessment with 5-tier scoring
- Configuration generation (CycloneDDS, Fast DDS, Zenoh, sysctl, build flags)
- MCP server (stdio + HTTP)
- Permission gatekeeper with blast radius
- Report generation with lesson management
- Gemini CLI wrapper
```

---

## 6. Troubleshooting

### 6.1 Common Issues

| Symptom | Cause | Solution |
|---|---|---|
| `argus: command not found` | Not installed or venv not active | `pip install -e .` or `source .venv/bin/activate` |
| `No module named 'argus'` | Python path issue | `pip install -e .` from project root |
| `Permission denied` | Gatekeeper blocked operation | Use `argus assess` with `--report` to approve via CLI |
| `ARGUS_GEMINI_KEY not set` | Missing env var | `export ARGUS_GEMINI_KEY="<key>"` |
| `No thermal sensors found` | Feature not available | Feature works on macOS and Linux with /sys/class/thermal |
| `XML parsing failed` | Invalid template | File a bug with the generated config |
| `Fingerprint mismatch` | Hardware changed | Re-run `argus diagnose` |
| `MCP connection refused` | Server not running | `argus mcp serve --transport http` |
| `401 Unauthorized` | Missing/incorrect Bearer token | Set `ARGUS_MCP_TOKEN` on server |

### 6.2 Debug Mode

```bash
# Set log level
export ARGUS_LOG_LEVEL=DEBUG
argus diagnose

# Pipe output to file
argus assess --report 2>&1 | tee /tmp/argus-debug.log
```

### 6.3 Clean Reset

```bash
# Remove all reports and configs
rm -rf ~/.argus/
```

### 6.4 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `ARGUS_MCP_TOKEN` | For HTTP | None | Bearer token for MCP HTTP transport |
| `ARGUS_GEMINI_KEY` | For Gemini wrapper | None | Google Gemini API key |
| `ARGUS_LOG_LEVEL` | No | INFO | Log level (DEBUG, INFO, WARNING, ERROR) |
| `ARGUS_CONFIG_DIR` | No | `~/.argus/` | Override default config directory |
