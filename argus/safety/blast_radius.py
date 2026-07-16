"""Blast radius classification for tools."""

from enum import Enum


class BlastRadius(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


APPROVAL_POLICY = {
    BlastRadius.NONE: "auto",
    BlastRadius.LOW: "auto",
    BlastRadius.MEDIUM: "ask",
    BlastRadius.HIGH: "ask",
    BlastRadius.CRITICAL: "deny",
}

TOOL_CLASSIFICATIONS: dict[str, BlastRadius] = {
    # NONE - pure read/compute
    "detect_arm_soc": BlastRadius.NONE,
    "detect_os": BlastRadius.NONE,
    "assess_hardware": BlastRadius.NONE,
    "generate_cyclonedds_config": BlastRadius.NONE,
    "generate_fastdds_config": BlastRadius.NONE,
    "generate_zenoh_advice": BlastRadius.NONE,
    "generate_sysctl_config": BlastRadius.NONE,
    "generate_build_flags": BlastRadius.NONE,
    "generate_install_script": BlastRadius.NONE,
    "measure_thermal": BlastRadius.NONE,
    "measure_ram": BlastRadius.NONE,
    "generate_report": BlastRadius.NONE,
    "diff_reports": BlastRadius.NONE,
    "list_reports": BlastRadius.NONE,
    "get_lessons": BlastRadius.NONE,
    "detect_serial_ports": BlastRadius.NONE,
    "project_list_files": BlastRadius.NONE,
    "project_read_file": BlastRadius.NONE,
    "project_git_status": BlastRadius.NONE,
    "project_git_diff": BlastRadius.NONE,
    
    # LOW - consumes resources or generates scripts/advice
    "stress_cpu": BlastRadius.LOW,
    "stress_memory": BlastRadius.LOW,
    "configure_micro_ros_uart": BlastRadius.LOW,
    
    # MEDIUM - writes files or runs scoped workspace build commands
    "generate_all_configs": BlastRadius.MEDIUM,
    "write_config": BlastRadius.MEDIUM,
    "scaffold_ros2_package": BlastRadius.MEDIUM,
    "project_write_file": BlastRadius.MEDIUM,
    "project_pip_install": BlastRadius.MEDIUM,
    "project_run_command": BlastRadius.MEDIUM,
    
    # HIGH - shell execution, system modification
    "run_command": BlastRadius.HIGH,
    "colcon_build": BlastRadius.HIGH,
    "apply_sysctl": BlastRadius.HIGH,
    "git_commit": BlastRadius.HIGH,
}