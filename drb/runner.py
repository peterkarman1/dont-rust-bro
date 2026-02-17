import os
import tempfile

from drb.container import run_in_container


def run_tests(user_code: str, test_code: str, engine: str, image: str,
              test_command: str, timeout: int = 10,
              solution_file: str = "solution.py",
              test_file: str = "test_solution.py") -> dict:
    """Run user code against test code in a container."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, solution_file), "w") as f:
            f.write(user_code)
        with open(os.path.join(tmpdir, test_file), "w") as f:
            f.write(test_code)

        return run_in_container(engine, image, test_command, tmpdir, timeout)
