"""Remote project management and build tools for Argus self-hosted development loop."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class ProjectListFilesParams(BaseModel):
    directory: str = "."
    pattern: str = "*"
    recursive: bool = False
    max_depth: int = 3


class ProjectReadFileParams(BaseModel):
    file_path: str
    max_lines: int = 500


class ProjectWriteFileParams(BaseModel):
    file_path: str
    content: str
    backup: bool = True


class ProjectGitStatusParams(BaseModel):
    directory: str = "."


class ProjectGitDiffParams(BaseModel):
    directory: str = "."
    file_path: str | None = None


class ProjectPipInstallParams(BaseModel):
    package: str = "-e ."
    break_system_packages: bool = True


class ProjectRunCommandParams(BaseModel):
    command: str
    cwd: str = "."
    timeout_s: int = 300


def project_list_files(directory: str = ".", pattern: str = "*", recursive: bool = False, max_depth: int = 3) -> dict[str, Any]:
    """List files in the target directory matching pattern up to max_depth."""
    target = Path(directory).resolve()
    if not target.exists():
        return {"error": f"Directory does not exist: {target}"}
    if not target.is_dir():
        return {"error": f"Not a directory: {target}"}
    
    files = []
    base_depth = len(target.parts)
    
    if recursive:
        for p in target.rglob(pattern):
            if len(p.parts) - base_depth <= max_depth:
                if ".git" in p.parts or "__pycache__" in p.parts or ".venv" in p.parts:
                    continue
                files.append({
                    "path": str(p.relative_to(target)),
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                })
    else:
        for p in target.glob(pattern):
            if ".git" in p.parts or "__pycache__" in p.parts or ".venv" in p.parts:
                continue
            files.append({
                "path": str(p.relative_to(target)),
                "is_dir": p.is_dir(),
                "size_bytes": p.stat().st_size if p.is_file() else 0,
            })
            
    return {"directory": str(target), "files": sorted(files, key=lambda x: (not x["is_dir"], x["path"]))}


def project_read_file(file_path: str, max_lines: int = 500) -> dict[str, Any]:
    """Read contents of a file up to max_lines."""
    target = Path(file_path).resolve()
    if not target.exists() or not target.is_file():
        return {"error": f"File not found: {target}"}
        
    try:
        lines = []
        with open(target, "r", errors="replace") as f:
            for idx, line in enumerate(f):
                if idx >= max_lines:
                    lines.append(f"... [Truncated at {max_lines} lines] ...\n")
                    break
                lines.append(line)
        return {
            "file_path": str(target),
            "lines_read": min(idx + 1, max_lines),
            "content": "".join(lines)
        }
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}


def project_write_file(file_path: str, content: str, backup: bool = True) -> dict[str, Any]:
    """Write or overwrite file content, optionally creating a .bak backup."""
    target = Path(file_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    
    if backup and target.exists():
        bak_path = target.with_suffix(target.suffix + ".bak")
        try:
            shutil.copy2(target, bak_path)
        except Exception:
            pass
            
    try:
        target.write_text(content)
        return {
            "status": "success",
            "file_path": str(target),
            "size_bytes": len(content.encode()),
            "backed_up": backup and target.exists()
        }
    except Exception as e:
        return {"error": f"Failed to write file: {e}"}


def project_git_status(directory: str = ".") -> dict[str, Any]:
    """Check git status of the project directory."""
    target = Path(directory).resolve()
    try:
        res = subprocess.run(["git", "status", "--short", "--branch"], cwd=target, capture_output=True, text=True, check=False)
        return {
            "status": res.stdout.strip(),
            "error": res.stderr.strip() if res.returncode != 0 else None
        }
    except Exception as e:
        return {"error": f"Git command failed: {e}"}


def project_git_diff(directory: str = ".", file_path: str | None = None) -> dict[str, Any]:
    """Check git diff of modified files or a specific file."""
    target = Path(directory).resolve()
    cmd = ["git", "diff"]
    if file_path:
        cmd.append(file_path)
    try:
        res = subprocess.run(cmd, cwd=target, capture_output=True, text=True, check=False)
        diff_text = res.stdout
        if len(diff_text) > 30000:
            diff_text = diff_text[:30000] + "\n... [Diff truncated at 30KB] ..."
        return {
            "diff": diff_text,
            "error": res.stderr.strip() if res.returncode != 0 else None
        }
    except Exception as e:
        return {"error": f"Git diff command failed: {e}"}


def project_pip_install(package: str = "-e .", break_system_packages: bool = True) -> dict[str, Any]:
    """Install Python packages via pip inside the workspace virtual environment or system."""
    cmd = ["python3", "-m", "pip", "install"]
    if break_system_packages and "--break-system-packages" not in package:
        cmd.append("--break-system-packages")
    cmd.extend(package.split())
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "returncode": res.returncode,
            "stdout": res.stdout[-4096:] if len(res.stdout) > 4096 else res.stdout,
            "stderr": res.stderr[-2048:] if len(res.stderr) > 2048 else res.stderr,
        }
    except Exception as e:
        return {"error": f"pip install command failed: {e}"}


def project_run_command(command: str, cwd: str = ".", timeout_s: int = 300) -> dict[str, Any]:
    """Run a shell build or test command (e.g. colcon build, pytest) with timeout and capture output."""
    target = Path(cwd).resolve()
    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=target,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False
        )
        return {
            "returncode": res.returncode,
            "stdout": res.stdout[-8192:] if len(res.stdout) > 8192 else res.stdout,
            "stderr": res.stderr[-4096:] if len(res.stderr) > 4096 else res.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout_s} seconds"}
    except Exception as e:
        return {"error": f"Command execution failed: {e}"}
