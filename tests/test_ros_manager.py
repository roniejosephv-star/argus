"""Unit and integration tests for Universal ROS 2 & Robotics Manager (`ros_manager.py`)."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from argus.robotics.ros_manager import (
    check_ros2_environment,
    ros2_create_package,
    ros2_build,
    ros2_launch_node,
    ros2_topic_pub,
    ros2_topic_echo,
    deploy_smart_tv_project,
)
from argus.common import ArgusLogger


def test_check_ros2_environment_host(tmp_path: Path):
    logger = ArgusLogger.get_instance(log_dir=tmp_path)
    logger.clear_phase_logs("phase3_ros2")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "humble\n"

        res = check_ros2_environment("host")
        assert res["installed"] is True
        assert res["distro"] == "humble"

        logs = logger.get_phase_logs("phase3_ros2")
        assert any("ROS2 Environment Check" in l["event"] for l in logs)


def test_ros2_create_package_fallback(tmp_path: Path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Package smart_tv_bot scaffolded at ~/ros2_ws/src/smart_tv_bot"

        res = ros2_create_package("smart_tv_bot", target_id_or_ip="host")
        assert res["success"] is True
        assert "scaffolded" in res["output"]


def test_ros2_build(tmp_path: Path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Summary: 1 package finished [0.5s]"

        res = ros2_build(target_id_or_ip="host", pkg_name="smart_tv_bot")
        assert res["success"] is True


def test_ros2_launch_node(tmp_path: Path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Node smart_tv_bot/smart_tv_node launched with PID 12345"

        res = ros2_launch_node("smart_tv_bot", "smart_tv_node", target_id_or_ip="host")
        assert res["success"] is True


def test_ros2_topic_pub_and_echo(tmp_path: Path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Published message to /smart_tv/channel_cmd"

        pub_res = ros2_topic_pub("/smart_tv/channel_cmd", "std_msgs/msg/String", '{"data": "BBC News"}', target_id_or_ip="host")
        assert pub_res["success"] is True

        mock_run.return_value.stdout = "data: 'TV switched to BBC News (CH 101)'"
        echo_res = ros2_topic_echo("/smart_tv/status", target_id_or_ip="host")
        assert echo_res["success"] is True
        assert "BBC News" in echo_res["output"]


def test_deploy_smart_tv_project(tmp_path: Path):
    with patch("subprocess.run") as mock_run, \
         patch("argus.robotics.ros_manager.ros2_build") as mock_build, \
         patch("argus.robotics.ros_manager.ros2_launch_node") as mock_launch:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Smart TV Package files written to ~/ros2_ws/src/smart_tv_bot"
        mock_build.return_value = {"success": True}
        mock_launch.return_value = {"success": True}

        res = deploy_smart_tv_project("host")
        assert res["success"] is True
        mock_build.assert_called_once()
        mock_launch.assert_called_once()
