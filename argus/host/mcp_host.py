"""Mac Mini Host MCP Server for Argus (argus mcp-host)."""

from __future__ import annotations

import json
import subprocess
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from argus.host.scanner import scan_network, load_targets, TargetDevice
from argus.host.bridge import connect_target, bootstrap_target, resolve_target


def run_host_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the Mac Mini Host MCP Server (`argus mcp-host`)."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        import sys
        print("Error: fastmcp package required. Run: pip install fastmcp", file=sys.stderr)
        return

    mcp = FastMCP(
        name="argus-host",
        description="Argus Host Control Plane (Mac Mini) for ARM target discovery, tunneling, and fleet proxying."
    )

    @mcp.tool()
    def host_scan_network(subnet: str = "192.168.1.0/24") -> Dict[str, Any]:
        """Scan local network and mDNS for ARM/Raspberry Pi hardware targets."""
        targets = scan_network(subnet=subnet)
        return {
            "count": len(targets),
            "targets": [t.model_dump() for t in targets]
        }

    @mcp.tool()
    def host_list_targets() -> Dict[str, Any]:
        """Return all discovered target devices in the local cache (~/.argus/targets.json)."""
        targets = load_targets()
        return {
            "count": len(targets),
            "targets": [t.model_dump() for t in targets]
        }

    @mcp.tool()
    def host_connect_target(target_id: str = "0") -> Dict[str, Any]:
        """Establish loopback SSH tunnel (`localhost:2222`) and sync MCP configurations for a target."""
        return connect_target(target_id)

    @mcp.tool()
    def host_bootstrap_target(target_id: str = "0") -> Dict[str, Any]:
        """Auto-install and verify Argus Target CLI inside remote ARM device over SSH."""
        return bootstrap_target(target_id)

    @mcp.tool()
    def host_proxy_command(command: str, target_id: str = "0") -> Dict[str, Any]:
        """Proxy and execute any raw command or Argus tool directly on the target over the loopback tunnel."""
        target = resolve_target(target_id)
        if not target:
            if target_id in ("0", "192.168.1.43"):
                target = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=2222)
            else:
                return {"success": False, "error": f"Target {target_id} not found."}

        # Check if tunnel is open, else run via direct IP or open tunnel
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no -p {target.tunnel_port} {target.username}@127.0.0.1 '{command}'"
        res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0 and "Connection refused" in res.stderr:
            # Try connecting tunnel first
            connect_target(target_id)
            res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)

        return {
            "success": res.returncode == 0,
            "target_id": target.id,
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }

    @mcp.tool()
    def ros2_check_environment(target_id: str = "0") -> Dict[str, Any]:
        """Inspect remote or local target for ROS 2 environment readiness and workspace info."""
        from argus.robotics import check_ros2_environment
        return check_ros2_environment(target_id)

    @mcp.tool()
    def ros2_create_remote_package(package_name: str, build_type: str = "ament_python", target_id: str = "0", dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scaffold a new ROS 2 package inside ~/ros2_ws/src on remote or local target."""
        from argus.robotics import ros2_create_package
        return ros2_create_package(package_name, build_type=build_type, target_id_or_ip=target_id, dependencies=dependencies)

    @mcp.tool()
    def ros2_remote_colcon_build(target_id: str = "0", package_name: Optional[str] = None) -> Dict[str, Any]:
        """Compile target ROS 2 workspace (`colcon build`)."""
        from argus.robotics import ros2_build
        return ros2_build(target_id_or_ip=target_id, pkg_name=package_name)

    @mcp.tool()
    def ros2_remote_launch(package_name: str, node_exec: str, target_id: str = "0") -> Dict[str, Any]:
        """Launch a ROS 2 node in background on target."""
        from argus.robotics import ros2_launch_node
        return ros2_launch_node(package_name, node_exec, target_id_or_ip=target_id)

    @mcp.tool()
    def ros2_remote_topic_pub(topic: str, msg_type: str, data_json: str, target_id: str = "0") -> Dict[str, Any]:
        """Publish a message (`--once`) to a ROS 2 topic on target."""
        from argus.robotics import ros2_topic_pub
        return ros2_topic_pub(topic, msg_type, data_json, target_id_or_ip=target_id)

    @mcp.tool()
    def ros2_remote_topic_echo(topic: str, target_id: str = "0", lines: int = 5) -> Dict[str, Any]:
        """Echo recent messages from a ROS 2 topic on target."""
        from argus.robotics import ros2_topic_echo
        return ros2_topic_echo(topic, target_id_or_ip=target_id, lines=lines)

    @mcp.tool()
    def ros2_deploy_smart_tv_project(target_id: str = "0") -> Dict[str, Any]:
        """Deploy and launch the Raspberry Pi Smart TV Robotics Controller project."""
        from argus.robotics import deploy_smart_tv_project
        return deploy_smart_tv_project(target_id_or_ip=target_id)

    @mcp.tool()
    def get_test_logs(phase: str = "phase3_ros2") -> List[Dict[str, Any]]:
        """Retrieve diagnostic structured JSON logs for a given phase or test suite (`phase1_banner`, `phase2_bridge`, `phase3_ros2`)."""
        from argus.common import ArgusLogger
        logger = ArgusLogger.get_instance()
        return logger.get_phase_logs(phase)

    if transport == "http":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio", show_banner=False, log_level="CRITICAL")
