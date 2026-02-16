# dont-rust-bro Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a coding practice popup that shows leetcode-style problems while AI agents are working, controlled via CLI + daemon architecture with Claude Code hooks.

**Architecture:** Hybrid CLI (`drb`) communicates with a long-running daemon process over Unix domain socket. The daemon owns a tkinter GUI window. Claude Code hooks call `drb show/hide/agent-stop` to control visibility. Reference counting tracks concurrent subagents.

**Tech Stack:** Python 3, tkinter (stdlib), pytest, Unix domain sockets, JSON for data/state.

---

### Task 1: Project scaffolding and problem pack data

**Files:**
- Create: `drb/__init__.py`
- Create: `drb/problems.py`
- Create: `packs/python/pack.json`
- Create: `packs/python/two_sum.json`
- Create: `packs/python/add_two_numbers.json`
- Create: `packs/python/reverse_string.json`
- Create: `packs/python/valid_palindrome.json`
- Create: `packs/python/fizzbuzz.json`
- Create: `tests/__init__.py`
- Create: `tests/test_problems.py`
- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```
pytest>=7.0
```

**Step 2: Create the Python problem pack**

Create `packs/python/pack.json`:
```json
{
  "name": "python",
  "language": "python",
  "version": "1.0.0",
  "description": "Python fundamentals and algorithms",
  "problems": ["two_sum", "add_two_numbers", "reverse_string", "valid_palindrome", "fizzbuzz"]
}
```

Create `packs/python/two_sum.json`:
```json
{
  "id": "two_sum",
  "title": "Two Sum",
  "difficulty": "easy",
  "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input has exactly one solution, and you may not use the same element twice.\n\nExample:\n  Input: nums = [2, 7, 11, 15], target = 9\n  Output: [0, 1]",
  "skeleton": "def two_sum(nums: list[int], target: int) -> list[int]:\n    # your code here\n    pass",
  "test_code": "from solution import two_sum\n\ndef test_basic():\n    assert sorted(two_sum([2, 7, 11, 15], 9)) == [0, 1]\n\ndef test_middle():\n    assert sorted(two_sum([3, 2, 4], 6)) == [1, 2]\n\ndef test_negative():\n    assert sorted(two_sum([-1, -2, -3, -4, -5], -8)) == [2, 4]\n"
}
```

Create `packs/python/add_two_numbers.json`:
```json
{
  "id": "add_two_numbers",
  "title": "Add Two Numbers",
  "difficulty": "easy",
  "description": "Write a function that takes two integers and returns their sum.\n\nExample:\n  Input: a = 2, b = 3\n  Output: 5",
  "skeleton": "def add(a: int, b: int) -> int:\n    # your code here\n    pass",
  "test_code": "from solution import add\n\ndef test_positive():\n    assert add(2, 3) == 5\n\ndef test_negative():\n    assert add(-1, -2) == -3\n\ndef test_zero():\n    assert add(0, 0) == 0\n\ndef test_mixed():\n    assert add(-5, 10) == 5\n"
}
```

Create `packs/python/reverse_string.json`:
```json
{
  "id": "reverse_string",
  "title": "Reverse String",
  "difficulty": "easy",
  "description": "Write a function that reverses a string in-place. The input is given as a list of characters.\n\nDo not allocate extra space for another array. You must do this by modifying the input list in-place with O(1) extra memory.\n\nExample:\n  Input: ['h', 'e', 'l', 'l', 'o']\n  Output: ['o', 'l', 'l', 'e', 'h']",
  "skeleton": "def reverse_string(s: list[str]) -> None:\n    # your code here - modify s in-place\n    pass",
  "test_code": "from solution import reverse_string\n\ndef test_hello():\n    s = ['h', 'e', 'l', 'l', 'o']\n    reverse_string(s)\n    assert s == ['o', 'l', 'l', 'e', 'h']\n\ndef test_hannah():\n    s = ['H', 'a', 'n', 'n', 'a', 'h']\n    reverse_string(s)\n    assert s == ['h', 'a', 'n', 'n', 'a', 'H']\n\ndef test_single():\n    s = ['a']\n    reverse_string(s)\n    assert s == ['a']\n"
}
```

Create `packs/python/valid_palindrome.json`:
```json
{
  "id": "valid_palindrome",
  "title": "Valid Palindrome",
  "difficulty": "easy",
  "description": "Given a string s, return True if it is a palindrome considering only alphanumeric characters and ignoring cases.\n\nExample:\n  Input: 'A man, a plan, a canal: Panama'\n  Output: True\n\n  Input: 'race a car'\n  Output: False",
  "skeleton": "def is_palindrome(s: str) -> bool:\n    # your code here\n    pass",
  "test_code": "from solution import is_palindrome\n\ndef test_panama():\n    assert is_palindrome('A man, a plan, a canal: Panama') is True\n\ndef test_race():\n    assert is_palindrome('race a car') is False\n\ndef test_empty():\n    assert is_palindrome(' ') is True\n\ndef test_symbols():\n    assert is_palindrome('.,') is True\n"
}
```

Create `packs/python/fizzbuzz.json`:
```json
{
  "id": "fizzbuzz",
  "title": "FizzBuzz",
  "difficulty": "easy",
  "description": "Given an integer n, return a list of strings where:\n- answer[i] == 'FizzBuzz' if i+1 is divisible by 3 and 5\n- answer[i] == 'Fizz' if i+1 is divisible by 3\n- answer[i] == 'Buzz' if i+1 is divisible by 5\n- answer[i] == str(i+1) otherwise\n\nExample:\n  Input: n = 5\n  Output: ['1', '2', 'Fizz', '4', 'Buzz']",
  "skeleton": "def fizzbuzz(n: int) -> list[str]:\n    # your code here\n    pass",
  "test_code": "from solution import fizzbuzz\n\ndef test_five():\n    assert fizzbuzz(5) == ['1', '2', 'Fizz', '4', 'Buzz']\n\ndef test_fifteen():\n    result = fizzbuzz(15)\n    assert result[14] == 'FizzBuzz'\n    assert result[2] == 'Fizz'\n    assert result[4] == 'Buzz'\n\ndef test_one():\n    assert fizzbuzz(1) == ['1']\n"
}
```

**Step 3: Write the failing test for problem loader**

Create `drb/__init__.py` (empty) and `tests/__init__.py` (empty).

Create `tests/test_problems.py`:
```python
import os
import pytest
from drb.problems import load_pack, load_problem, list_packs

PACKS_DIR = os.path.join(os.path.dirname(__file__), "..", "packs")


def test_list_packs():
    packs = list_packs(PACKS_DIR)
    assert "python" in packs


def test_load_pack():
    pack = load_pack(PACKS_DIR, "python")
    assert pack["name"] == "python"
    assert pack["language"] == "python"
    assert len(pack["problems"]) >= 5


def test_load_problem():
    problem = load_problem(PACKS_DIR, "python", "two_sum")
    assert problem["id"] == "two_sum"
    assert problem["title"] == "Two Sum"
    assert problem["difficulty"] == "easy"
    assert "skeleton" in problem
    assert "test_code" in problem


def test_load_problem_not_found():
    with pytest.raises(FileNotFoundError):
        load_problem(PACKS_DIR, "python", "nonexistent")


def test_load_pack_not_found():
    with pytest.raises(FileNotFoundError):
        load_pack(PACKS_DIR, "nonexistent")
```

**Step 4: Run test to verify it fails**

Run: `pytest tests/test_problems.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.problems'`

**Step 5: Write minimal implementation**

Create `drb/problems.py`:
```python
import json
import os


def list_packs(packs_dir: str) -> list[str]:
    """List available pack names."""
    if not os.path.isdir(packs_dir):
        return []
    return [
        d
        for d in os.listdir(packs_dir)
        if os.path.isfile(os.path.join(packs_dir, d, "pack.json"))
    ]


def load_pack(packs_dir: str, pack_name: str) -> dict:
    """Load a pack's metadata."""
    pack_path = os.path.join(packs_dir, pack_name, "pack.json")
    if not os.path.isfile(pack_path):
        raise FileNotFoundError(f"Pack not found: {pack_name}")
    with open(pack_path) as f:
        return json.load(f)


def load_problem(packs_dir: str, pack_name: str, problem_id: str) -> dict:
    """Load a single problem definition."""
    problem_path = os.path.join(packs_dir, pack_name, f"{problem_id}.json")
    if not os.path.isfile(problem_path):
        raise FileNotFoundError(f"Problem not found: {problem_id}")
    with open(problem_path) as f:
        return json.load(f)
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_problems.py -v`
Expected: All 5 tests PASS

**Step 7: Commit**

```bash
git add requirements.txt packs/ drb/ tests/
git commit -m "feat: add problem pack loader and initial Python problems"
```

---

### Task 2: State persistence

**Files:**
- Create: `drb/state.py`
- Create: `tests/test_state.py`

**Step 1: Write the failing test**

Create `tests/test_state.py`:
```python
import json
import os
import pytest
from drb.state import StateManager


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def test_initial_state(state_dir):
    sm = StateManager(state_dir)
    assert sm.active_pack == "python"
    assert sm.current_problem_index == 0
    assert sm.current_code == ""


def test_save_and_load(state_dir):
    sm = StateManager(state_dir)
    sm.active_pack = "python"
    sm.current_problem_index = 3
    sm.current_code = "def foo(): pass"
    sm.save()

    sm2 = StateManager(state_dir)
    assert sm2.active_pack == "python"
    assert sm2.current_problem_index == 3
    assert sm2.current_code == "def foo(): pass"


def test_clear_code(state_dir):
    sm = StateManager(state_dir)
    sm.current_code = "some code"
    sm.save()

    sm.clear_code()
    assert sm.current_code == ""

    sm2 = StateManager(state_dir)
    assert sm2.current_code == ""


def test_state_file_created(state_dir):
    sm = StateManager(state_dir)
    sm.save()
    assert os.path.isfile(os.path.join(state_dir, "state.json"))
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.state'`

**Step 3: Write minimal implementation**

Create `drb/state.py`:
```python
import json
import os


class StateManager:
    def __init__(self, state_dir: str):
        self._state_dir = state_dir
        self._state_file = os.path.join(state_dir, "state.json")
        self.active_pack = "python"
        self.current_problem_index = 0
        self.current_code = ""
        self._load()

    def _load(self):
        if os.path.isfile(self._state_file):
            with open(self._state_file) as f:
                data = json.load(f)
            self.active_pack = data.get("active_pack", "python")
            self.current_problem_index = data.get("current_problem_index", 0)
            self.current_code = data.get("current_code", "")

    def save(self):
        os.makedirs(self._state_dir, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(
                {
                    "active_pack": self.active_pack,
                    "current_problem_index": self.current_problem_index,
                    "current_code": self.current_code,
                },
                f,
                indent=2,
            )

    def clear_code(self):
        self.current_code = ""
        self.save()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add drb/state.py tests/test_state.py
git commit -m "feat: add state persistence manager"
```

---

### Task 3: Test runner

**Files:**
- Create: `drb/runner.py`
- Create: `tests/test_runner.py`

**Step 1: Write the failing test**

Create `tests/test_runner.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.runner'`

**Step 3: Write minimal implementation**

Create `drb/runner.py`:
```python
import os
import subprocess
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
                ["python", "-m", "pytest", test_path, "--tb=short", "-q"],
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_runner.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add drb/runner.py tests/test_runner.py
git commit -m "feat: add pytest-based test runner with timeout support"
```

---

### Task 4: Daemon with Unix socket IPC and agent reference counting

**Files:**
- Create: `drb/daemon.py`
- Create: `tests/test_daemon.py`

**Step 1: Write the failing test**

Create `tests/test_daemon.py`:
```python
import json
import os
import socket
import threading
import time
import pytest
from drb.daemon import DaemonServer


@pytest.fixture
def daemon_dir(tmp_path):
    return str(tmp_path)


def send_command(sock_path: str, command: str) -> dict:
    """Helper to send a command and get response."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(sock_path)
    client.sendall(json.dumps({"command": command}).encode() + b"\n")
    data = client.recv(4096)
    client.close()
    return json.loads(data.decode())


def test_show_increments_agent_count(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp = send_command(server.sock_path, "show")
        assert resp["status"] == "ok"
        assert resp["agents"] == 1

        resp = send_command(server.sock_path, "show")
        assert resp["agents"] == 2
    finally:
        server.shutdown()


def test_agent_stop_decrements(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 1

        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_agent_stop_does_not_go_negative(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_hide_resets_counter(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        resp = send_command(server.sock_path, "hide")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_pidfile_created(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        assert os.path.isfile(os.path.join(daemon_dir, "daemon.pid"))
    finally:
        server.shutdown()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_daemon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.daemon'`

**Step 3: Write minimal implementation**

Create `drb/daemon.py`:
```python
import json
import os
import signal
import socket
import threading


class DaemonServer:
    """Unix socket server that manages agent count and GUI visibility."""

    def __init__(self, state_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._headless = headless
        self._agent_count = 0
        self._lock = threading.Lock()
        self._running = False
        self._server_socket = None
        self._gui = None

        os.makedirs(state_dir, exist_ok=True)
        self.sock_path = os.path.join(state_dir, "daemon.sock")
        self._pid_path = os.path.join(state_dir, "daemon.pid")

    def _write_pidfile(self):
        with open(self._pid_path, "w") as f:
            f.write(str(os.getpid()))

    def _remove_pidfile(self):
        if os.path.isfile(self._pid_path):
            os.remove(self._pid_path)

    def _handle_command(self, command: str) -> dict:
        with self._lock:
            if command == "show":
                self._agent_count += 1
                if self._gui and not self._headless:
                    self._gui.show()
                return {"status": "ok", "agents": self._agent_count}
            elif command == "agent-stop":
                self._agent_count = max(0, self._agent_count - 1)
                if self._agent_count == 0 and self._gui and not self._headless:
                    self._gui.hide()
                return {"status": "ok", "agents": self._agent_count}
            elif command == "hide":
                self._agent_count = 0
                if self._gui and not self._headless:
                    self._gui.hide()
                return {"status": "ok", "agents": 0}
            elif command == "status":
                return {
                    "status": "ok",
                    "agents": self._agent_count,
                    "visible": self._gui.visible if self._gui else False,
                }
            elif command == "stop":
                self._running = False
                return {"status": "ok", "agents": 0}
            else:
                return {"status": "error", "message": f"Unknown command: {command}"}

    def _handle_client(self, conn: socket.socket):
        try:
            data = conn.recv(4096)
            if not data:
                return
            msg = json.loads(data.decode().strip())
            command = msg.get("command", "")
            response = self._handle_command(command)
            conn.sendall(json.dumps(response).encode() + b"\n")
        except (json.JSONDecodeError, KeyError):
            conn.sendall(json.dumps({"status": "error", "message": "Invalid message"}).encode() + b"\n")
        finally:
            conn.close()

    def set_gui(self, gui):
        self._gui = gui

    def serve_forever(self):
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_socket.bind(self.sock_path)
        self._server_socket.listen(5)
        self._server_socket.settimeout(0.5)
        self._running = True
        self._write_pidfile()

        try:
            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                    threading.Thread(
                        target=self._handle_client, args=(conn,), daemon=True
                    ).start()
                except socket.timeout:
                    continue
        finally:
            self._server_socket.close()
            if os.path.exists(self.sock_path):
                os.remove(self.sock_path)
            self._remove_pidfile()

    def shutdown(self):
        self._running = False
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_daemon.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add drb/daemon.py tests/test_daemon.py
git commit -m "feat: add daemon server with Unix socket IPC and agent counting"
```

---

### Task 5: CLI entry point

**Files:**
- Create: `drb/cli.py`
- Create: `bin/drb`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**

Create `tests/test_cli.py`:
```python
import json
import os
import socket
import threading
import time
import pytest
from unittest.mock import patch
from drb.cli import send_to_daemon, is_daemon_running


@pytest.fixture
def daemon_dir(tmp_path):
    return str(tmp_path)


def test_is_daemon_running_false(daemon_dir):
    assert is_daemon_running(daemon_dir) is False


def test_is_daemon_running_with_stale_pid(daemon_dir):
    pid_path = os.path.join(daemon_dir, "daemon.pid")
    with open(pid_path, "w") as f:
        f.write("99999999")
    assert is_daemon_running(daemon_dir) is False


def test_send_to_daemon(daemon_dir):
    """Start a minimal socket server and test send_to_daemon talks to it."""
    sock_path = os.path.join(daemon_dir, "daemon.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    def handle():
        conn, _ = server.accept()
        data = conn.recv(4096)
        conn.sendall(json.dumps({"status": "ok", "agents": 1}).encode() + b"\n")
        conn.close()

    t = threading.Thread(target=handle, daemon=True)
    t.start()

    resp = send_to_daemon(daemon_dir, "show")
    assert resp["status"] == "ok"
    assert resp["agents"] == 1
    server.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.cli'`

**Step 3: Write minimal implementation**

Create `drb/cli.py`:
```python
import json
import os
import signal
import socket
import subprocess
import sys


DEFAULT_STATE_DIR = os.path.expanduser("~/.dont-rust-bro")


def is_daemon_running(state_dir: str) -> bool:
    """Check if the daemon process is alive."""
    pid_path = os.path.join(state_dir, "daemon.pid")
    if not os.path.isfile(pid_path):
        return False
    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def send_to_daemon(state_dir: str, command: str) -> dict:
    """Send a command to the running daemon via Unix socket."""
    sock_path = os.path.join(state_dir, "daemon.sock")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(sock_path)
    client.sendall(json.dumps({"command": command}).encode() + b"\n")
    data = client.recv(4096)
    client.close()
    return json.loads(data.decode())


def launch_daemon(state_dir: str):
    """Launch the daemon as a background process."""
    drb_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.Popen(
        [sys.executable, "-m", "drb.daemon_main", "--state-dir", state_dir],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_daemon(state_dir: str):
    """Ensure the daemon is running, launching it if needed."""
    if not is_daemon_running(state_dir):
        launch_daemon(state_dir)
        import time
        for _ in range(20):
            time.sleep(0.1)
            if os.path.exists(os.path.join(state_dir, "daemon.sock")):
                break


def main(argv: list[str] | None = None):
    args = argv if argv is not None else sys.argv[1:]
    state_dir = DEFAULT_STATE_DIR

    if not args:
        print("Usage: drb <command>")
        print("Commands: show, hide, agent-stop, stop, status, update, packs")
        sys.exit(1)

    command = args[0]

    if command in ("show", "hide", "agent-stop", "status"):
        if command == "show":
            ensure_daemon(state_dir)
        try:
            resp = send_to_daemon(state_dir, command)
            if command == "status":
                print(f"Agents active: {resp.get('agents', 0)}")
                print(f"Visible: {resp.get('visible', False)}")
            elif command == "stop":
                print("Daemon stopped.")
        except (ConnectionRefusedError, FileNotFoundError):
            if command in ("hide", "agent-stop"):
                pass  # daemon not running, nothing to hide
            else:
                print(f"Daemon is not running.", file=sys.stderr)
                sys.exit(1)

    elif command == "stop":
        try:
            send_to_daemon(state_dir, "stop")
            print("Daemon stopped.")
        except (ConnectionRefusedError, FileNotFoundError):
            print("Daemon is not running.")

    elif command == "packs":
        sub = args[1] if len(args) > 1 else "list"
        packs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs")
        if not os.path.isdir(packs_dir):
            packs_dir = os.path.join(state_dir, "packs")

        from drb.problems import list_packs, load_pack
        from drb.state import StateManager

        if sub == "list":
            packs = list_packs(packs_dir)
            sm = StateManager(state_dir)
            for p in packs:
                marker = " (active)" if p == sm.active_pack else ""
                print(f"  {p}{marker}")
        elif sub == "use" and len(args) > 2:
            pack_name = args[2]
            packs = list_packs(packs_dir)
            if pack_name not in packs:
                print(f"Pack '{pack_name}' not found.", file=sys.stderr)
                sys.exit(1)
            sm = StateManager(state_dir)
            sm.active_pack = pack_name
            sm.current_problem_index = 0
            sm.clear_code()
            print(f"Switched to pack: {pack_name}")
        else:
            print("Usage: drb packs [list|use <name>]")

    elif command == "update":
        print("Pulling latest problems...")
        # Future: git pull or download from release
        print("Update not yet implemented. Pull the repo manually.")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Create `bin/drb`:
```bash
#!/usr/bin/env bash
# dont-rust-bro CLI entry point
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRB_ROOT="$(dirname "$SCRIPT_DIR")"

exec python3 -m drb.cli "$@"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add drb/cli.py bin/drb tests/test_cli.py
git commit -m "feat: add CLI entry point with daemon management"
```

---

### Task 6: Daemon main entry point (launches GUI + socket server)

**Files:**
- Create: `drb/daemon_main.py`

**Step 1: Write the daemon launcher**

Create `drb/daemon_main.py`:
```python
import argparse
import os
import sys
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", default=os.path.expanduser("~/.dont-rust-bro"))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    from drb.daemon import DaemonServer

    server = DaemonServer(args.state_dir, headless=args.headless)

    if args.headless:
        server.serve_forever()
    else:
        # Start socket server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # Run tkinter GUI in main thread (required by tkinter)
        from drb.gui import PracticeWindow

        packs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs")
        if not os.path.isdir(packs_dir):
            packs_dir = os.path.join(args.state_dir, "packs")

        gui = PracticeWindow(state_dir=args.state_dir, packs_dir=packs_dir)
        server.set_gui(gui)
        gui.run()

        # GUI exited, stop server
        server.shutdown()


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add drb/daemon_main.py
git commit -m "feat: add daemon main entry point"
```

---

### Task 7: Tkinter GUI window

**Files:**
- Create: `drb/gui.py`
- Create: `tests/test_gui.py`

This is the largest task. The GUI needs to:
- Display problem info (title, difficulty, description)
- Provide a code editor area
- Run tests and display results
- Navigate between problems
- Show/hide on command from daemon
- Persist state on edits and navigation

**Step 1: Write the failing test**

Create `tests/test_gui.py`:
```python
import json
import os
import pytest

# GUI tests are limited since tkinter needs a display.
# Test the non-GUI logic extracted into testable methods.

from drb.gui import PracticeWindow


@pytest.fixture
def setup_env(tmp_path):
    state_dir = str(tmp_path / "state")
    packs_dir = str(tmp_path / "packs" )
    os.makedirs(packs_dir)

    # Create a minimal pack
    python_dir = os.path.join(packs_dir, "python")
    os.makedirs(python_dir)

    with open(os.path.join(python_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "python",
            "language": "python",
            "version": "1.0.0",
            "description": "Test pack",
            "problems": ["add"]
        }, f)

    with open(os.path.join(python_dir, "add.json"), "w") as f:
        json.dump({
            "id": "add",
            "title": "Add",
            "difficulty": "easy",
            "description": "Add two numbers.",
            "skeleton": "def add(a, b):\n    pass",
            "test_code": "from solution import add\ndef test_add():\n    assert add(1,2)==3\n"
        }, f)

    return state_dir, packs_dir


def test_load_problem_data(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    problem = pw.current_problem
    assert problem["title"] == "Add"
    assert problem["difficulty"] == "easy"


def test_navigate_wraps(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    # Only 1 problem, next should wrap to 0
    pw.next_problem()
    assert pw.state.current_problem_index == 0


def test_show_hide_state(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.visible is False
    pw.show()
    assert pw.visible is True
    pw.hide()
    assert pw.visible is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'drb.gui'`

**Step 3: Write implementation**

Create `drb/gui.py`:
```python
import os
import threading
import tkinter as tk
from tkinter import font as tkfont

from drb.problems import load_pack, load_problem
from drb.runner import run_tests
from drb.state import StateManager


class PracticeWindow:
    def __init__(self, state_dir: str, packs_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._packs_dir = packs_dir
        self._headless = headless
        self.visible = False
        self._save_timer = None

        self.state = StateManager(state_dir)
        self._pack = load_pack(packs_dir, self.state.active_pack)
        self._problem_ids = self._pack["problems"]
        self._current_problem = None
        self._load_current_problem()

        if not headless:
            self._build_ui()

    def _load_current_problem(self):
        idx = self.state.current_problem_index
        if idx >= len(self._problem_ids):
            idx = 0
            self.state.current_problem_index = 0
        problem_id = self._problem_ids[idx]
        self._current_problem = load_problem(
            self._packs_dir, self.state.active_pack, problem_id
        )

    @property
    def current_problem(self) -> dict:
        return self._current_problem

    def _build_ui(self):
        self._root = tk.Tk()
        self._root.title("dont-rust-bro")
        self._root.geometry("700x650")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        mono = tkfont.Font(family="Menlo", size=13)
        desc_font = tkfont.Font(family="Helvetica", size=12)

        # Header
        header = tk.Frame(self._root, padx=10, pady=5)
        header.pack(fill=tk.X)

        self._title_label = tk.Label(header, text="", font=("Helvetica", 14, "bold"), anchor="w")
        self._title_label.pack(side=tk.LEFT)

        self._counter_label = tk.Label(header, text="", font=("Helvetica", 12), anchor="e")
        self._counter_label.pack(side=tk.RIGHT)

        self._difficulty_label = tk.Label(header, text="", font=("Helvetica", 12), anchor="e")
        self._difficulty_label.pack(side=tk.RIGHT, padx=(0, 10))

        # Description
        desc_frame = tk.Frame(self._root, padx=10, pady=5)
        desc_frame.pack(fill=tk.X)

        self._desc_text = tk.Text(desc_frame, height=6, wrap=tk.WORD, font=desc_font, state=tk.DISABLED, bg="#f5f5f5", relief=tk.FLAT)
        self._desc_text.pack(fill=tk.X)

        # Code editor
        editor_frame = tk.Frame(self._root, padx=10, pady=5)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(editor_frame, text="Solution:", font=("Helvetica", 11, "bold"), anchor="w").pack(fill=tk.X)

        self._code_text = tk.Text(editor_frame, font=mono, wrap=tk.NONE, undo=True, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self._code_text.pack(fill=tk.BOTH, expand=True)
        self._code_text.bind("<<Modified>>", self._on_code_modified)

        # Output
        output_frame = tk.Frame(self._root, padx=10, pady=5)
        output_frame.pack(fill=tk.X)

        tk.Label(output_frame, text="Output:", font=("Helvetica", 11, "bold"), anchor="w").pack(fill=tk.X)

        self._output_text = tk.Text(output_frame, height=6, font=mono, state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4", relief=tk.FLAT)
        self._output_text.pack(fill=tk.X)

        # Buttons
        btn_frame = tk.Frame(self._root, padx=10, pady=10)
        btn_frame.pack(fill=tk.X)

        self._prev_btn = tk.Button(btn_frame, text="◀ Prev", command=self.prev_problem)
        self._prev_btn.pack(side=tk.LEFT, padx=5)

        self._run_btn = tk.Button(btn_frame, text="Run ▶", command=self._run_tests, bg="#4CAF50", fg="white")
        self._run_btn.pack(side=tk.LEFT, padx=5)

        self._next_btn = tk.Button(btn_frame, text="Next ▶▶", command=self.next_problem)
        self._next_btn.pack(side=tk.LEFT, padx=5)

        self._refresh_ui()
        self._root.withdraw()

    def _refresh_ui(self):
        if self._headless:
            return

        p = self._current_problem
        idx = self.state.current_problem_index
        total = len(self._problem_ids)

        self._title_label.config(text=p["title"])
        self._difficulty_label.config(text=f"[{p['difficulty'].capitalize()}]")
        self._counter_label.config(text=f"{idx + 1}/{total}")

        self._desc_text.config(state=tk.NORMAL)
        self._desc_text.delete("1.0", tk.END)
        self._desc_text.insert("1.0", p["description"])
        self._desc_text.config(state=tk.DISABLED)

        self._code_text.delete("1.0", tk.END)
        code = self.state.current_code if self.state.current_code else p["skeleton"]
        self._code_text.insert("1.0", code)
        self._code_text.edit_modified(False)

        self._output_text.config(state=tk.NORMAL)
        self._output_text.delete("1.0", tk.END)
        self._output_text.config(state=tk.DISABLED)

    def _on_code_modified(self, event=None):
        if self._headless:
            return
        if not self._code_text.edit_modified():
            return
        self._code_text.edit_modified(False)
        if self._save_timer:
            self._root.after_cancel(self._save_timer)
        self._save_timer = self._root.after(1000, self._save_code)

    def _save_code(self):
        if self._headless:
            return
        self.state.current_code = self._code_text.get("1.0", tk.END).rstrip()
        self.state.save()

    def _run_tests(self):
        if self._headless:
            return
        self._run_btn.config(state=tk.DISABLED, text="Running...")
        user_code = self._code_text.get("1.0", tk.END)
        test_code = self._current_problem["test_code"]

        def run():
            result = run_tests(user_code, test_code)
            self._root.after(0, lambda: self._show_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, result: dict):
        self._output_text.config(state=tk.NORMAL)
        self._output_text.delete("1.0", tk.END)
        self._output_text.insert("1.0", result["output"])
        self._output_text.config(state=tk.DISABLED)
        self._run_btn.config(state=tk.NORMAL, text="Run ▶")

    def next_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index + 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()
        if not self._headless:
            self._refresh_ui()

    def prev_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index - 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()
        if not self._headless:
            self._refresh_ui()

    def show(self):
        self.visible = True
        if not self._headless:
            self._root.after(0, self._root.deiconify)

    def hide(self):
        self.visible = False
        if not self._headless:
            self._save_code()
            self._root.after(0, self._root.withdraw)

    def _on_close(self):
        self._save_code()
        self.hide()

    def run(self):
        if self._headless:
            return
        self._root.mainloop()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gui.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add drb/gui.py tests/test_gui.py
git commit -m "feat: add tkinter GUI with problem display, code editor, and test runner"
```

---

### Task 8: Hook configuration template

**Files:**
- Create: `hooks/claude-code.json`

**Step 1: Create hook template**

Create `hooks/claude-code.json`:
```json
{
  "hooks": {
    "SubagentStart": [
      {
        "type": "command",
        "command": "drb show"
      }
    ],
    "SubagentStop": [
      {
        "type": "command",
        "command": "drb agent-stop"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "drb hide"
      }
    ]
  }
}
```

**Step 2: Commit**

```bash
git add hooks/claude-code.json
git commit -m "feat: add Claude Code hook configuration template"
```

---

### Task 9: Installer script

**Files:**
- Create: `install.sh`

**Step 1: Write installer**

Create `install.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

DRB_HOME="${HOME}/.dont-rust-bro"
DRB_REPO="https://github.com/peterkarman1/dont-rust-bro.git"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[drb]${NC} $*"; }
warn()  { echo -e "${YELLOW}[drb]${NC} $*"; }
error() { echo -e "${RED}[drb]${NC} $*" >&2; }

# Parse flags
PACKS="python"
INSTALL_ALL=false

for arg in "$@"; do
    case "$arg" in
        --all) INSTALL_ALL=true ;;
        --packs=*) PACKS="${arg#--packs=}" ;;
    esac
done

# Check dependencies
if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found."
    exit 1
fi

if ! python3 -c "import tkinter" &>/dev/null; then
    error "tkinter is required. Install with: brew install python-tk@3.12"
    exit 1
fi

# Install or update
if [ -d "$DRB_HOME/.git" ]; then
    info "Updating existing installation..."
    git -C "$DRB_HOME" pull --quiet
else
    info "Installing dont-rust-bro to ${DRB_HOME}..."
    git clone --quiet "$DRB_REPO" "$DRB_HOME"
fi

# Ensure pytest is available
if ! python3 -c "import pytest" &>/dev/null; then
    warn "pytest not found. Installing..."
    python3 -m pip install --quiet pytest
fi

# Create bin symlink
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "${DRB_HOME}/bin/drb"
ln -sf "${DRB_HOME}/bin/drb" "${BIN_DIR}/drb"

# Check PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    warn "${BIN_DIR} is not in your PATH."
    warn "Add this to your shell profile:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Register Claude Code hooks
info "Registering Claude Code hooks..."
mkdir -p "$(dirname "$CLAUDE_SETTINGS")"

if [ -f "$CLAUDE_SETTINGS" ]; then
    # Merge hooks into existing settings using python
    python3 -c "
import json, sys

settings_path = '$CLAUDE_SETTINGS'
with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault('hooks', {})

drb_hooks = {
    'SubagentStart': {'type': 'command', 'command': '${BIN_DIR}/drb show'},
    'SubagentStop': {'type': 'command', 'command': '${BIN_DIR}/drb agent-stop'},
    'Stop': {'type': 'command', 'command': '${BIN_DIR}/drb hide'},
}

for event, hook in drb_hooks.items():
    event_hooks = hooks.setdefault(event, [])
    # Remove existing drb hooks
    event_hooks = [h for h in event_hooks if 'drb' not in h.get('command', '')]
    event_hooks.append(hook)
    hooks[event] = event_hooks

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
"
else
    python3 -c "
import json
settings = {
    'hooks': {
        'SubagentStart': [{'type': 'command', 'command': '${BIN_DIR}/drb show'}],
        'SubagentStop': [{'type': 'command', 'command': '${BIN_DIR}/drb agent-stop'}],
        'Stop': [{'type': 'command', 'command': '${BIN_DIR}/drb hide'}],
    }
}
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2)
"
fi

info "Installation complete!"
info ""
info "Commands:"
info "  drb status     - Check daemon status"
info "  drb packs list - List installed problem packs"
info "  drb update     - Pull latest problems"
info ""
info "The practice window will appear automatically when Claude agents are working."
```

**Step 2: Commit**

```bash
git add install.sh
git commit -m "feat: add curl-pipe-bash installer with hook registration"
```

---

### Task 10: Integration test — end-to-end headless

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

Create `tests/test_integration.py`:
```python
import json
import os
import socket
import threading
import time
import pytest

from drb.daemon import DaemonServer
from drb.gui import PracticeWindow


@pytest.fixture
def env(tmp_path):
    state_dir = str(tmp_path / "state")
    packs_dir = str(tmp_path / "packs")
    os.makedirs(packs_dir)

    python_dir = os.path.join(packs_dir, "python")
    os.makedirs(python_dir)

    with open(os.path.join(python_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "python", "language": "python",
            "version": "1.0.0", "description": "Test",
            "problems": ["add", "sub"]
        }, f)

    for pid, title, skel, test in [
        ("add", "Add", "def add(a,b):\n    pass", "from solution import add\ndef test_add():\n    assert add(1,2)==3\n"),
        ("sub", "Subtract", "def sub(a,b):\n    pass", "from solution import sub\ndef test_sub():\n    assert sub(5,3)==2\n"),
    ]:
        with open(os.path.join(python_dir, f"{pid}.json"), "w") as f:
            json.dump({
                "id": pid, "title": title, "difficulty": "easy",
                "description": f"{title} two numbers.",
                "skeleton": skel, "test_code": test
            }, f)

    return state_dir, packs_dir


def send_cmd(sock_path, cmd):
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(sock_path)
    c.sendall(json.dumps({"command": cmd}).encode() + b"\n")
    data = c.recv(4096)
    c.close()
    return json.loads(data.decode())


def test_full_lifecycle(env):
    state_dir, packs_dir = env

    server = DaemonServer(state_dir, headless=True)
    gui = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    server.set_gui(gui)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        # 3 subagents start
        resp = send_cmd(server.sock_path, "show")
        assert resp["agents"] == 1
        assert gui.visible is True

        send_cmd(server.sock_path, "show")
        send_cmd(server.sock_path, "show")

        # 1 finishes
        resp = send_cmd(server.sock_path, "agent-stop")
        assert resp["agents"] == 2
        assert gui.visible is True  # still visible

        # another finishes
        send_cmd(server.sock_path, "agent-stop")
        assert gui.visible is True  # still 1 agent

        # last finishes
        resp = send_cmd(server.sock_path, "agent-stop")
        assert resp["agents"] == 0
        assert gui.visible is False

        # Stop always resets
        send_cmd(server.sock_path, "show")
        send_cmd(server.sock_path, "show")
        resp = send_cmd(server.sock_path, "hide")
        assert resp["agents"] == 0
        assert gui.visible is False
    finally:
        server.shutdown()


def test_problem_navigation_persists(env):
    state_dir, packs_dir = env

    gui = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert gui.current_problem["id"] == "add"

    gui.next_problem()
    assert gui.current_problem["id"] == "sub"

    # Recreate — should restore to problem index 1
    gui2 = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert gui2.current_problem["id"] == "sub"
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: add integration tests for full lifecycle and navigation"
```

---

### Task 11: README and final polish

**Files:**
- Modify: `README.md`

**Step 1: Update README**

```markdown
# dont-rust-bro

Don't let your skills get rusty. Practice coding while your agent does the real work.

## What is this?

A coding practice popup that shows leetcode-style problems while AI coding agents are working. Instead of watching your agent think, sharpen your skills with bite-sized coding challenges.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/peterkarman1/dont-rust-bro/main/install.sh | bash
```

## How it works

When Claude Code spawns subagents, a practice window pops up with a coding problem. Write your solution and click Run to test it. The window automatically hides when Claude is ready for your input.

## Commands

| Command | Description |
|---------|-------------|
| `drb status` | Check daemon status |
| `drb packs list` | List installed problem packs |
| `drb packs use <name>` | Switch active pack |
| `drb update` | Pull latest problems |
| `drb stop` | Stop the daemon |

## Problem Packs

- **python** — Python fundamentals and algorithms (default)
- More coming soon (JavaScript, Rust, Go...)
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with install instructions and usage"
```
