"""Unit tests for new peripheral and project management tools."""

import os
from pathlib import Path
from argus.core.peripherals import detect_serial_ports, configure_micro_ros_uart
from argus.core.project_tools import (
    project_list_files,
    project_read_file,
    project_write_file,
    project_git_status,
    project_git_diff,
    project_run_command,
)
from argus.core.toolbox import execute_tool, TOOL_REGISTRY


def test_peripherals_detect_serial_ports():
    ports = detect_serial_ports()
    assert isinstance(ports, list)
    # Even on macOS or standard Linux, it returns candidates for ttyAMA0 or discovered ports
    assert len(ports) >= 0


def test_peripherals_configure_micro_ros_uart():
    advice = configure_micro_ros_uart(device="/dev/ttyAMA0", baudrate=921600)
    assert advice["device"] == "/dev/ttyAMA0"
    assert advice["baudrate"] == 921600
    assert "serial-getty@ttyAMA0.service" in advice["getty_service"]
    assert "enable_uart=1" in advice["setup_script"]
    assert "micro_ros_agent" in advice["systemd_unit"]


def test_project_list_and_read_files(tmp_path):
    # Create test directory and file
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello ROS 2 Jazzy!\nLine 2\n")
    
    res = project_list_files(directory=str(tmp_path))
    assert "files" in res
    assert any(f["path"] == "hello.txt" for f in res["files"])
    
    read_res = project_read_file(file_path=str(test_file))
    assert read_res["lines_read"] == 2
    assert "Hello ROS 2 Jazzy!" in read_res["content"]


def test_project_write_file_with_backup(tmp_path):
    target = tmp_path / "config.yaml"
    target.write_text("initial: true\n")
    
    res = project_write_file(file_path=str(target), content="updated: true\n", backup=True)
    assert res["status"] == "success"
    assert target.read_text() == "updated: true\n"
    assert (tmp_path / "config.yaml.bak").exists()
    assert (tmp_path / "config.yaml.bak").read_text() == "initial: true\n"


def test_project_run_command(tmp_path):
    res = project_run_command("echo 'Argus test'", cwd=str(tmp_path))
    assert res["returncode"] == 0
    assert "Argus test" in res["stdout"]


def test_tool_registry_has_all_23_tools():
    # We started with 14 tools and added 2 peripheral + 7 project tools = 23 tools total!
    assert len(TOOL_REGISTRY) >= 23
    assert "detect_serial_ports" in TOOL_REGISTRY
    assert "configure_micro_ros_uart" in TOOL_REGISTRY
    assert "project_list_files" in TOOL_REGISTRY
    assert "project_run_command" in TOOL_REGISTRY
    
    # Test execution through dispatcher
    res = execute_tool("detect_serial_ports", {})
    assert "ports" in res
