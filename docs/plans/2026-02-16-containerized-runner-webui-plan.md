# Containerized Runner + pywebview UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace tkinter with pywebview and run tests in ephemeral docker/podman containers.

**Architecture:** pywebview renders HTML/CSS/JS in a native OS window. A new `container.py` module handles docker/podman detection and ephemeral container execution. `runner.py` delegates to containers instead of local subprocess. `pack.json` declares `image` and `test_command` instead of host dependencies.

**Tech Stack:** Python 3.9+, pywebview, docker/podman, HTML/CSS/JS

**Design doc:** `docs/plans/2026-02-16-containerized-runner-webui-design.md`

---

### Task 1: Container module — detect engine

**Files:**
- Create: `drb/container.py`
- Create: `tests/test_container.py`

**Step 1: Write the failing test**

In `tests/test_container.py`:

```python
import pytest
from unittest.mock import patch
from drb.container import detect_engine


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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_container.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'drb.container'`

**Step 3: Write minimal implementation**

In `drb/container.py`:

```python
import shutil


def detect_engine() -> str:
    """Detect container engine. Prefers podman over docker."""
    for engine in ("podman", "docker"):
        if shutil.which(engine):
            return engine
    raise RuntimeError(
        "No container engine found. Install docker or podman."
    )
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_container.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add drb/container.py tests/test_container.py
git commit -m "feat: add container engine detection"
```

---

### Task 2: Container module — ensure_image

**Files:**
- Modify: `drb/container.py`
- Modify: `tests/test_container.py`

**Step 1: Write the failing test**

Append to `tests/test_container.py`:

```python
from drb.container import ensure_image


def test_ensure_image_already_present(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = type("R", (), {"returncode": 0})()
        ensure_image("docker", "python:3.12-slim")
        # inspect called, pull NOT called
        assert mock_run.call_count == 1
        assert "inspect" in mock_run.call_args[0][0]


def test_ensure_image_pulls_missing(tmp_path):
    def side_effect(cmd, **kwargs):
        r = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if "inspect" in cmd:
            r.returncode = 1
        return r

    with patch("subprocess.run", side_effect=side_effect):
        ensure_image("docker", "python:3.12-slim")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_container.py::test_ensure_image_already_present -v`
Expected: FAIL — `ImportError`

**Step 3: Write minimal implementation**

Append to `drb/container.py`:

```python
import subprocess


def ensure_image(engine: str, image: str):
    """Pull image if not already present locally."""
    result = subprocess.run(
        [engine, "image", "inspect", image],
        capture_output=True, timeout=10,
    )
    if result.returncode != 0:
        subprocess.run(
            [engine, "pull", image],
            capture_output=True, timeout=300,
        )
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_container.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add drb/container.py tests/test_container.py
git commit -m "feat: add container image pull support"
```

---

### Task 3: Container module — run_in_container

**Files:**
- Modify: `drb/container.py`
- Modify: `tests/test_container.py`

**Step 1: Write the failing test**

Append to `tests/test_container.py`:

```python
import os
from drb.container import run_in_container


def test_run_in_container_passing(tmp_path):
    """Mock subprocess to simulate passing test run."""
    def mock_run(cmd, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": "1 passed",
            "stderr": "",
        })()

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=10)
    assert result["passed"] is True
    assert "1 passed" in result["output"]


def test_run_in_container_failing(tmp_path):
    def mock_run(cmd, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "FAILED",
            "stderr": "",
        })()

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=10)
    assert result["passed"] is False


def test_run_in_container_timeout(tmp_path):
    def mock_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=2)

    with patch("subprocess.run", side_effect=mock_run):
        result = run_in_container("docker", "python:3.12-slim",
                                  "pytest test_solution.py", str(tmp_path), timeout=2)
    assert result["passed"] is False
    assert "timeout" in result["output"].lower()


def test_run_in_container_command_structure(tmp_path):
    """Verify the docker run command has correct flags."""
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_container.py::test_run_in_container_passing -v`
Expected: FAIL — `ImportError`

**Step 3: Write minimal implementation**

Append to `drb/container.py`:

```python
def run_in_container(engine: str, image: str, test_command: str,
                     work_dir: str, timeout: int = 10) -> dict:
    """Run test command in an ephemeral container.

    Mounts work_dir to /work inside the container.
    Returns dict with 'passed' (bool) and 'output' (str).
    """
    cmd = [
        engine, "run", "--rm", "--network=none",
        "-v", f"{work_dir}:/work", "-w", "/work",
        "--memory=256m", "--cpus=1",
        image, "sh", "-c", test_command,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = f"Timeout: tests did not complete within {timeout} seconds."
        passed = False

    return {"passed": passed, "output": output.strip()}
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_container.py -v`
Expected: 9 passed

**Step 5: Commit**

```bash
git add drb/container.py tests/test_container.py
git commit -m "feat: add containerized test execution"
```

---

### Task 4: Update runner.py to use containers

**Files:**
- Modify: `drb/runner.py`
- Modify: `tests/test_runner.py`

**Step 1: Write the failing tests**

Replace `tests/test_runner.py` entirely:

```python
import subprocess
import pytest
from unittest.mock import patch
from drb.runner import run_tests


def test_passing_solution():
    """Mock container run for a passing solution."""
    def mock_run(cmd, **kwargs):
        return type("R", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()

    with patch("drb.container.run_in_container") as mock_container:
        mock_container.return_value = {"passed": True, "output": "1 passed"}
        result = run_tests("def add(a,b): return a+b", "from solution import add\ndef test(): assert add(1,2)==3",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q")
    assert result["passed"] is True
    assert "1 passed" in result["output"]


def test_failing_solution():
    with patch("drb.container.run_in_container") as mock_container:
        mock_container.return_value = {"passed": False, "output": "FAILED"}
        result = run_tests("def add(a,b): return 0", "from solution import add\ndef test(): assert add(1,2)==3",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q")
    assert result["passed"] is False


def test_timeout():
    with patch("drb.container.run_in_container") as mock_container:
        mock_container.return_value = {"passed": False, "output": "Timeout: tests did not complete within 2 seconds."}
        result = run_tests("import time\ndef slow(): time.sleep(30)", "from solution import slow\ndef test(): slow()",
                           engine="docker", image="python:3.12-slim",
                           test_command="pytest test_solution.py --tb=short -q",
                           timeout=2)
    assert result["passed"] is False
    assert "timeout" in result["output"].lower()


def test_files_written_to_tmpdir():
    """Verify solution.py and test_solution.py are written before container runs."""
    import os
    written_dir = [None]

    def mock_run_in_container(engine, image, test_command, work_dir, timeout=10):
        written_dir[0] = work_dir
        assert os.path.isfile(os.path.join(work_dir, "solution.py"))
        assert os.path.isfile(os.path.join(work_dir, "test_solution.py"))
        return {"passed": True, "output": "ok"}

    with patch("drb.container.run_in_container", side_effect=mock_run_in_container):
        run_tests("code", "test_code", engine="docker", image="img",
                  test_command="pytest test_solution.py")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: FAIL — `run_tests() got unexpected keyword argument 'engine'`

**Step 3: Rewrite implementation**

Replace `drb/runner.py`:

```python
import os
import tempfile

from drb.container import run_in_container


def run_tests(user_code: str, test_code: str, engine: str, image: str,
              test_command: str, timeout: int = 10) -> dict:
    """Run user code against test code in a container.

    Writes solution.py and test_solution.py to a temp dir,
    mounts it into a container, and runs the test command.
    Returns dict with 'passed' (bool) and 'output' (str).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "solution.py"), "w") as f:
            f.write(user_code)
        with open(os.path.join(tmpdir, "test_solution.py"), "w") as f:
            f.write(test_code)

        return run_in_container(engine, image, test_command, tmpdir, timeout)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add drb/runner.py tests/test_runner.py
git commit -m "feat: runner delegates to container execution"
```

---

### Task 5: Config module for engine storage

**Files:**
- Modify: `drb/container.py`
- Modify: `tests/test_container.py`

**Step 1: Write the failing test**

Append to `tests/test_container.py`:

```python
import json
from drb.container import load_config, save_config


def test_save_and_load_config(tmp_path):
    config_path = str(tmp_path / "config.json")
    save_config(config_path, {"engine": "podman"})
    config = load_config(config_path)
    assert config["engine"] == "podman"


def test_load_config_missing(tmp_path):
    config_path = str(tmp_path / "config.json")
    config = load_config(config_path)
    assert config == {}
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_container.py::test_save_and_load_config -v`
Expected: FAIL — `ImportError`

**Step 3: Write minimal implementation**

Add to `drb/container.py`:

```python
import json
import os


def load_config(config_path: str) -> dict:
    """Load container config from JSON file."""
    if not os.path.isfile(config_path):
        return {}
    with open(config_path) as f:
        return json.load(f)


def save_config(config_path: str, config: dict):
    """Save container config to JSON file."""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_container.py -v`
Expected: 11 passed

**Step 5: Commit**

```bash
git add drb/container.py tests/test_container.py
git commit -m "feat: add container config persistence"
```

---

### Task 6: Update pack.json with image and test_command

**Files:**
- Modify: `packs/python/pack.json`

**Step 1: Update pack.json**

Replace `dependencies` field with `image` and `test_command`:

```json
{
  "name": "python",
  "language": "python",
  "version": "1.0.0",
  "description": "Python fundamentals and algorithms",
  "image": "python:3.12-slim",
  "test_command": "pip install pytest -q 2>/dev/null && python -m pytest test_solution.py --tb=short -q",
  "problems": [...]
}
```

**Step 2: Update tests that reference pack.json dependencies**

Modify `tests/test_cli.py::test_packs_use_rejects_missing_deps` — this test no longer applies. Replace it with a test that verifies `packs use` calls `ensure_image`. (Done in Task 8.)

**Step 3: Commit**

```bash
git add packs/python/pack.json
git commit -m "feat: pack.json uses container image instead of host dependencies"
```

---

### Task 7: Rewrite gui.py with pywebview

**Files:**
- Rewrite: `drb/gui.py`
- Create: `drb/ui/index.html`
- Modify: `tests/test_gui.py`

**Step 1: Write the failing tests**

Replace `tests/test_gui.py`:

```python
import json
import os
import pytest

from drb.gui import PracticeWindow


@pytest.fixture
def setup_env(tmp_path):
    state_dir = str(tmp_path / "state")
    packs_dir = str(tmp_path / "packs")
    os.makedirs(packs_dir)

    python_dir = os.path.join(packs_dir, "python")
    os.makedirs(python_dir)

    with open(os.path.join(python_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "python", "language": "python",
            "version": "1.0.0", "description": "Test pack",
            "image": "python:3.12-slim",
            "test_command": "pytest test_solution.py --tb=short -q",
            "problems": ["add"],
        }, f)

    with open(os.path.join(python_dir, "add.json"), "w") as f:
        json.dump({
            "id": "add", "title": "Add", "difficulty": "easy",
            "description": "Add two numbers.",
            "skeleton": "def add(a, b):\n    pass",
            "test_code": "from solution import add\ndef test_add():\n    assert add(1,2)==3\n",
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


def test_api_get_problem(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    api = pw.api
    problem = api.get_problem()
    assert problem["title"] == "Add"
    assert problem["skeleton"] == "def add(a, b):\n    pass"


def test_api_save_code(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    api = pw.api
    api.save_code("def add(a,b): return a+b")
    assert pw.state.current_code == "def add(a,b): return a+b"
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gui.py -v`
Expected: FAIL — `PracticeWindow` no longer has expected API

**Step 3: Write pywebview-based gui.py**

Replace `drb/gui.py`:

```python
import json
import os
import threading

from drb.problems import load_pack, load_problem
from drb.state import StateManager


class Api:
    """JavaScript-callable API exposed via pywebview."""

    def __init__(self, window_ref):
        self._pw = window_ref

    def get_problem(self) -> dict:
        p = self._pw.current_problem
        idx = self._pw.state.current_problem_index
        total = len(self._pw._problem_ids)
        return {
            "title": p["title"],
            "difficulty": p["difficulty"],
            "description": p["description"],
            "skeleton": p["skeleton"],
            "counter": f"{idx + 1}/{total}",
            "code": self._pw.state.current_code or p["skeleton"],
        }

    def save_code(self, code: str):
        self._pw.state.current_code = code.rstrip()
        self._pw.state.save()

    def next_problem(self) -> dict:
        self._pw.next_problem()
        return self.get_problem()

    def prev_problem(self) -> dict:
        self._pw.prev_problem()
        return self.get_problem()

    def run_tests(self, code: str) -> dict:
        from drb.runner import run_tests
        from drb.container import load_config

        self.save_code(code)
        config_path = os.path.join(self._pw._state_dir, "config.json")
        config = load_config(config_path)
        engine = config.get("engine", "docker")
        pack = self._pw._pack
        image = pack.get("image", "python:3.12-slim")
        test_command = pack.get("test_command", "pytest test_solution.py --tb=short -q")

        return run_tests(code, self._pw.current_problem["test_code"],
                         engine=engine, image=image,
                         test_command=test_command)


class PracticeWindow:
    def __init__(self, state_dir: str, packs_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._packs_dir = packs_dir
        self._headless = headless
        self.visible = False

        self.state = StateManager(state_dir)
        self._pack = load_pack(packs_dir, self.state.active_pack)
        self._problem_ids = self._pack["problems"]
        self._current_problem = None
        self._load_current_problem()

        self.api = Api(self)
        self._window = None

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

    def next_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index + 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()

    def prev_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index - 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()

    def show(self):
        self.visible = True
        if self._window and not self._headless:
            self._window.show()

    def hide(self):
        self.visible = False
        if self._window and not self._headless:
            self._window.hide()

    def run(self):
        if self._headless:
            return
        import webview
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
        self._window = webview.create_window(
            "dont-rust-bro", ui_path,
            js_api=self.api,
            width=720, height=680,
            hidden=True,
        )
        webview.start()
```

**Step 4: Create the HTML UI**

Create `drb/ui/index.html` — a single HTML file with embedded CSS and JS that:
- Calls `window.pywebview.api.get_problem()` on load to populate UI
- Has a description area, code textarea, output area, and Prev/Run/Next buttons
- Run button calls `window.pywebview.api.run_tests(code)` and displays result
- Dark theme code editor, clean layout
- Auto-saves code on changes via `window.pywebview.api.save_code(code)`

(Full HTML content to be written during implementation — it's a single standalone file with ~150 lines of HTML/CSS/JS.)

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gui.py -v`
Expected: 6 passed

**Step 6: Commit**

```bash
git add drb/gui.py drb/ui/index.html tests/test_gui.py
git commit -m "feat: replace tkinter with pywebview + HTML UI"
```

---

### Task 8: Update cli.py — remove deps, add container support

**Files:**
- Modify: `drb/cli.py`
- Modify: `tests/test_cli.py`
- Delete: `drb/deps.py`
- Delete: `tests/test_deps.py`

**Step 1: Write failing test for packs use with container**

Replace `test_packs_use_rejects_missing_deps` in `tests/test_cli.py`:

```python
def test_packs_use_pulls_image(tmp_path):
    """Test that packs use calls ensure_image for the pack's container image."""
    packs_dir = str(tmp_path / "packs")
    pack_dir = os.path.join(packs_dir, "testpack")
    os.makedirs(pack_dir)

    with open(os.path.join(pack_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "testpack", "language": "python",
            "version": "1.0.0", "description": "Test",
            "image": "python:3.12-slim",
            "test_command": "pytest test_solution.py",
            "problems": [],
        }, f)

    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump({"engine": "docker"}, f)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir), \
         patch("drb.container.ensure_image") as mock_ensure:
        main(["packs", "use", "testpack"])

    mock_ensure.assert_called_once_with("docker", "python:3.12-slim")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli.py::test_packs_use_pulls_image -v`
Expected: FAIL

**Step 3: Update cli.py**

In `drb/cli.py`, replace the `packs use` section:
- Remove `from drb.deps import check_pack_deps` import
- Add `from drb.container import ensure_image, load_config`
- After validating pack exists, read engine from config, call `ensure_image(engine, pack["image"])`
- Remove `dependencies` error checking

Also update the import/reference in uninstall — no deps changes needed there.

**Step 4: Delete old deps module**

```bash
rm drb/deps.py tests/test_deps.py
```

**Step 5: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add drb/cli.py tests/test_cli.py
git rm drb/deps.py tests/test_deps.py
git commit -m "feat: cli uses container engine, remove host dependency checks"
```

---

### Task 9: Update daemon_main.py

**Files:**
- Modify: `drb/daemon_main.py`

**Step 1: Update daemon_main.py**

The only change is removing the tkinter import path — pywebview is now used.
The structure stays the same: server thread + GUI on main thread.

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
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        from drb.gui import PracticeWindow

        packs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs")
        if not os.path.isdir(packs_dir):
            packs_dir = os.path.join(args.state_dir, "packs")

        gui = PracticeWindow(state_dir=args.state_dir, packs_dir=packs_dir)
        server.set_gui(gui)
        gui.run()

        server.shutdown()


if __name__ == "__main__":
    main()
```

**Step 2: Run integration tests**

Run: `python3 -m pytest tests/test_integration.py -v`
Expected: All pass (integration tests use headless=True, no pywebview needed)

**Step 3: Commit**

```bash
git add drb/daemon_main.py
git commit -m "refactor: daemon_main uses pywebview gui"
```

---

### Task 10: Update install.sh

**Files:**
- Modify: `install.sh`

**Step 1: Rewrite install.sh**

Key changes:
- Remove tkinter check
- Add docker/podman detection
- Save engine to `config.json`
- `pip3 install pywebview`
- Pull default pack image
- Keep hook registration as-is

```bash
#!/usr/bin/env bash
set -euo pipefail

DRB_HOME="${HOME}/.dont-rust-bro"
DRB_REPO="https://github.com/peterkarman1/dont-rust-bro.git"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[drb]${NC} $*"; }
warn()  { echo -e "${YELLOW}[drb]${NC} $*"; }
error() { echo -e "${RED}[drb]${NC} $*" >&2; }

# Check dependencies
if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found."
    exit 1
fi

# Detect container engine
ENGINE=""
if command -v podman &>/dev/null; then
    ENGINE="podman"
elif command -v docker &>/dev/null; then
    ENGINE="docker"
else
    error "docker or podman is required but neither was found."
    exit 1
fi
info "Using container engine: ${ENGINE}"

# Clean install
if [ -d "$DRB_HOME" ]; then
    info "Removing existing installation..."
    rm -rf "$DRB_HOME"
fi

info "Installing dont-rust-bro to ${DRB_HOME}..."
git clone --quiet "$DRB_REPO" "$DRB_HOME"

# Save engine config
python3 -c "
import json, os
config_path = '$DRB_HOME/config.json'
with open(config_path, 'w') as f:
    json.dump({'engine': '$ENGINE'}, f, indent=2)
"

# Install pywebview
info "Installing pywebview..."
pip3 install --quiet pywebview

# Pull default container image
DEFAULT_IMAGE=$(python3 -c "
import json
with open('$DRB_HOME/packs/python/pack.json') as f:
    print(json.load(f)['image'])
")
info "Pulling container image: ${DEFAULT_IMAGE}..."
$ENGINE pull "$DEFAULT_IMAGE"

# Create bin symlink
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "${DRB_HOME}/bin/drb"
ln -sf "${DRB_HOME}/bin/drb" "${BIN_DIR}/drb"

if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    warn "${BIN_DIR} is not in your PATH."
    warn "Add: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Register Claude Code hooks (unchanged)
# ... (keep existing hook registration code)

info "Installation complete!"
info ""
info "Container engine: ${ENGINE}"
info "Commands:"
info "  drb status     - Check daemon status"
info "  drb packs list - List installed problem packs"
info "  drb uninstall  - Remove everything"
```

**Step 2: Commit**

```bash
git add install.sh
git commit -m "feat: install detects docker/podman, installs pywebview, pulls images"
```

---

### Task 11: Update integration tests for new pack format

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Update fixtures to include image/test_command**

Add `"image": "python:3.12-slim"` and `"test_command": "pytest test_solution.py --tb=short -q"` to the pack.json fixture in `tests/test_integration.py`.

**Step 2: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: update integration fixtures for container pack format"
```

---

### Task 12: Update CLAUDE.md and docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/index.html`

**Step 1: Update CLAUDE.md**

- Replace tkinter references with pywebview
- Update architecture diagram
- Update key modules table: `drb/container.py`, remove `drb/deps.py`
- Note docker/podman requirement
- Update `pack.json` dependency model description

**Step 2: Update README.md**

- Prerequisites: docker or podman (not tkinter)
- Update "How it works" section

**Step 3: Update docs/index.html**

- Update feature cards and tech description

**Step 4: Commit**

```bash
git add CLAUDE.md README.md docs/index.html
git commit -m "docs: update for pywebview + container architecture"
```

---

### Task 13: Final integration test — end to end

**Step 1: Run full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Manual smoke test**

```bash
drb show   # should open pywebview window
drb hide   # should hide it
drb stop   # should stop daemon
```

**Step 3: Push**

```bash
git push
```
