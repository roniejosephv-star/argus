"""MCP server for Argus - exposes all tools via FastMCP."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from argus.core.toolbox import execute_tool, TOOL_REGISTRY
from argus.safety import create_gatekeeper, Gatekeeper
from argus.mcp.auth import BearerAuthMiddleware
from argus.mcp.resources import RESOURCE_HANDLERS, PROMPTS


# Global gatekeeper (auto-approve for MCP since client handles user)
_gatekeeper = create_gatekeeper(auto_approve=True)


def create_server() -> FastMCP:
    """Create and configure FastMCP server with all Argus tools."""
    mcp = FastMCP("argus")
    
    # Register tools with proper typed signatures
    @mcp.tool(name="detect_arm_soc", description="Detect Arm SoC model, cores, cache, ISA features, and RAM")
    async def detect_arm_soc_mcp(detailed: bool = False) -> Any:
        return execute_tool("detect_arm_soc", {"detailed": detailed})

    @mcp.tool(name="detect_os", description="Detect operating system, kernel, and architecture")
    async def detect_os_mcp() -> Any:
        return execute_tool("detect_os", {})

    @mcp.tool(name="stress_cpu", description="Run CPU stress test and return bogo-ops/sec + thermal data")
    async def stress_cpu_mcp(duration_s: int = 10, workers: int | None = None) -> Any:
        return execute_tool("stress_cpu", {"duration_s": duration_s, "workers": workers})

    @mcp.tool(name="stress_memory", description="Run memory bandwidth stress test (STREAM-like)")
    async def stress_memory_mcp(duration_s: int = 10, array_size_mb: int = 256) -> Any:
        return execute_tool("stress_memory", {"duration_s": duration_s, "array_size_mb": array_size_mb})

    @mcp.tool(name="measure_thermal", description="Measure current system temperature from thermal sensors")
    async def measure_thermal_mcp() -> Any:
        return execute_tool("measure_thermal", {})

    @mcp.tool(name="measure_ram", description="Sample RAM usage of a process or system over time")
    async def measure_ram_mcp(pid: int | None = None, interval_s: float = 1.0, duration_s: int = 10) -> Any:
        return execute_tool("measure_ram", {"pid": pid, "interval_s": interval_s, "duration_s": duration_s})

    @mcp.tool(name="assess_hardware", description="Assess hardware for ROS 2 suitability and generate tier scorecard")
    async def assess_hardware_mcp() -> Any:
        return execute_tool("assess_hardware", {})

    @mcp.tool(name="generate_cyclonedds_config", description="Generate optimized CycloneDDS XML configuration")
    async def generate_cyclonedds_config_mcp(dds_profile: str = "balanced") -> Any:
        return execute_tool("generate_cyclonedds_config", {"dds_profile": dds_profile})

    @mcp.tool(name="generate_fastdds_config", description="Generate optimized Fast DDS XML configuration")
    async def generate_fastdds_config_mcp(dds_profile: str = "balanced") -> Any:
        return execute_tool("generate_fastdds_config", {"dds_profile": dds_profile})

    @mcp.tool(name="generate_zenoh_advice", description="Generate Zenoh adoption guidance for this hardware")
    async def generate_zenoh_advice_mcp() -> Any:
        return execute_tool("generate_zenoh_advice", {})

    @mcp.tool(name="generate_sysctl_config", description="Generate optimized sysctl kernel parameters for ROS 2")
    async def generate_sysctl_config_mcp() -> Any:
        return execute_tool("generate_sysctl_config", {})

    @mcp.tool(name="generate_build_flags", description="Generate Arm-optimized compiler build flags for ROS 2")
    async def generate_build_flags_mcp() -> Any:
        return execute_tool("generate_build_flags", {})

    @mcp.tool(name="generate_install_script", description="Generate ROS 2 installation script for assessed tier")
    async def generate_install_script_mcp(os: str | None = None, tier: str | None = None) -> Any:
        return execute_tool("generate_install_script", {"os": os, "tier": tier})

    @mcp.tool(name="generate_all_configs", description="Generate all 6 config artifacts (DDS, sysctl, build, install) to disk")
    async def generate_all_configs_mcp(output_dir: str = "./configs") -> Any:
        return execute_tool("generate_all_configs", {"output_dir": output_dir})

    @mcp.tool(name="detect_serial_ports", description="Detect available hardware serial/UART ports and inspect getty/console conflicts")
    async def detect_serial_ports_mcp() -> Any:
        return execute_tool("detect_serial_ports", {})

    @mcp.tool(name="configure_micro_ros_uart", description="Generate scripts and systemd unit to dedicate hardware serial /dev/ttyAMA0 to micro-ROS")
    async def configure_micro_ros_uart_mcp(device: str = "/dev/ttyAMA0", baudrate: int = 115200) -> Any:
        return execute_tool("configure_micro_ros_uart", {"device": device, "baudrate": baudrate})

    @mcp.tool(name="project_list_files", description="Remote project management: list workspace directory structure and files")
    async def project_list_files_mcp(directory: str = ".", pattern: str = "*", recursive: bool = False, max_depth: int = 3) -> Any:
        return execute_tool("project_list_files", {"directory": directory, "pattern": pattern, "recursive": recursive, "max_depth": max_depth})

    @mcp.tool(name="project_read_file", description="Remote project management: read contents of a file in the workspace")
    async def project_read_file_mcp(file_path: str, max_lines: int = 500) -> Any:
        return execute_tool("project_read_file", {"file_path": file_path, "max_lines": max_lines})

    @mcp.tool(name="project_write_file", description="Remote project management: write or edit a file in the workspace with automatic backup")
    async def project_write_file_mcp(file_path: str, content: str, backup: bool = True) -> Any:
        return execute_tool("project_write_file", {"file_path": file_path, "content": content, "backup": backup})

    @mcp.tool(name="project_git_status", description="Remote project management: inspect git branch and modified files status")
    async def project_git_status_mcp(directory: str = ".") -> Any:
        return execute_tool("project_git_status", {"directory": directory})

    @mcp.tool(name="project_git_diff", description="Remote project management: view git diff of workspace or specific file")
    async def project_git_diff_mcp(directory: str = ".", file_path: str | None = None) -> Any:
        return execute_tool("project_git_diff", {"directory": directory, "file_path": file_path})

    @mcp.tool(name="project_pip_install", description="Remote project management: install Python dependencies via pip safely")
    async def project_pip_install_mcp(package: str = "-e .", break_system_packages: bool = True) -> Any:
        return execute_tool("project_pip_install", {"package": package, "break_system_packages": break_system_packages})

    @mcp.tool(name="project_run_command", description="Remote project management: execute build or test commands (colcon build, pytest) with timeout")
    async def project_run_command_mcp(command: str, cwd: str = ".", timeout_s: int = 300) -> Any:
        return execute_tool("project_run_command", {"command": command, "cwd": cwd, "timeout_s": timeout_s})

    @mcp.tool(name="ros2_status", description="Check ROS 2 installation status on this target device")
    async def ros2_status_mcp() -> Any:
        from argus.robotics import check_ros2_environment
        return check_ros2_environment("host")

    @mcp.tool(name="ros2_create_package", description="Scaffold a new ROS 2 package inside ~/ros2_ws/src")
    async def ros2_create_package_mcp(package_name: str, build_type: str = "ament_python", dependencies: list[str] | None = None) -> Any:
        from argus.robotics import ros2_create_package
        return ros2_create_package(package_name, build_type=build_type, target_id_or_ip="host", dependencies=dependencies)

    @mcp.tool(name="ros2_build", description="Compile ROS 2 workspace (~/ros2_ws) using colcon build")
    async def ros2_build_mcp(package_name: str | None = None) -> Any:
        from argus.robotics import ros2_build
        return ros2_build(target_id_or_ip="host", pkg_name=package_name)

    @mcp.tool(name="ros2_launch", description="Launch a ROS 2 node in background")
    async def ros2_launch_mcp(package_name: str, node_exec: str) -> Any:
        from argus.robotics import ros2_launch_node
        return ros2_launch_node(package_name, node_exec, target_id_or_ip="host")

    @mcp.tool(name="ros2_pub", description="Publish a message (`--once`) to a ROS 2 topic")
    async def ros2_pub_mcp(topic: str, msg_type: str, data_json: str) -> Any:
        from argus.robotics import ros2_topic_pub
        return ros2_topic_pub(topic, msg_type, data_json, target_id_or_ip="host")

    @mcp.tool(name="ros2_echo", description="Echo recent messages from a ROS 2 topic")
    async def ros2_echo_mcp(topic: str, lines: int = 5) -> Any:
        from argus.robotics import ros2_topic_echo
        return ros2_topic_echo(topic, target_id_or_ip="host", lines=lines)

    @mcp.tool(name="deploy_smart_tv_project", description="Deploy and launch the Smart TV Robotics Controller node on this device")
    async def deploy_smart_tv_project_mcp() -> Any:
        from argus.robotics import deploy_smart_tv_project
        return deploy_smart_tv_project("host")

    @mcp.tool(name="get_test_logs", description="Retrieve diagnostic structured JSON logs (`phase1_banner`, `phase2_bridge`, `phase3_ros2`)")
    async def get_test_logs_mcp(phase: str = "phase3_ros2") -> Any:
        from argus.common import ArgusLogger
        logger = ArgusLogger.get_instance()
        return logger.get_phase_logs(phase)
    
    # Register resources
    for uri, handler in RESOURCE_HANDLERS.items():
        mcp.resource(uri)(lambda: handler())
    
    # Register prompts
    for name, prompt in PROMPTS.items():
        mcp.prompt(name=name)(lambda: prompt)
    
    return mcp


async def run_stdio():
    """Run MCP server over stdio transport."""
    server = create_server()
    await server.run_stdio_async(show_banner=False, log_level="CRITICAL")


async def run_http(host: str = "127.0.0.1", port: int = 8765):
    """Run MCP server over HTTP transport with Bearer auth."""
    from mcp.server.sse import SseServerTransport
    from mcp.server import Server
    import uvicorn
    
    server = create_server()
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
    
    # Create Starlette app with auth
    app = Starlette(
        routes=[
            Route("/sse", handle_sse),
            Route("/messages/", sse.handle_post_message),
            Route("/health", health_check),
        ],
        middleware=[
            Middleware(CORSMiddleware, allow_origins=["*"]),
        ],
    )
    
    # Add Bearer auth if token configured
    token = os.environ.get("ARGUS_MCP_TOKEN")
    if token:
        app.add_middleware(BearerAuthMiddleware, token=token)
    
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


async def health_check(request):
    return JSONResponse({"status": "ok", "service": "argus-mcp"})


def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765):
    """Entry point for running MCP server."""
    import asyncio
    
    if transport == "stdio":
        asyncio.run(run_stdio())
    elif transport == "http":
        asyncio.run(run_http(host, port))
    else:
        raise ValueError(f"Unknown transport: {transport}")