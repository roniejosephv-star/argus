"""Core module exports."""

from argus.core.models import (
    HardwareProfile,
    StressResults,
    Scorecard,
    ConfigFile,
    ConfigArtifact,
    Tier,
    RMW,
    DDSProfile,
    BlastRadius,
    Report,
    ReportDiff,
    Lesson,
)

from argus.core.profiler import detect_arm_soc, get_cache_line_size, get_compiler_target, detect_os
from argus.core.assess import assess_hardware
from argus.core.optimizer import (
    generate_cyclonedds_xml,
    generate_fastdds_xml,
    generate_zenoh_advice,
    generate_sysctl_config,
    generate_build_flags,
    generate_install_script,
    generate_all_configs,
)
from argus.core.stresser import stress_cpu, stress_memory, measure_thermal, stress_thermal
from argus.core.ram_sampler import sample_ram
from argus.core.peripherals import detect_serial_ports, configure_micro_ros_uart
from argus.core.project_tools import (
    project_list_files,
    project_read_file,
    project_write_file,
    project_git_status,
    project_git_diff,
    project_pip_install,
    project_run_command,
    ProjectListFilesParams,
    ProjectReadFileParams,
    ProjectWriteFileParams,
    ProjectGitStatusParams,
    ProjectGitDiffParams,
    ProjectPipInstallParams,
    ProjectRunCommandParams,
)

__all__ = [
    # Models
    "HardwareProfile",
    "StressResults",
    "Scorecard",
    "ConfigFile",
    "ConfigArtifact",
    "Tier",
    "RMW",
    "DDSProfile",
    "BlastRadius",
    "Report",
    "ReportDiff",
    "Lesson",
    # Profiler
    "detect_arm_soc",
    "get_cache_line_size",
    "get_compiler_target",
    "detect_os",
    # Assessment
    "assess_hardware",
    # Optimizer
    "generate_cyclonedds_xml",
    "generate_fastdds_xml",
    "generate_zenoh_advice",
    "generate_sysctl_config",
    "generate_build_flags",
    "generate_install_script",
    "generate_all_configs",
    # Stresser
    "stress_cpu",
    "stress_memory",
    "measure_thermal",
    "stress_thermal",
    # RAM Sampler
    "sample_ram",
    # Peripherals
    "detect_serial_ports",
    "configure_micro_ros_uart",
    # Project Tools
    "project_list_files",
    "project_read_file",
    "project_write_file",
    "project_git_status",
    "project_git_diff",
    "project_pip_install",
    "project_run_command",
    "ProjectListFilesParams",
    "ProjectReadFileParams",
    "ProjectWriteFileParams",
    "ProjectGitStatusParams",
    "ProjectGitDiffParams",
    "ProjectPipInstallParams",
    "ProjectRunCommandParams",
]