import os
import subprocess
import sys
import tempfile


def run_tests(user_code: str, test_code: str, timeout: int = 10) -> dict:
    """Run user code against test code using pytest in a subprocess.

    Returns dict with 'passed' (bool) and 'output' (str).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        solution_path = os.path.join(tmpdir, "solution.py")
        test_path = os.path.join(tmpdir, "test_solution.py")

        with open(solution_path, "w") as f:
            f.write(user_code)
        with open(test_path, "w") as f:
            f.write(test_code)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
            output = result.stdout + result.stderr
            passed = result.returncode == 0
        except subprocess.TimeoutExpired:
            output = f"Timeout: tests did not complete within {timeout} seconds."
            passed = False

        return {"passed": passed, "output": output.strip()}
