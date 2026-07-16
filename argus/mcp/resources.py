"""MCP resource URIs and prompt templates."""

from __future__ import annotations

from typing import Any
import json

from argus.core import detect_arm_soc, assess_hardware, generate_cyclonedds_xml
from argus.state.report_store import latest_report, list_reports


# Resource URI handlers
RESOURCE_HANDLERS = {
    "argus://system/info": lambda: json.dumps(detect_arm_soc().model_dump(), indent=2),
    "argus://system/cpu": lambda: json.dumps({
        "model": detect_arm_soc().model,
        "cores": detect_arm_soc().total_cores,
        "p_cores": detect_arm_soc().p_cores,
        "e_cores": detect_arm_soc().e_cores,
        "cache_line": detect_arm_soc().cache_line_size,
        "isa": ["NEON"] if detect_arm_soc().neon else [] + 
               (["SVE"] if detect_arm_soc().sve else []) +
               (["SVE2"] if detect_arm_soc().sve2 else []) +
               (["LSE"] if detect_arm_soc().lse else []),
    }, indent=2),
    "argus://system/memory": lambda: json.dumps({
        "total_gb": detect_arm_soc().total_ram_gb,
        "available_gb": detect_arm_soc().available_ram_gb,
    }, indent=2),
    "argus://sensors/temperature": lambda: json.dumps({
        "temp_c": None,  # Would call measure_thermal()
        "sensors": [],
    }, indent=2),
    "argus://stress/latest": lambda: json.dumps({"note": "Run stress test first"}, indent=2),
    "argus://configs/cyclonedds": lambda: detect_arm_soc() and generate_cyclonedds_xml(detect_arm_soc(), "balanced"),
    "argus://configs/fastdds": lambda: json.dumps({"note": "Run generate_fastdds_config first"}, indent=2),
    "argus://configs/sysctl": lambda: json.dumps({"note": "Run generate_sysctl_config first"}, indent=2),
    "argus://scorecard/latest": lambda: json.dumps(assess_hardware(detect_arm_soc()).model_dump(), indent=2),
    "argus://reports/latest": lambda: json.dumps(latest_report(detect_arm_soc().fingerprint).model_dump() if latest_report(detect_arm_soc().fingerprint) else {}, indent=2),
}


# Prompt templates
PROMPTS = {
    "tune-ros2": """You are Argus, an Arm-native ROS 2 optimization specialist.
Perform the complete optimization workflow:
1. Profile the Arm hardware (detect_arm_soc)
2. Assess ROS 2 suitability (assess_hardware)
3. Generate optimized configurations (generate_all_configs)
4. Explain the recommendations and their hardware-specific rationale

Provide actionable guidance for deploying ROS 2 on this specific Arm platform.""",
    
    "profile-arm": """Profile this Arm SoC and explain the results in detail.
Cover: CPU architecture (big.LITTLE topology), cache hierarchy, ISA features,
memory subsystem, thermal characteristics, and compiler target selection.
Explain what each finding means for ROS 2 performance.""",
    
    "optimize-dds": """Analyze the hardware and generate optimal DDS configuration.
Consider: RAM capacity for buffer sizing, core count for participant indexing,
cache line size for fragment alignment, and workload profile (latency vs throughput).
Generate both CycloneDDS and Fast DDS configs with explanations.""",
    
    "debug-thermal": """Run thermal stress test and analyze throttling risk.
Execute combined CPU+memory stress (stress_thermal), monitor temperature curves,
identify throttling thresholds, and recommend cooling/mitigation strategies.
Correlate thermal behavior with ROS 2 real-time performance requirements.""",
}


def get_resource(uri: str) -> str | None:
    """Get resource content by URI."""
    handler = RESOURCE_HANDLERS.get(uri)
    if handler:
        try:
            return handler()
        except Exception as e:
            return f"Error: {e}"
    return None


def get_prompt(name: str) -> str | None:
    """Get prompt template by name."""
    return PROMPTS.get(name)