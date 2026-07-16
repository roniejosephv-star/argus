#!/bin/bash
# pi4_profile_collector.sh — Runs on Raspberry Pi 4 to collect full hardware/software profile
# Usage: curl -sSL <url> | bash  OR  scp to Pi and run: bash pi4_profile_collector.sh
# Output: ~/pi4_profile.json (structured data for Argus)

set -euo pipefail

OUT_FILE="${HOME}/pi4_profile.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== Argus Pi 4 Profile Collector ==="
echo "Timestamp: $TIMESTAMP"
echo "Output: $OUT_FILE"
echo ""

# Helper: safe command execution
safe_cmd() {
    local cmd="$1"
    local var_name="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        eval "$var_name=\"\$(eval "$cmd" 2>/dev/null | tr -d '\n')\""
    else
        eval "$var_name=\"\""
    fi
}

# Helper: JSON escape
json_escape() {
    printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""'
}

# ============================================================
# 1. HARDWARE DETECTION
# ============================================================
echo "[1/7] Hardware Detection..."

# CPU Info
CPUINFO=$(cat /proc/cpuinfo 2>/dev/null || echo "")
CPU_MODEL=$(echo "$CPUINFO" | grep -m1 'model name' | cut -d: -f2 | xargs || echo "")
CPU_PART=$(echo "$CPUINFO" | grep -m1 'CPU part' | cut -d: -f2 | xargs || echo "")
CPU_IMPLEMENTER=$(echo "$CPUINFO" | grep -m1 'CPU implementer' | cut -d: -f2 | xargs || echo "")
CPU_VARIANT=$(echo "$CPUINFO" | grep -m1 'CPU variant' | cut -d: -f2 | xargs || echo "")
CPU_REVISION=$(echo "$CPUINFO" | grep -m1 'CPU revision' | cut -d: -f2 | xargs || echo "")
CPU_FEATURES=$(echo "$CPUINFO" | grep -m1 'Features' | cut -d: -f2 | xargs || echo "")
CORE_COUNT=$(echo "$CPUINFO" | grep -c '^processor' || echo "0")

# Memory
MEMINFO=$(cat /proc/meminfo 2>/dev/null || echo "")
MEM_TOTAL_KB=$(echo "$MEMINFO" | grep 'MemTotal' | awk '{print $2}' || echo "0")
MEM_AVAILABLE_KB=$(echo "$MEMINFO" | grep 'MemAvailable' | awk '{print $2}' || echo "0")
MEM_TOTAL_GB=$(awk "BEGIN {printf \"%.2f\", $MEM_TOTAL_KB/1024/1024}")
MEM_AVAILABLE_GB=$(awk "BEGIN {printf \"%.2f\", $MEM_AVAILABLE_KB/1024/1024}")

# Cache
CACHE_LINE=$(getconf LEVEL1_DCACHE_LINESIZE 2>/dev/null || echo "64")
L1D_SIZE=$(getconf LEVEL1_DCACHE_SIZE 2>/dev/null || echo "0")
L2_SIZE=$(getconf LEVEL2_CACHE_SIZE 2>/dev/null || echo "0")
L3_SIZE=$(getconf LEVEL3_CACHE_SIZE 2>/dev/null || echo "0")

# Board Model
DEVICETREE_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "")
FIRMWARE_MODEL=$(cat /sys/firmware/devicetree/base/model 2>/dev/null | tr -d '\0' || echo "")

# Thermal
THERMAL_ZONES=()
if [ -d /sys/class/thermal ]; then
    for zone in /sys/class/thermal/thermal_zone*; do
        if [ -f "$zone/temp" ]; then
            name=$(cat "$zone/type" 2>/dev/null || echo "unknown")
            temp=$(cat "$zone/temp" 2>/dev/null || echo "0")
            THERMAL_ZONES+=("{\"name\":\"$name\",\"temp_millicelsius\":$temp}")
        fi
    done
fi
THERMAL_JSON=$(IFS=,; echo "[${THERMAL_ZONES[*]}]")

# GPU/VPU (Pi specific)
VCGENCMD_TEMP=$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//' | sed 's/'\''C//' || echo "")
VCGENCMD_CONFIG=$(vcgencmd get_config int 2>/dev/null || echo "")

# ============================================================
# 2. OS DETECTION
# ============================================================
echo "[2/7] OS Detection..."

OS_PRETTY=$(cat /etc/os-release 2>/dev/null | grep 'PRETTY_NAME' | cut -d= -f2 | tr -d '"' || echo "")
OS_ID=$(cat /etc/os-release 2>/dev/null | grep '^ID=' | cut -d= -f2 | tr -d '"' || echo "")
OS_VERSION=$(cat /etc/os-release 2>/dev/null | grep 'VERSION_ID' | cut -d= -f2 | tr -d '"' || echo "")
KERNEL_VERSION=$(uname -r)
KERNEL_ARCH=$(uname -m)
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "")

# Check if 64-bit userland
USERLAND_BITS=$(file /bin/bash 2>/dev/null | grep -o '64-bit' || echo "32-bit")

# ============================================================
# 3. KERNEL / RT DETECTION
# ============================================================
echo "[3/7] Kernel & RT Detection..."

PREEMPT_TYPE="none"
if zcat /proc/config.gz 2>/dev/null | grep -q 'CONFIG_PREEMPT_RT_FULL=y'; then
    PREEMPT_TYPE="full"
elif zcat /proc/config.gz 2>/dev/null | grep -q 'CONFIG_PREEMPT_RT=y'; then
    PREEMPT_TYPE="rt"
elif zcat /proc/config.gz 2>/dev/null | grep -q 'CONFIG_PREEMPT=y'; then
    PREEMPT_TYPE="voluntary"
elif zcat /proc/config.gz 2>/dev/null | grep -q 'CONFIG_PREEMPT_NONE=y'; then
    PREEMPT_TYPE="none"
fi

# Also check boot config
BOOT_PREEMPT=$(grep -i preempt /boot/config-$(uname -r) 2>/dev/null | head -1 || echo "")

# ============================================================
# 4. ROS 2 DETECTION
# ============================================================
echo "[4/7] ROS 2 Detection..."

ROS_VERSION=""
ROS_DISTRO=""
RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-}"
ROS_INSTALLED="false"
ROS_PACKAGES=()

if command -v ros2 >/dev/null 2>&1; then
    ROS_INSTALLED="true"
    ROS_VERSION=$(ros2 --version 2>/dev/null | head -1 || echo "")
    # Try to detect distro from installed packages
    if apt list --installed 2>/dev/null | grep -q 'ros-humble'; then
        ROS_DISTRO="humble"
    elif apt list --installed 2>/dev/null | grep -q 'ros-iron'; then
        ROS_DISTRO="iron"
    elif apt list --installed 2>/dev/null | grep -q 'ros-jazzy'; then
        ROS_DISTRO="jazzy"
    elif apt list --installed 2>/dev/null | grep -q 'ros-rolling'; then
        ROS_DISTRO="rolling"
    fi
    # Get RMW
    if [ -z "$RMW_IMPLEMENTATION" ]; then
        RMW_IMPLEMENTATION=$(printenv RMW_IMPLEMENTATION 2>/dev/null || echo "")
    fi
    # List ROS packages
    mapfile -t ROS_PKGS < <(apt list --installed 2>/dev/null | grep '^ros-' | cut -d'/' -f1 | sort -u)
    ROS_PACKAGES_JSON=$(printf '%s\n' "${ROS_PKGS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo "[]")
else
    ROS_PACKAGES_JSON="[]"
fi

# ============================================================
# 5. NETWORK & SSH
# ============================================================
echo "[5/7] Network Detection..."

HOSTNAME=$(hostname)
IP_ADDRESSES=$(hostname -I 2>/dev/null | tr ' ' '\n' | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo "[]")
SSH_PORT=$(grep -i '^port' /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "22")

# ============================================================
# 6. STRESS TEST CAPABILITY
# ============================================================
echo "[6/7] Stress Tool Detection..."

STRESS_NG_AVAILABLE="false"
STRESS_NG_VERSION=""
if command -v stress-ng >/dev/null 2>&1; then
    STRESS_NG_AVAILABLE="true"
    STRESS_NG_VERSION=$(stress-ng --version 2>&1 | head -1 || echo "")
fi

# ============================================================
# 7. PYTHON ENVIRONMENT
# ============================================================
echo "[7/7] Python Environment..."

PYTHON_PACKAGES=$(pip3 list --format=json 2>/dev/null | python3 -c 'import json,sys; data=json.load(sys.stdin); print(json.dumps({p["name"]:p["version"] for p in data}))' 2>/dev/null || echo "{}")

# ============================================================
# GENERATE JSON OUTPUT
# ============================================================
echo ""
echo "Generating profile JSON..."

cat > "$OUT_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "collection_method": "pi4_profile_collector.sh",
  "argus_version": "0.1.0",
  
  "hardware": {
    "cpu": {
      "model_name": $(json_escape "$CPU_MODEL"),
      "cpu_part": $(json_escape "$CPU_PART"),
      "cpu_implementer": $(json_escape "$CPU_IMPLEMENTER"),
      "cpu_variant": $(json_escape "$CPU_VARIANT"),
      "cpu_revision": $(json_escape "$CPU_REVISION"),
      "features": $(json_escape "$CPU_FEATURES"),
      "core_count": $CORE_COUNT,
      "architecture": "aarch64"
    },
    "memory": {
      "total_kb": $MEM_TOTAL_KB,
      "available_kb": $MEM_AVAILABLE_KB,
      "total_gb": $MEM_TOTAL_GB,
      "available_gb": $MEM_AVAILABLE_GB
    },
    "cache": {
      "cache_line_size": $CACHE_LINE,
      "l1d_size_bytes": $L1D_SIZE,
      "l2_size_bytes": $L2_SIZE,
      "l3_size_bytes": $L3_SIZE
    },
    "board": {
      "devicetree_model": $(json_escape "$DEVICETREE_MODEL"),
      "firmware_model": $(json_escape "$FIRMWARE_MODEL")
    },
    "thermal": {
      "zones": $THERMAL_JSON,
      "vcgencmd_temp_celsius": $(json_escape "$VCGENCMD_TEMP"),
      "vcgencmd_config": $(json_escape "$VCGENCMD_CONFIG")
    }
  },
  
  "os": {
    "pretty_name": $(json_escape "$OS_PRETTY"),
    "id": $(json_escape "$OS_ID"),
    "version_id": $(json_escape "$OS_VERSION"),
    "kernel_version": $(json_escape "$KERNEL_VERSION"),
    "kernel_arch": $(json_escape "$KERNEL_ARCH"),
    "python_version": $(json_escape "$PYTHON_VERSION"),
    "userland_bits": $(json_escape "$USERLAND_BITS")
  },
  
  "kernel": {
    "preempt_type": "$PREEMPT_TYPE",
    "boot_config_preempt": $(json_escape "$BOOT_PREEMPT"),
    "config_gz_available": $(test -f /proc/config.gz && echo "true" || echo "false")
  },
  
  "ros2": {
    "installed": $ROS_INSTALLED,
    "version": $(json_escape "$ROS_VERSION"),
    "distro": $(json_escape "$ROS_DISTRO"),
    "rmw_implementation": $(json_escape "$RMW_IMPLEMENTATION"),
    "packages": $ROS_PACKAGES_JSON
  },
  
  "network": {
    "hostname": $(json_escape "$HOSTNAME"),
    "ip_addresses": $IP_ADDRESSES,
    "ssh_port": $SSH_PORT
  },
  
  "tools": {
    "stress_ng": {
      "available": $STRESS_NG_AVAILABLE,
      "version": $(json_escape "$STRESS_NG_VERSION")
    },
    "python_packages": $PYTHON_PACKAGES
  }
}
EOF

echo "=== Profile Collection Complete ==="
echo "Output: $OUT_FILE"
echo ""
echo "Summary:"
echo "  SoC: $(echo "$DEVICETREE_MODEL" | head -1)"
echo "  CPU: $CORE_COUNT cores, Part: $CPU_PART"
echo "  RAM: ${MEM_TOTAL_GB} GB"
echo "  OS: $OS_PRETTY ($OS_ID $OS_VERSION)"
echo "  Kernel: $KERNEL_VERSION ($PREEMPT_TYPE preemption)"
echo "  ROS 2: $ROS_INSTALLED ${ROS_DISTRO:+($ROS_DISTRO)}"
echo "  Userland: $USERLAND_BITS"
echo ""
echo "Next steps:"
echo "  1. Copy to your Mac: scp $USER@$(hostname -I | awk '{print $1}'):$OUT_FILE ./tests/fixtures/pi4_profile.json"
echo "  2. Or cat the file and paste: cat $OUT_FILE"
ENDOFFILE