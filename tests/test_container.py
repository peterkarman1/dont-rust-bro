import pytest
import subprocess as subprocess_mod
from unittest.mock import patch
from drb.container import detect_engine, ensure_image, run_in_container


def test_detect_engine_podman_preferred():
    with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("podman", "docker") else None):
        assert detect_engine() == "podman"


def test_detect_engine_docker_fallback():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/docker" if x == "docker" else None):
        assert detect_engine() == "docker"


def test_detect_engine_none():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="docker or podman"):
            detect_engine()


def test_ensure_image_already_present():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = type("R", (), {"returncode": 0})()
        ensure_image("docker", "python:3.12-slim")
        assert mock_run.call_count == 1
        assert "inspect" in mock_run.call_args[0][0]


def test_ensure_image_pulls_missing():
    call_count = [0]
    def side_effect(cmd, **kwargs):
        call_count[0] += 1
        r = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if "inspect" in cmd:
            r.returncode = 1
        return r

    with patch("subprocess.run", side_effect=side_effect):
        ensure_image("docker", "python:3.12-slim")
    assert call_count[0] == 2  # inspect + pull


def test_run_in_container_passing(tmp_path):
    def mock_run(cmd, **kwargs):
        return type("R", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=10)
    assert result["passed"] is True
    assert "1 passed" in result["output"]


def test_run_in_container_failing(tmp_path):
    def mock_run(cmd, **kwargs):
        return type("R", (), {"returncode": 1, "stdout": "FAILED", "stderr": ""})()

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=10)
    assert result["passed"] is False


def test_run_in_container_timeout(tmp_path):
    def mock_run(cmd, **kwargs):
        raise subprocess_mod.TimeoutExpired(cmd=cmd, timeout=2)

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=2)
    assert result["passed"] is False
    assert "timeout" in result["output"].lower()


def test_run_in_container_command_structure(tmp_path):
    captured_cmd = []
    def mock_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    with patch("subprocess.run", side_effect=mock_run):
        run_in_container("docker", "python:3.12-slim",
                         "pytest test_solution.py", str(tmp_path), timeout=10)

    assert captured_cmd[0] == "docker"
    assert "run" in captured_cmd
    assert "--rm" in captured_cmd
    assert "--network=none" in captured_cmd
    assert "--memory=256m" in captured_cmd
