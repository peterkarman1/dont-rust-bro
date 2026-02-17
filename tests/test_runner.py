import os
import pytest
from unittest.mock import patch
from drb.runner import run_tests


def test_passing_solution():
    with patch("drb.runner.run_in_container") as mock_container:
        mock_container.return_value = {"passed": True, "output": "1 passed"}
        result = run_tests("def add(a,b): return a+b",
                           "from solution import add\ndef test(): assert add(1,2)==3",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q")
    assert result["passed"] is True
    assert "1 passed" in result["output"]


def test_failing_solution():
    with patch("drb.runner.run_in_container") as mock_container:
        mock_container.return_value = {"passed": False, "output": "FAILED"}
        result = run_tests("def add(a,b): return 0",
                           "from solution import add\ndef test(): assert add(1,2)==3",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q")
    assert result["passed"] is False


def test_timeout():
    with patch("drb.runner.run_in_container") as mock_container:
        mock_container.return_value = {"passed": False, "output": "Timeout: tests did not complete within 2 seconds."}
        result = run_tests("import time\ndef slow(): time.sleep(30)",
                           "from solution import slow\ndef test(): slow()",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q",
                           timeout=2)
    assert result["passed"] is False
    assert "timeout" in result["output"].lower()


def test_files_written_to_tmpdir():
    written_dir = [None]
    def mock_run_in_container(engine, image, test_command, work_dir, timeout=10):
        written_dir[0] = work_dir
        assert os.path.isfile(os.path.join(work_dir, "solution.py"))
        assert os.path.isfile(os.path.join(work_dir, "test_solution.py"))
        return {"passed": True, "output": "ok"}

    with patch("drb.runner.run_in_container", side_effect=mock_run_in_container):
        run_tests("code", "test_code", engine="docker", image="img",
                  test_command="pytest test_solution.py")


def test_custom_filenames():
    written_files = []
    def mock_run_in_container(engine, image, test_command, work_dir, timeout=10):
        written_files.append(os.listdir(work_dir))
        assert os.path.isfile(os.path.join(work_dir, "solution.js"))
        assert os.path.isfile(os.path.join(work_dir, "test_solution.js"))
        return {"passed": True, "output": "ok"}

    with patch("drb.runner.run_in_container", side_effect=mock_run_in_container):
        run_tests("code", "test_code", engine="docker", image="img",
                  test_command="jest", solution_file="solution.js",
                  test_file="test_solution.js")
