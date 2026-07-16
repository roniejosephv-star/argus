"""Tool registry and dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Type
from pydantic import BaseModel

from argus.safety.blast_radius import BlastRadius
from argus.safety.gatekeeper import create_gatekeeper
from argus.core import (
    detect_arm_soc, detect_os, assess_hardware,
    generate_cyclonedds_xml, generate_fastdds_xml, generate_zenoh_advice,
    generate_sysctl_config, generate_build_flags, generate_install_script,
    generate_all_configs, stress_cpu, stress_memory, measure_thermal,
    sample_ram, detect_serial_ports, configure_micro_ros_uart,
    project_list_files, project_read_file, project_write_file,
    project_git_status, project_git_diff, project_pip_install,
    project_run_command, ProjectListFilesParams, ProjectReadFileParams,
    ProjectWriteFileParams, ProjectGitStatusParams, ProjectGitDiffParams,
    ProjectPipInstallParams, ProjectRunCommandParams,
)


# Parameter models for each tool
class ConfigureMicroRosParams(BaseModel):
    device: str = "/dev/ttyAMA0"
    baudrate: int = 115200


class DetectArmSocParams(BaseModel):
    detailed: bool = False


class StressCpuParams(BaseModel):
    duration_s: int = 10
    workers: int | None = None


class StressMemoryParams(BaseModel):
    duration_s: int = 10
    array_size_mb: int = 256


class MeasureRamParams(BaseModel):
    pid: int | None = None
    interval_s: float = 1.0
    duration_s: int = 10


class GenerateDdsConfigParams(BaseModel):
    dds_profile: str = "balanced"


class GenerateInstallScriptParams(BaseModel):
    os: str | None = None
    tier: str | None = None


class GenerateAllConfigsParams(BaseModel):
    output_dir: str = "./configs"


class GenerateReportParams(BaseModel):
    reason: str = "manual"


class DiffReportsParams(BaseModel):
    report_id_1: str
    report_id_2: str


@dataclass
class ToolSpec:
    name: str
    description: str
    category: str
    blast_radius: BlastRadius
    timeout_s: int
    parameters: Type[BaseModel]
    handler: Callable


TOOL_REGISTRY: dict[str, ToolSpec] = {}

_gatekeeper = create_gatekeeper(auto_approve=False)


def register_tool(spec: ToolSpec) -> None:
    """Register a tool in the global registry."""
    TOOL_REGISTRY[spec.name] = spec


def execute_tool(name: str, args: dict) -> Any:
    """Execute a tool by name with validated arguments."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    
    spec = TOOL_REGISTRY[name]
    
    # Validate parameters
    try:
        validated = spec.parameters(**args)
    except Exception as e:
        return {"error": f"Invalid parameters: {e}"}
    
    # Check permission
    decision = _gatekeeper.check_permission(spec, args)
    
    if not decision.allowed:
        if decision.requires_prompt:
            # In CLI mode, gatekeeper handles prompting
            # In MCP mode, return permission_required response
            if _gatekeeper.auto_approve:
                pass  # Will be handled by CLI
            else:
                return {
                    "error": "Permission denied",
                    "permission_required": True,
                    "tool": name,
                    "blast_radius": decision.blast_radius.value,
                    "reason": decision.reason,
                }
        else:
            return {
                "error": "Permission denied",
                "tool": name,
                "blast_radius": decision.blast_radius.value,
                "reason": decision.reason,
            }
    
    # Execute handler
    try:
        result = spec.handler(**validated.model_dump())
        return result
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}


def get_mcp_tool_definitions() -> list[dict]:
    """Get tool definitions in FastMCP format."""
    definitions = []
    for spec in TOOL_REGISTRY.values():
        # Get JSON schema from Pydantic model
        schema = spec.parameters.model_json_schema()
        definitions.append({
            "name": spec.name,
            "description": spec.description,
            "inputSchema": schema,
        })
    return definitions


def get_tool_list() -> list[dict]:
    """Get human-readable tool listing."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "category": spec.category,
            "blast_radius": spec.blast_radius.value,
        }
        for spec in TOOL_REGISTRY.values()
    ]


def set_auto_approve(enabled: bool):
    """Enable/disable auto-approval (for CI/non-interactive)."""
    _gatekeeper.auto_approve = enabled


# ============================================================
# Tool Handlers
# ============================================================

def _detect_arm_soc(detailed: bool = False) -> dict:
    profile = detect_arm_soc(detailed=detailed)
    return profile.model_dump()


def _detect_os() -> dict:
    return detect_os()


def _stress_cpu(duration_s: int = 10, workers: int | None = None) -> dict:
    result = stress_cpu(duration_s=duration_s, workers=workers)
    return result.model_dump()


def _stress_memory(duration_s: int = 10, array_size_mb: int = 256) -> dict:
    result = stress_memory(duration_s=duration_s, array_size_mb=array_size_mb)
    return result.model_dump()


def _measure_thermal() -> dict:
    return measure_thermal()


def _measure_ram(pid: int | None = None, interval_s: float = 1.0, duration_s: int = 10) -> dict:
    return sample_ram(pid=pid, interval_s=interval_s, duration_s=duration_s)


def _assess_hardware() -> dict:
    profile = detect_arm_soc()
    result = assess_hardware(profile)
    return result.model_dump()


def _generate_cyclonedds_config(dds_profile: str = "balanced") -> dict:
    profile = detect_arm_soc()
    xml = generate_cyclonedds_xml(profile, dds_profile)
    return {"xml": xml, "summary": f"CycloneDDS {dds_profile} profile generated"}


def _generate_fastdds_config(dds_profile: str = "balanced") -> dict:
    profile = detect_arm_soc()
    xml = generate_fastdds_xml(profile, dds_profile)
    return {"xml": xml, "summary": f"Fast DDS {dds_profile} profile generated"}


def _generate_zenoh_advice() -> dict:
    profile = detect_arm_soc()
    advice = generate_zenoh_advice(profile)
    return {"advice": advice, "summary": "Zenoh adoption guidance generated"}


def _generate_sysctl_config() -> dict:
    profile = detect_arm_soc()
    config = generate_sysctl_config(profile)
    return {"config": config, "summary": "sysctl configuration generated"}


def _generate_build_flags() -> dict:
    profile = detect_arm_soc()
    flags = generate_build_flags(profile)
    return {"flags": flags, "summary": "Build flags generated"}


def _generate_install_script(os: str | None = None, tier: str | None = None) -> dict:
    profile = detect_arm_soc()
    # Auto-detect OS if not provided
    if os is None:
        os = profile.os
    # Auto-detect tier if not provided
    if tier is None:
        result = assess_hardware(profile)
        tier = result.tier.value
    script = generate_install_script(profile, tier, result.recommended_rmw.value)
    return {"script": script, "summary": f"Install script for {tier} tier with {result.recommended_rmw.value}"}


def _generate_all_configs(output_dir: str = "./configs") -> dict:
    profile = detect_arm_soc()
    scorecard = assess_hardware(profile)
    artifact = generate_all_configs(profile, scorecard, output_dir)
    return {
        "artifacts": [f.name for f in artifact.files],
        "output_dir": str(artifact.soc_model),
        "count": len(artifact.files),
    }


def _detect_serial_ports() -> dict:
    ports = detect_serial_ports()
    return {"ports": ports, "count": len(ports)}


def _configure_micro_ros_uart(device: str = "/dev/ttyAMA0", baudrate: int = 115200) -> dict:
    return configure_micro_ros_uart(device=device, baudrate=baudrate)


def _project_list_files(directory: str = ".", pattern: str = "*", recursive: bool = False, max_depth: int = 3) -> dict:
    return project_list_files(directory=directory, pattern=pattern, recursive=recursive, max_depth=max_depth)


def _project_read_file(file_path: str, max_lines: int = 500) -> dict:
    return project_read_file(file_path=file_path, max_lines=max_lines)


def _project_write_file(file_path: str, content: str, backup: bool = True) -> dict:
    return project_write_file(file_path=file_path, content=content, backup=backup)


def _project_git_status(directory: str = ".") -> dict:
    return project_git_status(directory=directory)


def _project_git_diff(directory: str = ".", file_path: str | None = None) -> dict:
    return project_git_diff(directory=directory, file_path=file_path)


def _project_pip_install(package: str = "-e .", break_system_packages: bool = True) -> dict:
    return project_pip_install(package=package, break_system_packages=break_system_packages)


def _project_run_command(command: str, cwd: str = ".", timeout_s: int = 300) -> dict:
    return project_run_command(command=command, cwd=cwd, timeout_s=timeout_s)


# ============================================================
# Register All Tools
# ============================================================

register_tool(ToolSpec(
    name="detect_arm_soc",
    description="Detect Arm SoC model, cores, cache, ISA features, and RAM",
    category="discover",
    blast_radius=BlastRadius.NONE,
    timeout_s=5,
    parameters=DetectArmSocParams,
    handler=_detect_arm_soc,
))

register_tool(ToolSpec(
    name="detect_os",
    description="Detect operating system, kernel, and architecture",
    category="discover",
    blast_radius=BlastRadius.NONE,
    timeout_s=5,
    parameters=type('DetectOsParams', (BaseModel,), {}),
    handler=_detect_os,
))

register_tool(ToolSpec(
    name="stress_cpu",
    description="Run CPU stress test and return bogo-ops/sec + thermal data",
    category="profile",
    blast_radius=BlastRadius.LOW,
    timeout_s=300,
    parameters=StressCpuParams,
    handler=_stress_cpu,
))

register_tool(ToolSpec(
    name="stress_memory",
    description="Run memory bandwidth stress test (STREAM-like)",
    category="profile",
    blast_radius=BlastRadius.LOW,
    timeout_s=300,
    parameters=StressMemoryParams,
    handler=_stress_memory,
))

register_tool(ToolSpec(
    name="measure_thermal",
    description="Measure current system temperature from thermal sensors",
    category="profile",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=type('MeasureThermalParams', (BaseModel,), {}),
    handler=_measure_thermal,
))

register_tool(ToolSpec(
    name="measure_ram",
    description="Sample RAM usage of a process or system over time",
    category="profile",
    blast_radius=BlastRadius.NONE,
    timeout_s=300,
    parameters=MeasureRamParams,
    handler=_measure_ram,
))

register_tool(ToolSpec(
    name="assess_hardware",
    description="Assess hardware for ROS 2 suitability and generate tier scorecard",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=type('AssessHardwareParams', (BaseModel,), {}),
    handler=_assess_hardware,
))

register_tool(ToolSpec(
    name="generate_cyclonedds_config",
    description="Generate optimized CycloneDDS XML configuration",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=GenerateDdsConfigParams,
    handler=_generate_cyclonedds_config,
))

register_tool(ToolSpec(
    name="generate_fastdds_config",
    description="Generate optimized Fast DDS XML configuration",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=GenerateDdsConfigParams,
    handler=_generate_fastdds_config,
))

register_tool(ToolSpec(
    name="generate_zenoh_advice",
    description="Generate Zenoh adoption guidance for this hardware",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=type('GenerateZenohParams', (BaseModel,), {}),
    handler=_generate_zenoh_advice,
))

register_tool(ToolSpec(
    name="generate_sysctl_config",
    description="Generate optimized sysctl kernel parameters for ROS 2",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=type('GenerateSysctlParams', (BaseModel,), {}),
    handler=_generate_sysctl_config,
))

register_tool(ToolSpec(
    name="generate_build_flags",
    description="Generate Arm-optimized compiler build flags for ROS 2",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=type('GenerateBuildFlagsParams', (BaseModel,), {}),
    handler=_generate_build_flags,
))

register_tool(ToolSpec(
    name="generate_install_script",
    description="Generate ROS 2 installation script for assessed tier",
    category="tune",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=GenerateInstallScriptParams,
    handler=_generate_install_script,
))

register_tool(ToolSpec(
    name="generate_all_configs",
    description="Generate all 6 config artifacts (DDS, sysctl, build, install) to disk",
    category="tune",
    blast_radius=BlastRadius.MEDIUM,
    timeout_s=30,
    parameters=GenerateAllConfigsParams,
    handler=_generate_all_configs,
))

register_tool(ToolSpec(
    name="detect_serial_ports",
    description="Detect available hardware serial/UART ports and inspect getty/console conflicts",
    category="discover",
    blast_radius=BlastRadius.NONE,
    timeout_s=5,
    parameters=type('DetectSerialParams', (BaseModel,), {}),
    handler=_detect_serial_ports,
))

register_tool(ToolSpec(
    name="configure_micro_ros_uart",
    description="Generate scripts and systemd unit to dedicate hardware serial /dev/ttyAMA0 to micro-ROS",
    category="tune",
    blast_radius=BlastRadius.LOW,
    timeout_s=5,
    parameters=ConfigureMicroRosParams,
    handler=_configure_micro_ros_uart,
))

register_tool(ToolSpec(
    name="project_list_files",
    description="Remote project management: list workspace directory structure and files",
    category="project",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=ProjectListFilesParams,
    handler=_project_list_files,
))

register_tool(ToolSpec(
    name="project_read_file",
    description="Remote project management: read contents of a file in the workspace",
    category="project",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=ProjectReadFileParams,
    handler=_project_read_file,
))

register_tool(ToolSpec(
    name="project_write_file",
    description="Remote project management: write or edit a file in the workspace with automatic backup",
    category="project",
    blast_radius=BlastRadius.MEDIUM,
    timeout_s=10,
    parameters=ProjectWriteFileParams,
    handler=_project_write_file,
))

register_tool(ToolSpec(
    name="project_git_status",
    description="Remote project management: inspect git branch and modified files status",
    category="project",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=ProjectGitStatusParams,
    handler=_project_git_status,
))

register_tool(ToolSpec(
    name="project_git_diff",
    description="Remote project management: view git diff of workspace or specific file",
    category="project",
    blast_radius=BlastRadius.NONE,
    timeout_s=10,
    parameters=ProjectGitDiffParams,
    handler=_project_git_diff,
))

register_tool(ToolSpec(
    name="project_pip_install",
    description="Remote project management: install Python dependencies via pip safely",
    category="project",
    blast_radius=BlastRadius.MEDIUM,
    timeout_s=60,
    parameters=ProjectPipInstallParams,
    handler=_project_pip_install,
))

register_tool(ToolSpec(
    name="project_run_command",
    description="Remote project management: execute build or test commands (colcon build, pytest) with timeout",
    category="project",
    blast_radius=BlastRadius.MEDIUM,
    timeout_s=300,
    parameters=ProjectRunCommandParams,
    handler=_project_run_command,
))