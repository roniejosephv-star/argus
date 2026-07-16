"""Permission gatekeeper for tool execution."""

from __future__ import annotations

from typing import Literal, Protocol
from dataclasses import dataclass

from argus.safety.blast_radius import BlastRadius, APPROVAL_POLICY, TOOL_CLASSIFICATIONS
from argus.safety.blocklist import is_blocked, get_block_reason


class ToolSpecProtocol(Protocol):
    """Protocol for tool spec - avoids circular import."""
    name: str
    description: str
    category: str
    blast_radius: BlastRadius
    timeout_s: int
    parameters: type
    handler: callable


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str
    blast_radius: BlastRadius
    requires_prompt: bool


class Gatekeeper:
    """Evaluates tool calls for permission before execution."""
    
    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self.session_allowed: set[str] = set()  # Tools allowed for this session
    
    def check_permission(self, tool_spec: ToolSpecProtocol, args: dict) -> PermissionDecision:
        """Check if tool execution is permitted."""
        
        # 1. Blocklist check (hard deny)
        command = args.get("command", "")
        if is_blocked(tool_spec.name, command):
            reason = get_block_reason(tool_spec.name, command) or "Blocked by safety policy"
            return PermissionDecision(
                allowed=False,
                reason=reason,
                blast_radius=BlastRadius.CRITICAL,
                requires_prompt=False,
            )
        
        # 2. Blast radius lookup
        blast_radius = TOOL_CLASSIFICATIONS.get(tool_spec.name, BlastRadius.HIGH)
        policy = APPROVAL_POLICY[blast_radius]
        
        # 3. Evaluate policy
        if policy == "auto":
            return PermissionDecision(
                allowed=True,
                reason="Auto-approved (blast radius: NONE/LOW)",
                blast_radius=blast_radius,
                requires_prompt=False,
            )
        
        elif policy == "deny":
            return PermissionDecision(
                allowed=False,
                reason=f"Denied: blast radius {blast_radius.value} is CRITICAL",
                blast_radius=blast_radius,
                requires_prompt=False,
            )
        
        elif policy == "ask":
            # Check session allowance
            if tool_spec.name in self.session_allowed:
                return PermissionDecision(
                    allowed=True,
                    reason=f"Session-approved (blast radius: {blast_radius.value})",
                    blast_radius=blast_radius,
                    requires_prompt=False,
                )
            
            if self.auto_approve:
                return PermissionDecision(
                    allowed=True,
                    reason=f"Auto-approved via ARGUS_AUTO_APPROVE (blast radius: {blast_radius.value})",
                    blast_radius=blast_radius,
                    requires_prompt=False,
                )
            
            return PermissionDecision(
                allowed=False,
                reason=f"Requires user approval (blast radius: {blast_radius.value})",
                blast_radius=blast_radius,
                requires_prompt=True,
            )
        
        return PermissionDecision(
            allowed=False,
            reason="Unknown policy",
            blast_radius=BlastRadius.HIGH,
            requires_prompt=False,
        )
    
    def allow_session(self, tool_name: str):
        """Allow tool for remainder of session."""
        self.session_allowed.add(tool_name)
    
    def prompt_user(self, tool_spec: ToolSpec, args: dict, decision: PermissionDecision) -> bool:
        """Prompt user for approval (CLI mode)."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
        
        console = Console()
        
        # Format action description
        action_desc = self._describe_action(tool_spec, args)
        
        if decision.blast_radius == BlastRadius.MEDIUM:
            panel = Panel.fit(
                f"[bold]Tool:[/bold] {tool_spec.name}\n"
                f"[bold]Action:[/bold] {action_desc}\n\n"
                f"[yellow]Blast radius: MEDIUM[/yellow] - writes files",
                title="🛡️ Permission Required",
                border_style="yellow",
            )
            options = ["y", "n", "v", "a", "q"]
            prompt_text = "Proceed? [y]es / [n]o / [v]iew files / [a]llow session / [q]uit"
        else:  # HIGH
            panel = Panel.fit(
                f"[bold]Tool:[/bold] {tool_spec.name}\n"
                f"[bold]Action:[/bold] {action_desc}\n\n"
                f"[red]Blast radius: HIGH[/red] - executes shell commands",
                title="🛡️ Permission Required (HIGH RISK)",
                border_style="red",
            )
            options = ["y", "n", "d", "q"]
            prompt_text = "Proceed? [y]es / [n]o / [d]etail / [q]uit"
        
        console.print(panel)
        
        while True:
            choice = Prompt.ask(prompt_text, choices=options, default="n").lower()
            
            if choice == "y":
                return True
            elif choice == "n":
                return False
            elif choice == "v" and decision.blast_radius == BlastRadius.MEDIUM:
                self._show_files(tool_spec, args)
            elif choice == "a":
                self.allow_session(tool_spec.name)
                console.print("[green]Session approval granted for this tool.[/green]")
                return True
            elif choice == "d":
                self._show_detail(tool_spec, args, decision)
            elif choice == "q":
                return False
        
        return False
    
    def _describe_action(self, tool_spec: ToolSpec, args: dict) -> str:
        """Generate human-readable action description."""
        if tool_spec.name == "generate_all_configs":
            return f"Write 6 config files to {args.get('output_dir', './configs')}/{args.get('soc_model', 'unknown')}/"
        elif tool_spec.name == "write_config":
            return f"Write config file: {args.get('path', 'unknown')}"
        elif tool_spec.name == "run_command":
            return f"Execute: {args.get('command', '')}"
        elif tool_spec.name == "apply_sysctl":
            return "Apply sysctl kernel parameters"
        elif tool_spec.name == "colcon_build":
            return f"Build ROS 2 workspace in {args.get('workspace', '.')}"
        return tool_spec.description
    
    def _show_files(self, tool_spec: ToolSpec, args: dict):
        """Show files that would be created."""
        from rich.console import Console
        console = Console()
        if tool_spec.name == "generate_all_configs":
            console.print("[cyan]Files to be created:[/cyan]")
            for f in ["cyclonedds.xml", "fastdds.xml", "zenoh_advice.yaml", "sysctl.conf", "build_flags.json", "install_ros2.sh"]:
                console.print(f"  • {f}")
        elif tool_spec.name == "write_config":
            console.print(f"[cyan]File: {args.get('path', 'unknown')}[/cyan]")
            console.print(args.get('content', '')[:500])
    
    def _show_detail(self, tool_spec: ToolSpec, args: dict, decision: PermissionDecision):
        """Show detailed reason for HIGH risk."""
        from rich.console import Console
        console = Console()
        console.print(f"[bold]Tool:[/bold] {tool_spec.name}")
        console.print(f"[bold]Blast radius:[/bold] {decision.blast_radius.value}")
        console.print(f"[bold]Reason:[/bold] {decision.reason}")
        console.print(f"[bold]Command:[/bold] {args.get('command', 'N/A')}")


def create_gatekeeper(auto_approve: bool = False) -> Gatekeeper:
    """Factory function for gatekeeper."""
    return Gatekeeper(auto_approve=auto_approve)