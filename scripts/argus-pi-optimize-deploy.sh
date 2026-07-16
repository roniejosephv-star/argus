#!/bin/bash
# =============================================================================
# Argus Pi 4 Optimization & Deployment Script
# Run this ON THE PI (via monitor/keyboard) to:
# 1. Fix WiFi stability
# 2. Debloat Ubuntu Server 24.04 for ROS 2
# 3. Install Argus CLI
# 4. Run assessment and generate configs
# =============================================================================

set -euo pipefail

LOG_FILE="/tmp/argus-pi-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "==========================================="
echo "Argus Pi 4 Optimization & Deployment"
echo "==========================================="
echo "Log: $LOG_FILE"
echo ""

# =============================================================================
# SECTION 1: Fix WiFi Stability (MUST RUN FIRST)
# =============================================================================
echo "[1/8] Fixing WiFi power management..."

sudo iwconfig wlan0 power off 2>/dev/null || true

# Make permanent
echo -e "[connection]\nwifi.powersave = 2" | sudo tee /etc/NetworkManager/conf.d/wifi-powersave.conf >/dev/null
sudo systemctl restart NetworkManager

# Verify
sleep 2
iwconfig wlan0 | grep -i "power management" || true

echo "✓ WiFi power management disabled"
echo ""

# =============================================================================
# SECTION 2: System Update & Essential Packages
# =============================================================================
echo "[2/8] Updating system and installing essentials..."

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    git curl wget \
    build-essential cmake \
    htop iotop iftop \
    vim nano \
    net-tools iproute2 \
    2>&1 | tail -20

echo "✓ Essential packages installed"
echo ""

# =============================================================================
# SECTION 3: Debloat Ubuntu Server - Remove Unnecessary Packages
# =============================================================================
echo "[3/8] Debloating Ubuntu Server (removing unnecessary packages)..."

# List of packages to remove (safe to remove for ROS 2 headless)
PACKAGES_TO_REMOVE=(
    # Cloud/init
    cloud-init cloud-guest-utils cloud-initramfs-copymods
    # Snap (we use apt)
    snapd
    # Unneeded services
    modemmanager ppp pppconfig pppoeconf
    popularity-contest
    # Documentation/man
    man-db manpages
    # Unneeded locale/fonts
    fonts-noto-core fonts-dejavu-core
    # Unneeded sound
    pulseaudio bluez bluez-cups
    # Unneeded printing
    cups cups-browsed
    # Unneeded X11 (headless)
    x11-common x11-utils x11-xkb-utils x11-xserver-utils
    # Unneeded kernels (keep current)
    # linux-image-generic linux-headers-generic
)

echo "Removing unnecessary packages..."
for pkg in "${PACKAGES_TO_REMOVE[@]}"; do
    if dpkg -l | grep -q "^ii  $pkg "; then
        sudo apt-get remove -y --purge "$pkg" 2>/dev/null && echo "  Removed: $pkg" || true
    fi
done

# Clean up
sudo apt-get autoremove -y --purge
sudo apt-get autoclean
sudo apt-get clean

# Remove cloud-init artifacts
sudo rm -rf /var/lib/cloud/instances/*
sudo rm -rf /etc/cloud/cloud.cfg.d/99-installer.cfg 2>/dev/null || true
sudo sed -i 's/^datasource_list:.*/datasource_list: [None]/' /etc/cloud/cloud.cfg 2>/dev/null || true

echo "✓ Debloating complete"
echo ""

# =============================================================================
# SECTION 4: Disable Unnecessary Services
# =============================================================================
echo "[4/8] Disabling unnecessary services..."

SERVICES_TO_DISABLE=(
    snapd.service
    snapd.socket
    snapd.seeded.service
    cloud-init.service
    cloud-config.service
    cloud-final.service
    cloud-init-local.service
    ModemManager.service
    bluetooth.service
    cups.service
    cups-browsed.service
    avahi-daemon.service
    systemd-resolved.service
)

for svc in "${SERVICES_TO_DISABLE[@]}"; do
    if systemctl list-unit-files | grep -q "^$svc"; then
        sudo systemctl disable --now "$svc" 2>/dev/null && echo "  Disabled: $svc" || true
    fi
done

# Keep essential: ssh, NetworkManager, systemd-timesyncd, cron, systemd-journald

echo "✓ Services optimized"
echo ""

# =============================================================================
# SECTION 5: Kernel Parameters for ROS 2 Real-time Performance
# =============================================================================
echo "[5/8] Optimizing kernel parameters for ROS 2..."

sudo tee /etc/sysctl.d/99-argus-ros2.conf > /dev/null <<'EOF'
# Argus ROS 2 Kernel Optimizations for Pi 4

# Network buffers for DDS traffic
net.core.rmem_max = 8388608
net.core.wmem_max = 8388608
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.core.netdev_max_backlog = 5000
net.core.somaxconn = 1024

# IP fragmentation for large DDS packets
net.ipv4.ipfrag_time = 30
net.ipv4.ipfrag_high_thresh = 16777216
net.ipv4.ipfrag_low_thresh = 8388608

# Memory management for ROS 2 nodes
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.swappiness = 10
vm.vfs_cache_pressure = 50

# Scheduler for real-time workloads
kernel.sched_autogroup_enabled = 0
kernel.sched_min_granularity_ns = 1000000
kernel.sched_wakeup_granularity_ns = 1500000
kernel.sched_rt_runtime_us = 950000

# Disable transparent hugepages (latency spikes)
# echo never > /sys/kernel/mm/transparent_hugepage/enabled

# Network stack
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0

# File system
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 1024
EOF

sudo sysctl --system 2>/dev/null | tail -5

echo "✓ Kernel parameters applied"
echo ""

# =============================================================================
# SECTION 6: CPU Governor - Performance Mode
# =============================================================================
echo "[6/8] Setting CPU governor to performance..."

# Install cpufrequtils if not present
if ! command -v cpufreq-set &>/dev/null; then
    sudo apt-get install -y cpufrequtils
fi

# Set performance governor
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee "$cpu" >/dev/null 2>&1 || true
done

# Make permanent
sudo sed -i 's/^GOVERNOR=.*/GOVERNOR="performance"/' /etc/default/cpufrequtils 2>/dev/null || true

echo "✓ CPU governor set to performance"
echo ""

# =============================================================================
# SECTION 7: Install ROS 2 Jazzy (Official Ubuntu Repo)
# =============================================================================
echo "[7/8] Installing ROS 2 Jazzy..."

# Add ROS 2 apt repository
sudo apt-get install -y curl gnupg2 lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt-get update
sudo apt-get install -y \
    ros-jazzy-ros-base \
    ros-jazzy-cyclonedds \
    ros-jazzy-rmw-cyclonedds-cpp \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool

# Initialize rosdep
sudo rosdep init 2>/dev/null || true
rosdep update

# Setup environment
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc

echo "✓ ROS 2 Jazzy installed"
echo ""

# =============================================================================
# SECTION 8: Install Argus CLI
# =============================================================================
echo "[8/8] Installing Argus CLI..."

cd ~
if [ -d "argus" ]; then
    cd argus && git pull 2>/dev/null || true
else
    git clone https://github.com/roniejosephv-star/argus.git
    cd argus
fi

# Install Argus in development mode
pip install -e . --break-system-packages

# Verify installation
argus --version

echo ""
echo "==========================================="
echo "Running Argus Assessment..."
echo "==========================================="

# Run full assessment with config generation
argus diagnose --detailed
echo ""
argus assess --output-dir ~/pi4-configs

echo ""
echo "==========================================="
echo "✅ SETUP COMPLETE!"
echo "==========================================="
echo ""
echo "Generated configs in: ~/pi4-configs/"
ls -la ~/pi4-configs/
echo ""
echo "Next steps:"
echo "  1. Review configs: cat ~/pi4-configs/cyclonedds.xml"
echo "  2. Apply sysctl: sudo sysctl -p ~/pi4-configs/sysctl.conf"
echo "  3. Source ROS 2: source /opt/ros/jazzy/setup.bash"
echo "  4. Run MCP server: argus mcp serve --transport stdio"
echo ""
echo "For OpenCode/Claude Code MCP config:"
echo '  {"mcpServers":{"argus-pi4":{"command":"ssh","args":["pi@raspberrypi.local","argus","mcp","serve","--transport","stdio"]}}}'
echo ""
echo "Log saved to: $LOG_FILE"