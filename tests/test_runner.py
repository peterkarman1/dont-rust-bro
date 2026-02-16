import pytest
from drb.runner import run_tests


def test_passing_solution():
    user_code = "def add(a, b):\n    return a + b\n"
    test_code = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    result = run_tests(user_code, test_code, timeout=10)
    assert result["passed"] is True
    assert "1 passed" in result["output"]


def test_failing_solution():
    user_code = "def add(a, b):\n    return 0\n"
    test_code = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    result = run_tests(user_code, test_code, timeout=10)
    assert result["passed"] is False
    assert "FAILED" in result["output"] or "failed" in result["output"]


def test_syntax_error():
    user_code = "def add(a, b)\n    return a + b\n"
    test_code = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    result = run_tests(user_code, test_code, timeout=10)
    assert result["passed"] is False
    assert "error" in result["output"].lower() or "Error" in result["output"]


def test_timeout():
    user_code = "import time\ndef slow():\n    time.sleep(30)\n"
    test_code = "from solution import slow\n\ndef test_slow():\n    slow()\n"
    result = run_tests(user_code, test_code, timeout=2)
    assert result["passed"] is False
    assert "timeout" in result["output"].lower()
