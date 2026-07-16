"""Hardware assessment and ROS 2 tier scoring."""

from __future__ import annotations

from argus.core.models import HardwareProfile, Scorecard, StressResults, Tier, RMW, DDSProfile


# Tier thresholds (RAM-primary, compute-secondary)
TIER_THRESHOLDS = [
    (Tier.ROS_DESKTOP,     8.0, 8, 80),  # min_ram_gb, min_cores, min_score
    (Tier.ROS_BASE_FULL,   4.0, 4, 60),
    (Tier.ROS_BASE,        2.0, 2, 40),
    (Tier.MICRO_ROS,       0.512, 1, 20),
    (Tier.ZENOH_PICO,      0.128, 1, 0),
]


def assess_hardware(profile: HardwareProfile, stress: StressResults | None = None) -> Scorecard:
    """Generate ROS 2 efficiency scorecard with tier recommendation."""
    
    # Score breakdown (100 points max)
    ram_score = _score_ram(profile.total_ram_gb)
    compute_score = _score_compute(profile.total_cores, profile.neon, profile.sve, profile.sve2, profile.lse)
    isa_score = _score_isa(profile.neon, profile.sve, profile.sve2, profile.lse)
    cache_score = _score_cache(profile.l2_cache, profile.l3_cache)
    thermal_score = _score_thermal(stress)
    rt_score = _score_rt(profile.has_preempt_rt, profile.total_cores)
    
    breakdown = {
        "ram": ram_score,
        "compute": compute_score,
        "isa": isa_score,
        "cache": cache_score,
        "thermal": thermal_score,
        "rt": rt_score,
    }
    
    total_score = sum(breakdown.values())
    total_score = min(100, max(0, int(round(total_score))))
    
    # Determine tier from thresholds
    tier = Tier.ZENOH_PICO
    for t, min_ram, min_cores, min_score in TIER_THRESHOLDS:
        if profile.total_ram_gb >= min_ram and profile.total_cores >= min_cores and total_score >= min_score:
            tier = t
            break
    
    # RMW recommendation
    recommended_rmw = _recommend_rmw(profile, tier)
    
    # DDS profile recommendation
    dds_profile = _recommend_dds_profile(profile, tier)
    
    # ROS 2 distro recommendation
    ros2_distro = _recommend_ros2_distro(profile)

    # Rationale
    rationale = _generate_rationale(profile, breakdown, tier, total_score)
    
    # Warnings
    warnings = _generate_warnings(profile, stress)
    
    return Scorecard(
        tier=tier,
        score=total_score,
        breakdown=breakdown,
        rationale=rationale,
        recommended_rmw=recommended_rmw,
        dds_profile=dds_profile,
        ros2_distro=ros2_distro,
        warnings=warnings,
    )


def _recommend_ros2_distro(profile: HardwareProfile) -> str:
    """Recommend ROS 2 distro based on OS and Ubuntu LTS version."""
    if profile.os_version:
        v = str(profile.os_version)
        if "24.04" in v:
            return "jazzy"
        elif "22.04" in v:
            return "humble"
        elif "20.04" in v:
            return "foxy"
    return "jazzy"


def _score_ram(ram_gb: float) -> float:
    """RAM score: 0 at 128MB, 30 at 8GB, linear in between, capped at 30."""
    if ram_gb <= 0.128:
        return 0.0
    elif ram_gb >= 8.0:
        return 30.0
    # Linear interpolation: 0.128GB -> 0, 8GB -> 30
    return 30.0 * (ram_gb - 0.128) / (8.0 - 0.128)


def _score_compute(cores: int, neon: bool, sve: bool, sve2: bool, lse: bool) -> float:
    """Compute score: base from cores + ISA bonuses."""
    # Base from cores (max 15 at 8+ cores)
    core_score = min(15.0, cores * 1.875)  # 8 cores = 15
    
    # ISA bonuses (max 5 total)
    isa_bonus = 0.0
    if neon:
        isa_bonus += 2.0
    if sve:
        isa_bonus += 1.5
    if sve2:
        isa_bonus += 1.0
    if lse:
        isa_bonus += 1.5  # LSE is important for ROS 2 atomics
    
    return core_score + min(5.0, isa_bonus)


def _score_isa(neon: bool, sve: bool, sve2: bool, lse: bool) -> float:
    """ISA feature score (max 15)."""
    score = 0.0
    if neon:
        score += 5.0
    if sve:
        score += 5.0
    if sve2:
        score += 3.0
    if lse:
        score += 2.0
    return score


def _score_cache(l2: str | None, l3: str | None) -> float:
    """Cache score (max 10)."""
    score = 0.0
    if l2:
        try:
            size_mb = float(l2.replace("MB", "").replace("KB", "")) / 1024 if "KB" in l2 else float(l2.replace("MB", ""))
            if size_mb >= 4:
                score += 5.0
            elif size_mb >= 1:
                score += 3.0
            else:
                score += 1.0
        except Exception:
            score += 2.0
    if l3:
        score += 5.0
    return min(10.0, score)


def _score_thermal(stress: StressResults | None) -> float:
    """Thermal headroom score (max 10)."""
    if not stress or stress.peak_temp_c is None:
        return 5.0  # Unknown = median
    
    peak = stress.peak_temp_c
    if peak < 60:
        return 10.0
    elif peak < 70:
        return 8.0
    elif peak < 80:
        return 6.0
    elif peak < 85:
        return 4.0
    else:
        return 2.0


def _score_rt(has_preempt_rt: bool, cores: int) -> float:
    """Real-time capability score (max 15)."""
    if not has_preempt_rt:
        return 0.0
    # More cores = better isolation potential
    if cores >= 8:
        return 15.0
    elif cores >= 4:
        return 10.0
    else:
        return 5.0


def _recommend_rmw(profile: HardwareProfile, tier: Tier) -> RMW:
    """Recommend RMW based on hardware and tier."""
    # Low memory -> Zenoh
    if profile.total_ram_gb < 2.0:
        return RMW.ZENOH
    
    # RT kernel -> Fast DDS (better RT support)
    if profile.has_preempt_rt:
        return RMW.FASTDDS
    
    # Default: CycloneDDS (balanced, good performance on Arm)
    return RMW.CYCLONEDDS


def _recommend_dds_profile(profile: HardwareProfile, tier: Tier) -> DDSProfile:
    """Recommend DDS profile."""
    if tier in (Tier.MICRO_ROS, Tier.ZENOH_PICO):
        return DDSProfile.LOW_MEMORY
    elif profile.total_ram_gb >= 8.0 and profile.total_cores >= 8:
        return DDSProfile.HIGH_THROUGHPUT
    elif profile.has_preempt_rt:
        return DDSProfile.LOW_LATENCY
    return DDSProfile.BALANCED


def _generate_rationale(profile: HardwareProfile, breakdown: dict, tier: Tier, score: int) -> str:
    """Generate human-readable rationale."""
    parts = []
    parts.append(f"Total score: {score}/100 → Tier: {tier.value}")
    parts.append(f"Profile: {tier.value.replace('-', ' ').title()}")
    parts.append(f"RAM: {profile.total_ram_gb:.1f} GB ({breakdown['ram']:.0f}/30 pts)")
    parts.append(f"Compute: {profile.total_cores} cores ({breakdown['compute']:.0f}/20 pts)")
    parts.append(f"ISA: {'NEON ' if profile.neon else ''}{'SVE ' if profile.sve else ''}{'SVE2 ' if profile.sve2 else ''}{'LSE ' if profile.lse else ''}({breakdown['isa']:.0f}/15 pts)")
    
    if profile.has_preempt_rt:
        parts.append("PREEMPT_RT kernel detected (+RT capability)")
    
    warnings = []
    if profile.total_ram_gb < 2.0:
        warnings.append("Low RAM (<2GB) limits ROS 2 to minimal configurations")
    if not profile.neon:
        warnings.append("NEON not detected - SIMD optimizations unavailable")
    if profile.cache_line_size not in (64, 128):
        warnings.append(f"Unusual cache line size: {profile.cache_line_size}")
    
    if warnings:
        parts.append("Warnings: " + "; ".join(warnings))
    
    return " | ".join(parts)


def _generate_warnings(profile: HardwareProfile, stress: StressResults | None) -> list[str]:
    warnings = []
    if profile.total_ram_gb < 1.0:
        warnings.append("RAM < 1GB: Only micro-ROS or Zenoh Pico viable")
    elif profile.total_ram_gb < 2.0:
        warnings.append("RAM < 2GB: Limited to ros-base tier")
    if not profile.neon:
        warnings.append("NEON SIMD not available - significant performance impact")
    if stress and stress.thermal_throttled:
        warnings.append("Thermal throttling detected during stress test")
    if not profile.has_preempt_rt and profile.total_cores >= 4:
        warnings.append("Consider PREEMPT_RT kernel for real-time workloads")
    return warnings