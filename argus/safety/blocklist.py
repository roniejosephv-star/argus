"""Command blocklist for safety gatekeeper."""

import re

BLOCKLIST_PATTERNS: list[str] = [
    r"rm\s+-rf\s+/",           # Root deletion
    r"sudo\s+.*",               # Sudo elevation
    r">\s+/dev/",               # Device overwrite
    r"dd\s+if=.*of=.*",        # Raw disk operations
    r"mkfs\.*\s+",             # Filesystem creation
    r":\(\)\{\s*:\s*\|\|:\s*&\s*\};:",  # Fork bomb
    r"curl.*\|\s*(bash|sh)",   # Pipe to shell
    r"wget.*\|\s*(bash|sh)",   # Pipe to shell
    r"chmod\s+777\s+/",        # World-writable root
    r"chown\s+-R\s+.*\s+/",    # Recursive chown root
    r"mount\s+-o\s+remount,rw\s+/",  # Remount root RW
]

BLOCKLIST_COMMANDS: list[str] = [
    "vim", "vi", "nano", "emacs",    # Interactive editors
    "nohup",                          # Background processes
    "gdb", "lldb", "valgrind",        # Debuggers
    "tmux", "screen",                 # Session managers
    "reboot", "shutdown", "halt",     # System control
    "systemctl", "service",           # Service management
    "apt", "apt-get", "dpkg",         # Package management
    "pip", "pip3",                    # Python packages
    "cargo", "go", "npm", "yarn",     # Other package managers
    "make", "cmake", "ninja",         # Build tools (use colcon_build instead)
]


def is_blocked(tool_name: str, command: str) -> bool:
    """Check if a command matches any blocklist pattern."""
    if tool_name != "run_command":
        return False
    
    cmd = command.strip()
    if not cmd:
        return True
    
    # Check pattern blocklist
    for pattern in BLOCKLIST_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True
    
    # Check command name blocklist
    cmd_name = cmd.split()[0] if cmd.split() else ""
    if cmd_name in BLOCKLIST_COMMANDS:
        return True
    
    return False


def get_block_reason(tool_name: str, command: str) -> str | None:
    """Get human-readable reason for blocking."""
    if tool_name != "run_command":
        return None
    
    cmd = command.strip()
    if not cmd:
        return "Empty command"
    
    for pattern in BLOCKLIST_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return f"Matches blocked pattern: {pattern}"
    
    cmd_name = cmd.split()[0] if cmd.split() else ""
    if cmd_name in BLOCKLIST_COMMANDS:
        return f"Blocked command: {cmd_name}"
    
    return None