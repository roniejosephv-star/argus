"""Host-side control plane module for Argus Mac Mini installation."""

from __future__ import annotations

from argus.host.scanner import scan_network, load_targets, save_targets, TargetDevice
from argus.host.bridge import connect_target, bootstrap_target, sync_mcp_configs

__all__ = [
    "scan_network",
    "load_targets",
    "save_targets",
    "TargetDevice",
    "connect_target",
    "bootstrap_target",
    "sync_mcp_configs",
]
