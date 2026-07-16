"""CLI commands for Argus."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from argus.core import (
    detect_arm_soc, assess_hardware, stress_cpu, stress_memory,
    measure_thermal, sample_ram, generate_all_configs,
)
from argus.core.models import Tier
from argus.safety import create_gatekeeper


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="argus")
def cli():
    """Argus - Arm-native ROS 2 diagnostic & optimization platform."""
    pass


@cli.command()
@click.option("--detailed", is_flag=True, help="Show extended hardware info")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def diagnose(detailed: bool, output_json: bool):
    """Profile Arm SoC and print hardware capabilities."""
    profile = detect_arm_soc(detailed=detailed)
    
    if output_json:
        console.print(JSON(profile.model_dump()))
        return
    
    table = Table(title=f"Hardware Profile: {profile.model}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("OS / Arch", f"{profile.os} / {profile.arch}")
    table.add_row("Model", profile.model)
    table.add_row("Cores", f"{profile.total_cores} (P:{profile.p_cores} E:{profile.e_cores})")
    table.add_row("RAM", f"{profile.total_ram_gb:.1f} GB total, {profile.available_ram_gb:.1f} GB available")
    table.add_row("Cache Line", f"{profile.cache_line_size} bytes")
    table.add_row("L1d Cache", profile.l1d_cache or "N/A")
    table.add_row("L2 Cache", profile.l2_cache or "N/A")
    table.add_row("L3 Cache", profile.l3_cache or "N/A")
    table.add_row("NEON", "✓" if profile.neon else "✗")
    table.add_row("SVE", "✓" if profile.sve else "✗")
    table.add_row("LSE", "✓" if profile.lse else "✗")
    table.add_row("Compiler Target", profile.compiler_target)
    table.add_row("Fingerprint", profile.fingerprint[:16] + "...")
    table.add_row("PREEMPT_RT", "Yes" if profile.has_preempt_rt else "No")
    
    console.print(table)


@cli.command()
@click.option("--duration", default=10, help="Test duration in seconds")
@click.option("--workers", default=None, type=int, help="Number of workers (default: CPU count)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def stress(duration: int, workers: Optional[int], output_json: bool):
    """Run CPU and memory stress tests."""
    console.print(f"[bold]Running stress tests for {duration}s...[/bold]")
    
    cpu_result = stress_cpu(duration_s=duration, workers=workers)
    mem_result = stress_memory(duration_s=duration)
    
    if output_json:
        console.print(JSON({"cpu": cpu_result, "memory": mem_result}))
        return
    
    # CPU results
    cpu_table = Table(title="CPU Stress")
    cpu_table.add_column("Metric", style="cyan")
    cpu_table.add_column("Value", style="green")
    cpu_table.add_row("Bogo-ops/sec", f"{cpu_result.get('bogo_ops_s', 0):,.0f}" if cpu_result.get('bogo_ops_s') else "N/A")
    cpu_table.add_row("Avg Temp", f"{cpu_result.get('avg_temp_c', 0):.1f}°C" if cpu_result.get('avg_temp_c') else "N/A")
    cpu_table.add_row("Peak Temp", f"{cpu_result.get('peak_temp_c', 0):.1f}°C" if cpu_result.get('peak_temp_c') else "N/A")
    cpu_table.add_row("Workers", str(cpu_result.get('workers', 'N/A')))
    console.print(cpu_table)
    
    # Memory results
    mem_table = Table(title="Memory Bandwidth (STREAM-like)")
    mem_table.add_column("Operation", style="cyan")
    mem_table.add_column("MB/s", style="green")
    for op in ["copy", "scale", "add", "triad"]:
        val = mem_result.get(f"{op}_mbps")
        mem_table.add_row(op.capitalize(), f"{val:,.0f}" if val else "N/A")
    console.print(mem_table)


@cli.command()
@click.option("--pid", default=None, type=int, help="Process ID to sample (default: system-wide)")
@click.option("--interval", default=1.0, type=float, help="Sampling interval in seconds")
@click.option("--duration", default=10, type=int, help="Number of samples")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def ram(pid: Optional[int], interval: float, duration: int, output_json: bool):
    """Sample RAM usage over time."""
    result = sample_ram(pid=pid, interval_s=interval, duration_s=duration)
    
    if output_json:
        console.print(JSON(result))
        return
    
    table = Table(title=f"RAM Sampling ({'PID ' + str(pid) if pid else 'System-wide'})")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Avg RSS", f"{result['avg_rss_kb']:.0f} KB")
    table.add_row("Peak RSS", f"{result['peak_rss_kb']:.0f} KB")
    table.add_row("System Total", f"{result['system_total_kb'] / 1024 / 1024:.1f} GB")
    table.add_row("System Available", f"{result['system_available_kb'] / 1024 / 1024:.1f} GB")
    console.print(table)


@cli.command()
@click.option("--output-dir", default="./configs", help="Output directory for configs")
@click.option("--report", is_flag=True, help="Generate pre/post assessment report")
@click.option("--no-configs", is_flag=True, help="Skip config generation (assessment only)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def assess(output_dir: str, report: bool, no_configs: bool, output_json: bool):
    """Full hardware assessment with ROS 2 tier scoring and config generation."""
    
    # Pre-assessment report
    if report:
        console.print("[dim]Generating pre-assessment report...[/dim]")
        # TODO: integrate with state/report.py
    
    # Run assessment
    profile = detect_arm_soc()
    console.print(f"[bold]Detected:[/bold] {profile.model} ({profile.total_cores} cores, {profile.total_ram_gb:.1f} GB RAM)")
    
    # Run stress for thermal data
    console.print("[dim]Running quick stress test for thermal data...[/dim]")
    stress_result = stress_cpu(duration_s=5)
    mem_result = stress_memory(duration_s=5)
    
    # Combine stress results for assessment
    from argus.core.models import StressResults
    combined_stress = StressResults(
        cpu_bogo_ops_s=stress_result.get("bogo_ops_s"),
        memory_copy_mbps=mem_result.get("memory_copy_mbps"),
        memory_scale_mbps=mem_result.get("memory_scale_mbps"),
        memory_add_mbps=mem_result.get("memory_add_mbps"),
        memory_triad_mbps=mem_result.get("memory_triad_mbps"),
        peak_temp_c=stress_result.get("peak_temp_c"),
        avg_temp_c=stress_result.get("avg_temp_c"),
        thermal_throttled=stress_result.get("thermal_throttled"),
    )
    
    scorecard = assess_hardware(profile, combined_stress)
    
    # Display scorecard
    tier_colors = {
        Tier.ROS_DESKTOP: "green",
        Tier.ROS_BASE_FULL: "blue",
        Tier.ROS_BASE: "yellow",
        Tier.MICRO_ROS: "orange",
        Tier.ZENOH_PICO: "red",
    }
    color = tier_colors.get(scorecard.tier, "white")
    
    score_table = Table(title="ROS 2 Assessment Scorecard")
    score_table.add_column("Metric", style="cyan")
    score_table.add_column("Score", style="green")
    score_table.add_row("Total Score", f"[{color}]{scorecard.score}/100[/{color}]")
    score_table.add_row("Tier", f"[{color}]{scorecard.tier.value}[/{color}]")
    score_table.add_row("Recommended RMW", scorecard.recommended_rmw.value)
    score_table.add_row("DDS Profile", scorecard.dds_profile.value)
    for k, v in scorecard.breakdown.items():
        score_table.add_row(f"  {k.capitalize()}", f"{v:.1f}")
    console.print(score_table)
    
    console.print(f"\n[bold]Rationale:[/bold] {scorecard.rationale}")
    
    if scorecard.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in scorecard.warnings:
            console.print(f"  ⚠ {w}")
    
    # Generate configs
    if not no_configs:
        console.print(f"\n[dim]Generating configs to {output_dir}...[/dim]")
        gatekeeper = create_gatekeeper(auto_approve=False)
        # Check permission for generate_all_configs (MEDIUM)
        # In real implementation, this would prompt
        
        artifact = generate_all_configs(profile, scorecard, output_dir)
        
        config_table = Table(title="Generated Configs")
        config_table.add_column("File", style="cyan")
        config_table.add_column("Size", style="green")
        for f in artifact.files:
            config_table.add_row(f.name, f"{f.size_bytes / 1024:.1f} KB")
        console.print(config_table)
        
        console.print(f"\n[green]✓[/green] Configs written to {artifact.soc_model}/")
    
    if output_json:
        result = {"scorecard": scorecard.model_dump()}
        if not no_configs:
            result["configs"] = [f.name for f in artifact.files]
        console.print(JSON(result))


@cli.command()
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio")
@click.option("--port", default=8765, help="HTTP port")
@click.option("--host", default="127.0.0.1", help="HTTP host")
def mcp(transport: str, port: int, host: str):
    """Start MCP server for AI agent integration."""
    from argus.mcp.server import run_server
    run_server(transport=transport, host=host, port=port)


@cli.command()
def version():
    """Print version info."""
    from argus import __version__
    console.print(f"Argus v{__version__}")


if __name__ == "__main__":
    cli()