#!/bin/bash
# =============================================================================
# Quick Argus Deploy Script for Pi 4 (Run AFTER network is stable)
# =============================================================================

set -euo pipefail

echo "==========================================="
echo "Quick Argus Deploy for Pi 4"
echo "==========================================="

# 1. Install Argus
echo "[1/4] Installing Argus..."
cd ~
if [ -d "argus" ]; then
    cd argus && git pull
else
    git clone https://github.com/roniejosephv-star/argus.git
    cd argus
fi

pip install -e . --break-system-packages

# 2. Verify
echo "[2/4] Verifying installation..."
argus --version

# 3. Run assessment
echo "[3/4] Running hardware assessment..."
argus diagnose --detailed
argus assess --output-dir ~/pi4-configs

# 4. Show results
echo "[4/4] Results:"
ls -la ~/pi4-configs/
echo ""
cat ~/pi4-configs/metadata.yaml
echo ""
echo "✅ Done! Apply sysctl: sudo sysctl -p ~/pi4-configs/sysctl.conf"
echo "Source ROS 2: source /opt/ros/jazzy/setup.bash"