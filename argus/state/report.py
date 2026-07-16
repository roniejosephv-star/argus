"""Report data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class HardwareSnapshot(BaseModel):
    model: str
    p_cores: int
    e_cores: int
    total_ram_gb: float
    available_ram_gb: float
    cache_line_size: int
    compiler_target: str
    fingerprint: str


class OSSnapshot(BaseModel):
    os: str
    arch: str
    kernel_version: str
    distro: str | None = None
    has_preempt_rt: bool = False
    uptime_hours: float
    kernel_params: dict[str, str] = {}


class ROS2Snapshot(BaseModel):
    installed: bool = False
    distro: str | None = None
    rmw: str | None = None
    packages: list[str] = []
    workspace_path: str | None = None
    active_nodes: list[str] = []
    active_topics: list[str] = []
    domain_id: int | None = None


class ConfigSnapshot(BaseModel):
    has_cyclonedds_xml: bool = False
    cyclonedds_xml_path: str | None = None
    has_fastdds_xml: bool = False
    fastdds_xml_path: str | None = None
    has_zenoh_config: bool = False
    zenoh_config_path: str | None = None
    has_sysctl_ros_conf: bool = False
    rmw_implementation: str | None = None
    ros_domain_id: int | None = None


class PerformanceSnapshot(BaseModel):
    cpu_bogo_ops_s: float | None = None
    memory_copy_mbps: float | None = None
    memory_scale_mbps: float | None = None
    memory_add_mbps: float | None = None
    memory_triad_mbps: float | None = None
    peak_temp_c: float | None = None
    thermal_throttled: bool | None = None
    ram_used_kb: int | None = None
    ram_available_kb: int | None = None
    swap_used_kb: int | None = None


class DiskSnapshot(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    top_processes_ram: list[dict] = []
    top_processes_cpu: list[dict] = []


class Report(BaseModel):
    report_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.now)
    argus_version: str = "0.1.0"
    reason: str = "manual"
    metadata: dict = {}

    hardware: HardwareSnapshot
    os: OSSnapshot
    ros2: ROS2Snapshot
    configs: ConfigSnapshot
    performance: PerformanceSnapshot | None = None
    disk: DiskSnapshot | None = None
    scorecard: Scorecard | None = None
    lessons: list["Lesson"] = []
    pre_report_id: str | None = None
    diff: ReportDiff | None = None


class ReportDiff(BaseModel):
    report_before_id: str
    report_after_id: str
    timestamp_before: datetime
    timestamp_after: datetime
    fingerprint: str

    hardware_changed: bool = False
    os_changed: bool = False
    ros2_changed: bool = False
    configs_changed: bool = False
    performance_changed: bool = False

    configs_added: list[str] = []
    configs_removed: list[str] = []
    configs_modified: list[dict] = []
    ros2_packages_added: list[str] = []
    ros2_packages_removed: list[str] = []

    cpu_bogo_ops_delta_pct: float | None = None
    memory_bandwidth_delta_pct: float | None = None
    ram_usage_delta_kb: int | None = None
    temp_delta_c: float | None = None

    summary: str


class Lesson(BaseModel):
    lesson_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    fingerprint: str
    hardware_model: str
    description: str
    category: Literal["dds", "sysctl", "build_flags", "rmw", "tier", "general"]
    benefit: str
    tradeoff: str
    confidence: float = Field(ge=0, le=100, default=50)
    tags: list[str] = []
    diff_summary: str = ""