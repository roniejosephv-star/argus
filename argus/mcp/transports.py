"""MCP transport configuration."""

from __future__ import annotations

from pydantic import BaseModel
from typing import Literal


class TransportConfig(BaseModel):
    mode: Literal["stdio", "http", "both"] = "both"
    host: str = "127.0.0.1"
    port: int = 8765
    auth_token: str | None = None  # From ARGUS_MCP_TOKEN env var