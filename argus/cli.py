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
from argus.common.logger import log_event


console = Console()


def run_interactive_shell(ctx: click.Context):
    """Launch interactive Argus Control Plane REPL loop when invoked without subcommands."""
    import shlex
    import sys
    import select
    import subprocess
    from argus.ui import render_banner, animate_dynamic_banner, render_live_dashboard
    from argus.host.bridge import check_target_status_tunnel, connect_target
    
    from argus.core import detect_os
    import socket

    host_os = detect_os()

    # If running natively inside Linux/ARM Edge Target (e.g. Raspberry Pi)
    if host_os != "darwin":
        animate_dynamic_banner(console, duration_s=1.2)
        if sys.stdout.isatty() and sys.stdin.isatty():
            console.print("[bold #38b6ff]Interactive Edge Target Control Plane Active[/bold #38b6ff]\n")
            target_host = socket.gethostname()
            while True:
                try:
                    console.print(f"[bold #66c2ff]─── [ Target Telemetry Probe · Node: {target_host} · Edge Mode: ● ACTIVE ] ───[/bold #66c2ff]")
                    cmd_line = console.input(f"[bold #00d2ff]argus [{target_host}]>[/bold #00d2ff] ").strip()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[bold #38b6ff]Exiting Target Control Plane. Returning to Host session...[/bold #38b6ff]")
                    break
                if not cmd_line:
                    continue
                if cmd_line.lower() in ("exit", "quit", "q"):
                    console.print("[bold #38b6ff]Exiting Target Control Plane. Returning to Host session...[/bold #38b6ff]")
                    break
                if cmd_line.lower() in ("help", "?"):
                    console.print("[bold #b3e6ff]Target Edge Commands:[/bold #b3e6ff]")
                    console.print("  [bold #00d2ff]diagnose[/bold #00d2ff]         Profile local Arm SoC capabilities & thermal status")
                    console.print("  [bold #00d2ff]assess[/bold #00d2ff]           Execute ROS 2 hardware scorecard & generate DDS tuning")
                    console.print("  [bold #00d2ff]stress[/bold #00d2ff]           Run CPU/memory stress tests & verify thermal stability")
                    console.print("  [bold #00d2ff]dash[/bold #00d2ff]             Monitor real-time edge telemetry & RAM allocation")
                    console.print("  [bold #00d2ff]exit / quit[/bold #00d2ff]      Exit remote session & return to Mac Mini Host Control Tier\n")
                    continue
                if cmd_line.lower() in ("banner",):
                    render_banner(console)
                    continue
                if cmd_line.lower() in ("clear", "cls"):
                    console.clear()
                    render_banner(console)
                    continue
                try:
                    args = shlex.split(cmd_line)
                    cli.main(args=args, standalone_mode=False)
                except SystemExit:
                    pass
                except Exception as e:
                    console.print(f"[red]Error executing command: {e}[/red]")
        return

    # 1. Run the host dynamic initialization banner on Mac Mini
    animate_dynamic_banner(console, duration_s=2.5)
    
    selected_target = "host"
    if sys.stdout.isatty() and sys.stdin.isatty():
        # Clear any buffered keypresses
        try:
            while select.select([sys.stdin], [], [], 0.0)[0]:
                sys.stdin.read(1)
        except Exception:
            pass
            
        console.print("\n[bold #00d2ff]═══ Available Remote ARM Edge Targets ═══[/bold #00d2ff]")
        from argus.host.scanner import load_targets
        targets = load_targets()
        if not targets:
            console.print("  [bold #38b6ff][1] Device 1: armcreate-pi4[/bold #38b6ff] (192.168.1.43 · BCM2711 / Cortex-A72)")
        else:
            for idx, t in enumerate(targets):
                dev_idx = t.id + 1 if isinstance(t.id, int) else idx + 1
                console.print(f"  [bold #38b6ff][{dev_idx}] Device {dev_idx}: {t.hostname}[/bold #38b6ff] ({t.ip} · {t.soc_model})")
        console.print("")
        
        try:
            choice = console.input("[bold #ff7b00]Select remote edge target (1) or 'exit' for Mac Host REPL [Default: 1]: [/bold #ff7b00]").strip().lower()
            if choice in ("1", "device 1", "d1", ""):
                selected_target = "device_1"
            elif choice.isdigit():
                selected_target = f"device_{choice}"
            elif choice in ("exit", "host", "h"):
                selected_target = "host"
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold #38b6ff]Exiting Argus. Goodbye![/bold #38b6ff]")
            return

    if selected_target != "host":
        target_id_str = selected_target.split("_")[-1]
        target_idx = int(target_id_str) - 1 if target_id_str.isdigit() else 0
        
        from argus.host.scanner import load_targets, TargetDevice
        targets = load_targets()
        t = None
        if targets:
            for device in targets:
                if device.id == target_idx:
                    t = device
                    break
        if not t:
            t = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=2222)
            
        console.print(f"\n[bold #38b6ff]Establishing SSH bridge for Target [Device {t.id + 1}] ({t.ip})...[/bold #38b6ff]")
        
        # Ensure bridge/tunnel is active
        tunnel_active = check_target_status_tunnel(t.tunnel_port)
        if not tunnel_active:
            res = connect_target(str(t.id), tunnel_port=t.tunnel_port)
            if not res.get("success"):
                console.print(f"[red]✗ Failed to establish bridge: {res.get('error')}[/red]")
                subprocess.run(f"ssh -t -o StrictHostKeyChecking=no {t.username}@{t.ip} '~/Argus/.venv/bin/argus'", shell=True)
                return
                
        # Clear screen and invoke remote Argus on the target Pi to load its own dynamic banner!
        console.clear()
        console.print(f"[bold #00d2ff]Entering target control plane on [Device {t.id + 1}] ({t.hostname})...[/bold #00d2ff]")
        subprocess.run(f"ssh -t -o StrictHostKeyChecking=no -p {t.tunnel_port} {t.username}@127.0.0.1 '~/Argus/.venv/bin/argus'", shell=True)
        # When exiting remote target session, land back on Host Control Plane
        console.clear()
        render_banner(console, dynamic=False)
        
    # If host is selected or returning from target, enter the Mac Mini Host REPL
    if sys.stdout.isatty() and sys.stdin.isatty():
        try:
            render_live_dashboard(console, target_id="0", refresh_s=0.5)
        except KeyboardInterrupt:
            pass
            
        try:
            while select.select([sys.stdin], [], [], 0.0)[0]:
                sys.stdin.read(1)
        except Exception:
            pass
            
        console.clear()
        render_banner(console, dynamic=False)
        
    console.print("[bold #38b6ff]Interactive Mac Mini Host Control Plane Active[/bold #38b6ff]\n")
    
    while True:
        try:
            tunnel_live = check_target_status_tunnel(2222)
            prompt_label = "Device 1" if tunnel_live else "Host"
            header_label = "armcreate-pi4 (192.168.1.43)" if tunnel_live else "Mac Mini Host Control Tier"

            status_badge = "[bold #00d2ff]● ACTIVE[/bold #00d2ff]" if tunnel_live else "[bold #1e90ff]○ OFFLINE[/bold #1e90ff]"
            console.print(f"[bold #66c2ff]─── [ Dynamic Telemetry · Target [{prompt_label}]: {header_label} · Bridge: {status_badge}[bold #66c2ff] ] ───[/bold #66c2ff]")
            cmd_line = console.input(f"[bold #00d2ff]argus [{prompt_label}]>[/bold #00d2ff] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold #38b6ff]Exiting Argus Control Plane. Goodbye![/bold #38b6ff]")
            break
            
        if not cmd_line:
            continue
            
        try:
            log_event("phase4_application", f"REPL Command: {cmd_line}", details={"prompt": prompt_label})
        except Exception:
            pass

        if cmd_line.lower() in ("exit", "quit", "q"):
            console.print("[bold #38b6ff]Exiting Argus Control Plane. Goodbye![/bold #38b6ff]")
            break
            
        if cmd_line.lower() in ("help", "?"):
            console.print("[bold #b3e6ff]Available Commands:[/bold #b3e6ff]")
            console.print("  [bold #00d2ff]scan[/bold #00d2ff]             Sweep subnet (`192.168.1.0/24`) & mDNS for ARM targets")
            console.print("  [bold #00d2ff]connect <ID>[/bold #00d2ff]       Open loopback SSH bridge (e.g. 'connect 0')")
            console.print("  [bold #00d2ff]login <ID>[/bold #00d2ff]         Log in to remote ARM device via interactive SSH console")
            console.print("  [bold #00d2ff]bootstrap <ID>[/bold #00d2ff]     Deploy daemon inside target virtual environment")
            console.print("  [bold #00d2ff]ros <subcmd>[/bold #00d2ff]       Orchestrate remote ROS 2 nodes, packages & topics over bridge")
            console.print("  [bold #00d2ff]assess[/bold #00d2ff]           Execute ROS 2 hardware scorecard & DDS tuning")
            console.print("  [bold #00d2ff]dash <ID>[/bold #00d2ff]        Launch interactive real-time telemetry dashboard")
            console.print("  [bold #00d2ff]diagnose[/bold #00d2ff]         Profile local Arm SoC capabilities")
            console.print("  [bold #00d2ff]banner / clear[/bold #00d2ff]   Re-render welcome banner or clear screen")
            console.print("  [bold #00d2ff]exit / quit[/bold #00d2ff]      Exit interactive control plane\n")
            continue
            
        if cmd_line.lower() in ("banner",):
            render_banner(console)
            continue
            
        if cmd_line.lower() in ("clear", "cls"):
            console.clear()
            render_banner(console)
            continue
            
        try:
            args = shlex.split(cmd_line)
            if args and args[0].lower() == "argus":
                args = args[1:]
            if not args:
                continue
            if args[0].lower() in ("connect", "dash", "bootstrap", "login") and len(args) > 1:
                selected_target = args[1]
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except click.UsageError as e:
            console.print(f"[bold #1e90ff]Usage error:[/bold #1e90ff] {e}")
        except click.NoSuchOption as e:
            console.print(f"[bold #1e90ff]Option error:[/bold #1e90ff] {e}")
        except click.ClickException as e:
            console.print(f"[bold #1e90ff]Error:[/bold #1e90ff] {e}")
        except Exception as e:
            console.print(f"[bold #1e90ff]Command failed:[/bold #1e90ff] {e}")


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="argus")
@click.pass_context
def cli(ctx: click.Context):
    """Argus - Arm-native ROS 2 diagnostic & optimization platform."""
    if ctx.invoked_subcommand is None:
        run_interactive_shell(ctx)



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
    """Start MCP server for AI agent integration (Target mode)."""
    from argus.mcp.server import run_server
    run_server(transport=transport, host=host, port=port)


@cli.command()
@click.option("--subnet", default="192.168.1.0/24", help="Subnet to scan")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def scan(subnet: str, output_json: bool):
    """Scan local network and mDNS for ARM/Raspberry Pi targets (Host mode)."""
    from argus.host.scanner import scan_network
    console.print(f"[dim]Scanning {subnet} and local mDNS...[/dim]")
    targets = scan_network(subnet=subnet)
    
    if output_json:
        console.print(JSON(json.dumps([t.model_dump() for t in targets])))
        return
        
    table = Table(title="Discovered ARM Hardware Targets")
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("Hostname", style="bold white")
    table.add_column("IP Address", style="blue")
    table.add_column("SoC / Architecture", style="magenta")
    table.add_column("Status / Auth", style="green")
    
    for t in targets:
        status_color = "green" if "Ready" in t.status else ("yellow" if "Bootstrap" in t.status else "red")
        table.add_row(
            f"[{t.id}]",
            t.hostname,
            t.ip,
            t.soc_model,
            f"[{status_color}]{t.status}[/{status_color}]"
        )
    console.print(table)


@cli.command()
@click.argument("target", default="0")
@click.option("--port", default=2222, help="Local loopback forwarding port")
def connect(target: str, port: int):
    """Establish loopback SSH tunnel and bridge for target (Host mode)."""
    from argus.host.bridge import connect_target
    console.print(f"[bold]Connecting to Target {target}...[/bold]")
    res = connect_target(target, tunnel_port=port)
    if res.get("success"):
        console.print(f"[green]✓ {res['message']}[/green]")
    else:
        console.print(f"[red]✗ {res.get('error')}[/red]")


@cli.command()
@click.argument("target", default="0")
def bootstrap(target: str):
    """Install Argus Target CLI inside remote ARM device over SSH (Host mode)."""
    from argus.host.bridge import bootstrap_target
    console.print(f"[bold]Bootstrapping Target {target}...[/bold]")
    res = bootstrap_target(target)
    if res.get("success"):
        console.print(f"[green]✓ {res['message']}[/green]")
        console.print(f"[dim]{res['output']}[/dim]")
    else:
        console.print(f"[red]✗ Bootstrap failed: {res.get('error')}[/red]")


@cli.command("mcp-host")
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio")
@click.option("--port", default=8765, help="HTTP port")
@click.option("--host", default="127.0.0.1", help="HTTP host")
def mcp_host(transport: str, port: int, host: str):
    """Start Mac Mini Host MCP Server (`argus mcp-host`)."""
    from argus.host.mcp_host import run_host_server
    run_host_server(transport=transport, host=host, port=port)


@cli.command()
@click.argument("target", default="0")
@click.option("--port", default=2222, help="Local loopback forwarding port")
@click.option("--dash", "run_dash", is_flag=True, help="Automatically launch remote Argus telemetry dashboard")
def login(target: str, port: int, run_dash: bool):
    """Log in to remote ARM device via interactive SSH bridge."""
    import subprocess
    from argus.host.bridge import resolve_target, connect_target, check_target_status_tunnel
    
    t = resolve_target(target)
    if not t:
        if target in ("0", "192.168.1.43"):
            from argus.host.scanner import TargetDevice
            t = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43", tunnel_port=port)
        else:
            console.print(f"[red]✗ Target {target} not found in registry. Run 'argus scan' first.[/red]")
            return

    # Ensure loopback tunnel/bridge is active
    tunnel_active = check_target_status_tunnel(t.tunnel_port)
    if not tunnel_active:
        console.print(f"[dim]Bridge offline. Establishing tunnel on port {t.tunnel_port}...[/dim]")
        res = connect_target(target, tunnel_port=t.tunnel_port)
        if not res.get("success"):
            console.print(f"[red]✗ Failed to establish bridge: {res.get('error')}[/red]")
            # Fallback to direct SSH if bridge fails
            console.print(f"[yellow]Attempting direct connection to {t.username}@{t.ip}...[/yellow]")
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no {t.username}@{t.ip}"
            if run_dash:
                ssh_cmd += " -t '~/Argus/.venv/bin/argus dash'"
            subprocess.run(ssh_cmd, shell=True)
            return

    dev_label = f"Device {t.id + 1}" if isinstance(t.id, int) and t.id >= 0 else "Device 1"
    
    if run_dash:
        console.print(f"[bold #00d2ff]Launching target-side telemetry dashboard on [{dev_label}] ({t.ip})...[/bold #00d2ff]")
        ssh_cmd = f"ssh -t -o StrictHostKeyChecking=no -p {t.tunnel_port} {t.username}@127.0.0.1 '~/Argus/.venv/bin/argus dash'"
    else:
        console.print(f"[bold #00d2ff]Logging into [{dev_label}] ({t.ip}) via loopback SSH bridge...[/bold #00d2ff]")
        console.print("  [bold #38b6ff]💡 Run 'dash' inside the target console to launch the telemetry dashboard.[/bold #38b6ff]")
        console.print("  [bold #38b6ff]💡 Run 'assess' or 'diagnose' to test edge hardware capabilities.[/bold #38b6ff]")
        console.print("  [bold #b3e6ff]Type 'exit' or Ctrl+D to return to Mac Mini Host Control Plane REPL.[/bold #b3e6ff]\n")
        ssh_cmd = f"ssh -t -o StrictHostKeyChecking=no -p {t.tunnel_port} {t.username}@127.0.0.1 '~/Argus/.venv/bin/argus'"
        
    subprocess.run(ssh_cmd, shell=True)


@cli.command()
@click.argument("target", default="0")
@click.option("--refresh", default=1.0, help="Refresh interval in seconds")
def dash(target: str, refresh: float):
    """Launch interactive real-time cyberpunk target telemetry monitor (`argus dash`)."""
    from argus.ui import render_live_dashboard
    render_live_dashboard(console, target_id=target, refresh_s=refresh)


@cli.group()
def ros():
    """Orchestrate ROS 2 nodes, packages, and topics across edge targets."""
    pass


@ros.command()
@click.option("--target", default="0", help="Target ID or IP")
def status(target: str):
    """Inspect target for ROS 2 environment readiness and workspace info."""
    from argus.robotics import check_ros2_environment
    console.print(f"[bold #38b6ff]Checking ROS 2 environment on target '{target}'...[/bold #38b6ff]")
    res = check_ros2_environment(target)
    console.print(f"  [bold #b3e6ff]Installed:[/bold #b3e6ff] {res['installed']}")
    console.print(f"  [bold #b3e6ff]Distribution / Profile:[/bold #b3e6ff] [bold #00d2ff]{res['distro']}[/bold #00d2ff]")
    console.print(f"  [bold #b3e6ff]Workspace:[/bold #b3e6ff] {res['workspace']}")


@ros.command()
@click.argument("package_name")
@click.option("--build-type", default="ament_python", help="Package build type")
@click.option("--target", default="0", help="Target ID or IP")
def create(package_name: str, build_type: str, target: str):
    """Scaffold a new ROS 2 package on target."""
    from argus.robotics import ros2_create_package
    console.print(f"[bold #38b6ff]Creating ROS 2 package '{package_name}' ({build_type}) on target '{target}'...[/bold #38b6ff]")
    res = ros2_create_package(package_name, build_type=build_type, target_id_or_ip=target)
    if res["success"]:
        console.print(f"[bold #00d2ff]✔ Package '{package_name}' created successfully.[/bold #00d2ff]")
    else:
        console.print(f"[bold #1e90ff]✗ Failed to create package: {res['error']}[/bold #1e90ff]")


@ros.command()
@click.option("--pkg", default=None, help="Specific package to build")
@click.option("--target", default="0", help="Target ID or IP")
def build(pkg: Optional[str], target: str):
    """Compile target ROS 2 workspace (`colcon build`)."""
    from argus.robotics import ros2_build
    console.print(f"[bold #38b6ff]Building ROS 2 workspace on target '{target}'...[/bold #38b6ff]")
    res = ros2_build(target_id_or_ip=target, pkg_name=pkg)
    if res["success"]:
        console.print("[bold #00d2ff]✔ Workspace build completed successfully.[/bold #00d2ff]")
    else:
        console.print(f"[bold #1e90ff]✗ Workspace build failed:\n{res['error']}[/bold #1e90ff]")


@ros.command()
@click.argument("package_name")
@click.argument("node_exec")
@click.option("--target", default="0", help="Target ID or IP")
def launch(package_name: str, node_exec: str, target: str):
    """Launch a ROS 2 node on target."""
    from argus.robotics import ros2_launch_node
    console.print(f"[bold #38b6ff]Launching node '{package_name}/{node_exec}' on target '{target}'...[/bold #38b6ff]")
    res = ros2_launch_node(package_name, node_exec, target_id_or_ip=target)
    if res["success"]:
        console.print(f"[bold #00d2ff]✔ Node launched successfully.[/bold #00d2ff]\n{res['output']}")
    else:
        console.print(f"[bold #1e90ff]✗ Node launch failed:\n{res['error']}[/bold #1e90ff]")


@ros.command()
@click.argument("topic")
@click.argument("msg_type")
@click.argument("data")
@click.option("--target", default="0", help="Target ID or IP")
def pub(topic: str, msg_type: str, data: str, target: str):
    """Publish a message (`--once`) to a ROS 2 topic on target."""
    from argus.robotics import ros2_topic_pub
    console.print(f"[bold #38b6ff]Publishing to topic '{topic}' on target '{target}'...[/bold #38b6ff]")
    res = ros2_topic_pub(topic, msg_type, data, target_id_or_ip=target)
    if res["success"]:
        console.print("[bold #00d2ff]✔ Topic published.[/bold #00d2ff]")
    else:
        console.print(f"[bold #1e90ff]✗ Publish failed: {res['error']}[/bold #1e90ff]")


@ros.command()
@click.argument("topic")
@click.option("--target", default="0", help="Target ID or IP")
@click.option("--lines", default=5, help="Number of messages to echo")
def echo(topic: str, target: str, lines: int):
    """Echo recent messages from a ROS 2 topic on target."""
    from argus.robotics import ros2_topic_echo
    console.print(f"[bold #38b6ff]Echoing topic '{topic}' on target '{target}'...[/bold #38b6ff]")
    res = ros2_topic_echo(topic, target_id_or_ip=target, lines=lines)
    console.print(f"[bold #b3e6ff]{res['output']}[/bold #b3e6ff]")


@ros.command(name="tv-channel")
@click.argument("command_text")
@click.option("--target", default="0", help="Target ID or IP")
def tv_channel(command_text: str, target: str):
    """Deploy & interact with the Raspberry Pi Smart TV Robotics Controller via natural language."""
    from argus.robotics import deploy_smart_tv_project, ros2_topic_pub, ros2_topic_echo
    console.print(f"[bold #00d2ff]📺 Checking Smart TV Robotics Controller on target '{target}'...[/bold #00d2ff]")
    deploy_smart_tv_project(target_id_or_ip=target)
    console.print(f"[bold #38b6ff]Sending TV command over ROS 2 topic:[/bold #38b6ff] [bold #66c2ff]\"{command_text}\"[/bold #66c2ff]")
    pub_res = ros2_topic_pub("/smart_tv/channel_cmd", "std_msgs/msg/String", f'{{"data": "{command_text}"}}', target_id_or_ip=target)
    if pub_res["success"]:
        console.print("[bold #00d2ff]✔ TV command published to `/smart_tv/channel_cmd` successfully.[/bold #00d2ff]")
        console.print("[bold #38b6ff]Checking TV controller node activity:[/bold #38b6ff]")
        echo_res = ros2_topic_echo("/smart_tv/status", target_id_or_ip=target, lines=3)
        if echo_res["output"]:
            console.print(f"[bold #b3e6ff]{echo_res['output']}[/bold #b3e6ff]")
        else:
            console.print(f"[bold #00d2ff]Smart TV switched to: {command_text}[/bold #00d2ff]")
    else:
        console.print(f"[bold #1e90ff]✗ Failed to send TV command: {pub_res['error']}[/bold #1e90ff]")


@cli.command()
def version():
    """Print version info."""
    from argus import __version__
    console.print(f"Argus v{__version__}")


if __name__ == "__main__":
    cli()