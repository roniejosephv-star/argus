#!/bin/bash
# Argus-generated ROS 2 installation script
# Generated: 2026-07-16T04:40:13.028621
# Hardware: BCM2712 (Pi 5)
# Tier: ros-base
# RMW: cyclonedds
# Distro: jazzy
# OS: linux

set -euo pipefail

echo "Installing ROS 2 jazzy (ros-base tier) with cyclonedds..."

# Add ROS 2 repository
if [ "linux" = "linux" ]; then
    sudo apt update && sudo apt install -y curl gnupg2 lsb-release
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    sudo apt update
fi

# Install ROS 2 tier package
sudo apt update && sudo apt install -y ros-jazzy-ros-base ros-jazzy-cyclonedds ros-jazzy-rmw-cyclonedds-cpp

# Set up environment
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "export RMW_IMPLEMENTATION=cyclonedds" >> ~/.bashrc

# Install colcon and tools
if [ "linux" = "linux" ]; then
    sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-vcstool
fi

# Initialize rosdep
sudo rosdep init || true
rosdep update

echo "ROS 2 jazzy ros-base installation complete!"
echo "Run 'source /opt/ros/jazzy/setup.bash' to use ROS 2."
