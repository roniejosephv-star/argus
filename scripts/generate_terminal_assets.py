"""Generate high-resolution SVG/HTML/terminal captures for GitHub README."""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def generate_host_terminal():
    console = Console(record=True, width=95, force_terminal=True)
    
    # Render Host Header
    header = Text()
    header.append("█  Argus — Arm-Native Edge Robotics & DDS Control Plane        █\n", style="bold #38b6ff")
    header.append("█           MAC MINI HOST TIER ◄═ [BRIDGE] ═► ARM EDGE TARGET  █", style="bold #00d2ff")
    console.print(Align.center(header))
    console.print("")
    
    panel_text = (
        "[bold #38b6ff]Version 0.1.0[/bold #38b6ff] · [bold white]Mac Mini Host Control Tier (darwin)[/bold white] · [bold #00ff88]Dynamic Telemetry Sync[/bold #00ff88]\n"
        "[bold #00ff88]✔ ARGUS CONTROL PLANE ONLINE · 1 TARGET(S) REGISTERED[/bold #00ff88]"
    )
    console.print(Panel(panel_text, title="[bold #00d2ff] ARGUS CORE STATUS [/bold #00d2ff]", border_style="#00d2ff"))
    
    # Fleet Table
    table = Table(title="[bold #00d2ff]─── [ REGISTERED ARM EDGE FLEET & TUNNEL STATUS ] ───[/bold #00d2ff]", box=None, expand=True)
    table.add_column("ID", style="bold cyan", width=6)
    table.add_column("Hostname", style="bold white", width=16)
    table.add_column("IP Address", style="blue", width=14)
    table.add_column("Hardware SoC", style="magenta", width=22)
    table.add_column("Bridge / Tunnel", style="green", width=24)
    
    table.add_row(
        "[1]",
        "armcreate-pi4",
        "192.168.1.43",
        "BCM2711 · Cortex-A72",
        "[bold #00ff88]● ACTIVE (localhost:2222)[/bold #00ff88]"
    )
    console.print(table)
    console.print("")
    
    # Commands Panel
    cmd_panel = (
        "[bold #00d2ff]argus scan[/bold #00d2ff]             Sweep subnet (`192.168.1.0/24`) & mDNS for ARM targets\n"
        "[bold #00d2ff]argus connect 0[/bold #00d2ff]        Establish loopback SSH bridge & check target daemon\n"
        "[bold #00d2ff]argus login 0[/bold #00d2ff]          Drop directly into remote ARM board interactive REPL\n"
        "[bold #00d2ff]argus ros tv-channel[/bold #00d2ff]   Deploy & verify Smart TV natural language controller\n"
        "[bold #00d2ff]argus mcp-host[/bold #00d2ff]         Start FastMCP host orchestration server (`stdio`/`http`)"
    )
    console.print(Panel(cmd_panel, title="[bold #38b6ff] HOST ORCHESTRATION COMMAND DIRECTORY [/bold #38b6ff]", border_style="#38b6ff"))
    
    console.print("[bold #38b6ff]Interactive Mac Mini Host Control Plane Active[/bold #38b6ff]")
    console.print("[bold #66c2ff]─── [ Dynamic Telemetry · Target [Device 1]: armcreate-pi4 · Bridge: ● ACTIVE ] ───[/bold #66c2ff]")
    console.print("[bold #00d2ff]argus [Device 1]>[/bold #00d2ff] ros pub /smart_tv/command std_msgs/msg/String '{\"data\": \"channel up\"}' --target 0")
    console.print("[bold #00ff88]✔ Published to /smart_tv/command on target 0: {\"data\": \"channel up\"}[/bold #00ff88]")
    
    svg_path = ASSETS_DIR / "terminal_host.svg"
    console.save_svg(str(svg_path), title="Argus Mac Mini Host Control Tier")
    print(f"Generated {svg_path}")


def generate_target_terminal():
    console = Console(record=True, width=95, force_terminal=True)
    
    panel_text = (
        "[bold #38b6ff]Version 0.1.0[/bold #38b6ff] · [bold white]ARM Edge Target Control Tier (armCreate)[/bold white] · [bold #00ff88]Dynamic Telemetry Sync[/bold #00ff88]\n"
        "[bold #00ff88]✔ ARGUS CONTROL PLANE ONLINE · TELEMETRY BRIDGE SYNCHRONIZED[/bold #00ff88]"
    )
    console.print(Panel(panel_text, title="[bold #00d2ff] ARGUS EDGE STATUS [/bold #00d2ff]", border_style="#00d2ff"))
    
    sys_panel = (
        "[bold cyan]Target SoC:[/bold cyan]          linux (aarch64) · Cortex-A72 (4 Cores @ 1.5GHz)\n"
        "[bold cyan]Edge Telemetry:[/bold cyan]      0.4 / 1.8 GB RAM (22%) · Real-Time Dynamic Sync\n"
        "[bold cyan]Host Connection:[/bold cyan]     [bold #00ff88]✔ ACTIVE (Connected to Mac Mini via Loopback Bridge)[/bold #00ff88]\n"
        "[bold cyan]AI Proxy Engine:[/bold cyan]     Antigravity 2.0 Proxy Ready · FastMCP Stream Sync [bold #00ff88]✔ VERIFIED[/bold #00ff88]\n"
        "[bold cyan]ROS 2 & DDS Tier:[/bold cyan]    [bold #00ff88]✔ ROS 2 & FastDDS / CycloneDDS Configured · Node Ready[/bold #00ff88]"
    )
    console.print(Panel(sys_panel, title="[bold #38b6ff] EDGE TARGET CONTROL TIER : ARMCREATE [/bold #38b6ff]", border_style="#38b6ff"))
    
    periph_panel = (
        "[bold cyan]Thermal Zone:[/bold cyan]        [bold #00ff88]54.0°C (Nominal - No Throttling)[/bold #00ff88]\n"
        "[bold cyan]UART & Serial:[/bold cyan]       Discovered (/dev/ttyS0, /dev/ttyAMA0) · Micro-ROS UART Ready\n"
        "[bold cyan]DDS Transport:[/bold cyan]       FastDDS Shared Memory / UDPv4 Active (`micro-ros` Tier)"
    )
    console.print(Panel(periph_panel, title="[bold #38b6ff] EDGE TARGET PERIPHERALS & SENSORS [/bold #38b6ff]", border_style="#38b6ff"))
    
    cmd_panel = (
        "[bold #00d2ff]argus diagnose[/bold #00d2ff]         Profile Arm SoC & print detailed hardware capabilities\n"
        "[bold #00d2ff]argus assess[/bold #00d2ff]           Execute full ROS 2 hardware scorecard & generate DDS configs\n"
        "[bold #00d2ff]argus stress[/bold #00d2ff]           Run CPU/memory stress tests & verify thermal stability\n"
        "[bold #00d2ff]argus dash[/bold #00d2ff]             Monitor real-time edge telemetry & RAM allocation\n"
        "[bold #00d2ff]argus exit[/bold #00d2ff]             Exit remote target session & return to Mac Mini Host"
    )
    console.print(Panel(cmd_panel, title="[bold #00d2ff] EDGE COMMAND DIRECTORY [/bold #00d2ff]", border_style="#00d2ff"))
    
    console.print("[bold #38b6ff]Interactive Edge Target Control Plane Active[/bold #38b6ff]")
    console.print("[bold #66c2ff]─── [ Target Telemetry Probe · Node: armCreate · Edge Mode: ● ACTIVE ] ───[/bold #66c2ff]")
    console.print("[bold #00d2ff]argus [armCreate]>[/bold #00d2ff] assess")
    console.print("[bold #00ff88]✔ Generated 7 optimal configs in ./configs: cyclonedds.xml, sysctl.conf, build_flags.json...[/bold #00ff88]")
    
    svg_path = ASSETS_DIR / "terminal_target.svg"
    console.save_svg(str(svg_path), title="Argus ARM Edge Target Control Tier")
    print(f"Generated {svg_path}")


def generate_dashboard_terminal():
    console = Console(record=True, width=95, force_terminal=True)
    
    title = "[bold #38b6ff]⚡ ARGUS EDGE TELEMETRY MONITOR (`argus dash`) ⚡[/bold #38b6ff]"
    console.print(Align.center(title))
    console.print("")
    
    # Metrics
    table = Table(box=None, expand=True)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Status / Reading", style="bold white")
    table.add_column("Gauge / Visualization", style="green")
    
    table.add_row(
        "CPU Load (4x Cortex-A72)",
        "28.4% @ 1.50 GHz",
        "[bold #00ff88]███████████─────────────────────────────[/bold #00ff88] 28%"
    )
    table.add_row(
        "RAM Allocation",
        "412.0 MB / 1840.0 MB",
        "[bold #38b6ff]████████────────────────────────────────[/bold #38b6ff] 22%"
    )
    table.add_row(
        "Thermal Zone (/sys/class)",
        "[bold #00ff88]54.0°C (Nominal)[/bold #00ff88]",
        "[bold #00ff88]███████████████████─────────────────────[/bold #00ff88] 54°C"
    )
    table.add_row(
        "ROS 2 Bridge Transport",
        "FastDDS / SHM + UDP",
        "[bold #00d2ff]● ACTIVE (`localhost:2222` Loopback)[/bold #00d2ff]"
    )
    table.add_row(
        "Active ROS 2 Nodes",
        "3 Nodes Running",
        "[bold white]/smart_tv_node, /argus_telemetry, /bridge[/bold white]"
    )
    
    console.print(Panel(table, title="[bold #00d2ff] REAL-TIME EDGE TARGET TELEMETRY [/bold #00d2ff]", border_style="#00d2ff"))
    console.print("[dim]Press Ctrl+C to return to interactive Argus REPL[/dim]")
    
    svg_path = ASSETS_DIR / "terminal_dash.svg"
    console.save_svg(str(svg_path), title="Argus Real-Time Cyberpunk Dashboard")
    print(f"Generated {svg_path}")


if __name__ == "__main__":
    generate_host_terminal()
    generate_target_terminal()
    generate_dashboard_terminal()
