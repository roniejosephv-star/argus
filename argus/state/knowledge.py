"""Knowledge extraction from pre/post diffs."""

from __future__ import annotations

from typing import Any
from argus.state.report_store import Report, ReportDiff, Lesson


def extract_lessons(pre: Report, post: Report, diff: ReportDiff) -> list[Lesson]:
    """Extract learned lessons from pre/post diff."""
    lessons = []
    
    if not diff.configs_added and not diff.configs_modified:
        return lessons
    
    # DDS config changes
    if diff.configs_modified:
        for change in diff.configs_modified:
            if "FragmentSize" in change.get("param", ""):
                lessons.append(Lesson(
                    fingerprint=pre.hardware.fingerprint,
                    hardware_model=pre.hardware.model,
                    description=f"CycloneDDS FragmentSize {change.get('old')}→{change.get('new')} for {pre.hardware.model} cache line alignment",
                    category="dds",
                    benefit="Reduced DDS latency via cache-line alignment",
                    tradeoff="Slightly higher memory per fragment",
                    confidence=85,
                    tags=["cyclonedds", "cache-line", "latency"],
                    diff_summary=f"FragmentSize: {change.get('old')}→{change.get('new')}",
                ))
            elif "MaxMessageSize" in change.get("param", ""):
                lessons.append(Lesson(
                    fingerprint=pre.hardware.fingerprint,
                    hardware_model=pre.hardware.model,
                    description=f"MaxMessageSize {change.get('old')}→{change.get('new')} scaled to {pre.hardware.total_ram_gb:.1f}GB RAM",
                    category="dds",
                    benefit="Optimized for available memory",
                    tradeoff="Larger messages use more per-participant memory",
                    confidence=80,
                    tags=["cyclonedds", "memory-scaling"],
                    diff_summary=f"MaxMessageSize: {change.get('old')}→{change.get('new')}",
                ))
    
    # Sysctl changes
    if diff.configs_modified:
        for change in diff.configs_modified:
            if change.get("param") in ["net.core.rmem_max", "net.core.wmem_max"]:
                lessons.append(Lesson(
                    fingerprint=pre.hardware.fingerprint,
                    hardware_model=pre.hardware.model,
                    description=f"Socket buffer {change.get('old')}→{change.get('new')} for {pre.hardware.model} RAM",
                    category="sysctl",
                    benefit="Higher network throughput for DDS",
                    tradeoff="Increased kernel memory reservation",
                    confidence=75,
                    tags=["sysctl", "network", "buffer"],
                    diff_summary=f"{change.get('param')}: {change.get('old')}→{change.get('new')}",
                ))
    
    # Tier changes
    if pre.scorecard and post.scorecard and pre.scorecard.tier != post.scorecard.tier:
        lessons.append(Lesson(
            fingerprint=pre.hardware.fingerprint,
            hardware_model=pre.hardware.model,
            description=f"Tier changed {pre.scorecard.tier.value}→{post.scorecard.tier.value} after optimization",
            category="tier",
            benefit="Better ROS 2 variant selection",
            tradeoff="May require different RMW/DDS profile",
            confidence=90,
            tags=["tier", "optimization-result"],
            diff_summary=f"Tier: {pre.scorecard.tier.value}→{post.scorecard.tier.value}",
        ))
    
    return lessons


def apply_learned_knowledge(profile_fingerprint: str, recommendations: dict) -> dict:
    """Augment config recommendations with past lessons."""
    # Placeholder - would query lessons from store
    # For now, return recommendations unchanged
    return recommendations