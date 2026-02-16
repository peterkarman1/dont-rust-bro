# Containerized Runner + pywebview UI

**Date:** 2026-02-16
**Status:** Approved

## Problem

The tkinter GUI crashes on macOS 26 because the system Python 3.9.6 ships with
Tcl/Tk 8.5, which is incompatible with the new OS. Beyond fixing this one issue,
the current architecture ties test execution to the host's installed tools, making
multi-language support (JS, Rust, Go) painful.

## Solution

Two changes:

1. **Replace tkinter with pywebview** — renders HTML/CSS/JS in a native OS window
   (WebKit on macOS, Edge on Windows, GTK/WebKit on Linux). `pip install pywebview`.
2. **Run tests in ephemeral containers** — `docker run --rm` (or podman) with
   per-language images. No host dependencies beyond docker/podman.

## Architecture

```
User sends prompt --> UserPromptSubmit hook --> `drb show`
                                                    |
                                              ensure_daemon()
                                                    |
                                    +---------------+---------------+
                                    |         DaemonServer          |
                                    |   (Unix socket, daemon.py)    |
                                    |                               |
                                    |   show  -> gui.show()         |
                                    |   hide  -> gui.hide()         |
                                    |   stop  -> shutdown           |
                                    +---------------+---------------+
                                                    |
                                    +---------------+---------------+
                                    |       PracticeWindow          |
                                    |  (pywebview + HTML/CSS/JS)    |
                                    |                               |
                                    |   Problem display + editor    |
                                    |   Run button -> runner.py     |
                                    |   State persistence           |
                                    +---------------+---------------+
                                                    |
                                              Run Tests
                                                    |
                                    +---------------+---------------+
                                    |    Container Runner            |
                                    |  docker/podman run --rm       |
                                    |                               |
                                    |  Mount: solution.py + tests   |
                                    |  Image: per-language minimal  |
                                    |  e.g. python:3.12-slim        |
                                    +-------------------------------+
```

## Component Details

### 1. Container Runner (`drb/container.py`)

Replaces `drb/deps.py`. Three functions:

- `detect_engine() -> str` — returns "podman" or "docker" (prefers podman)
- `ensure_image(engine, image)` — pulls image if not present locally
- `run_in_container(engine, image, test_command, tmpdir, timeout) -> dict` — core exec

Runner invocation:

```python
subprocess.run(
    [engine, "run", "--rm", "--network=none",
     "-v", f"{tmpdir}:/work", "-w", "/work",
     "--memory=256m", "--cpus=1",
     image, "sh", "-c", test_command],
    capture_output=True, text=True, timeout=timeout
)
```

Key flags:
- `--network=none` — sandbox user code from network
- `--memory=256m --cpus=1` — resource limits
- `--rm` — ephemeral, removed after each run

### 2. pywebview GUI (`drb/gui.py` + `drb/ui/index.html`)

Python API class exposed to JS via `window.pywebview.api`:

```python
class Api:
    def run_tests(self, code)   # called from JS "Run" button
    def get_problem(self)       # returns current problem JSON
    def next_problem(self)
    def prev_problem(self)
    def save_code(self, code)
```

JS calls: `await window.pywebview.api.run_tests(code)`

Single `drb/ui/index.html` with embedded CSS/JS. Code editor as styled
textarea (can upgrade to CodeMirror later). Show/hide via pywebview's
native `window.show()` / `window.hide()`.

### 3. pack.json Changes

Before:
```json
{
  "name": "python",
  "dependencies": {
    "executables": ["python3"],
    "python_modules": ["pytest"]
  }
}
```

After:
```json
{
  "name": "python",
  "image": "python:3.12-slim",
  "test_command": "pip install pytest -q && python -m pytest test_solution.py --tb=short -q",
  "problems": [...]
}
```

No more host dependency declarations. The container image has everything.

### 4. Install Changes (`install.sh`)

- Detect docker or podman on PATH (error if neither found)
- Store engine in `~/.dont-rust-bro/config.json`: `{"engine": "podman"}`
- `pip3 install pywebview` for the GUI
- Pull default pack image: `$engine pull python:3.12-slim`
- Remove tkinter check entirely
- Remove dependency checking logic

### 5. CLI Changes (`drb/cli.py`)

- `packs use <name>`: calls `ensure_image()` instead of `check_pack_deps()`
- Config loading: reads engine from `config.json`
- Everything else stays the same

## What Gets Removed

- `drb/deps.py` — replaced by `drb/container.py`
- `tests/test_deps.py` — replaced by `tests/test_container.py`
- tkinter import and all Tk-related code in `gui.py`
- `pack.json` `dependencies` field
- tkinter check in `install.sh`

## What Stays the Same

- Daemon architecture (daemon.py + Unix socket IPC)
- CLI structure (same commands)
- State management (state.py)
- Problem loading (problems.py)
- Hook system (UserPromptSubmit/Stop)
- All 35 problem JSON files (skeleton + test_code format unchanged)

## Future: Adding JavaScript Pack

With this architecture, adding JS is trivial:

```json
{
  "name": "javascript",
  "image": "node:22-slim",
  "test_command": "npm install -g jest --silent && jest test_solution.js --no-cache",
  "problems": [...]
}
```

No host-side Node.js required.
