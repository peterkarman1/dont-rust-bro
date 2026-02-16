# dont-rust-bro Design Document

## Overview

A coding practice tool that pops up a tkinter window with leetcode-style problems while AI coding agents are working. Users practice coding during agent wait time, keeping skills sharp instead of idle-scrolling.

## Architecture: Hybrid CLI + Daemon

A unified `drb` CLI serves as both the hook entry point and user command interface. A long-running daemon process owns the tkinter GUI window. Hooks and user commands communicate with the daemon via Unix domain socket.

### Core Components

```
hooks (claude-code) → drb CLI → Unix socket → daemon (tkinter GUI)
                                                  ├── problem loader
                                                  ├── test runner (pytest subprocess)
                                                  └── state manager
```

## Agent Lifecycle & Reference Counting

The popup must only be visible while Claude is actively working, and must handle multiple concurrent subagents.

- **SubagentStart** hook → `drb show` → daemon increments active agent counter, shows window
- **SubagentStop** hook → `drb agent-stop` → daemon decrements counter, hides window when counter reaches 0
- **Stop** hook → `drb hide` → force-hides window and resets counter to 0 (definitive "waiting for user" signal)

Only one popup window is ever open. If the daemon is already running, `drb show` reuses it.

## GUI Window (tkinter)

### Layout

```
┌─────────────────────────────────────────────┐
│  Problem: Two Sum                [Easy] 1/20│
│─────────────────────────────────────────────│
│  Given an array of integers nums and an     │
│  integer target, return indices of the two  │
│  numbers such that they add up to target.   │
│─────────────────────────────────────────────│
│  def two_sum(nums, target):                 │
│      # your code here                       │
│      █                                      │
│                                             │
│                                             │
│─────────────────────────────────────────────│
│  Output:                                    │
│  (test results appear here)                 │
│─────────────────────────────────────────────│
│  [◀ Prev]  [Run ▶]  [Next ▶▶]  [Skip]     │
└─────────────────────────────────────────────┘
```

### Behavior

- Text editor area with syntax-appropriate font (monospace)
- Run button executes user code against test cases via pytest subprocess
- Output panel shows pass/fail results and error messages
- Prev/Next navigate between problems in the active pack
- Window hides (not destroys) on agent stop — preserves state for re-show
- Window position remembered across show/hide cycles

## Problem Packs

### Structure

```
packs/
└── python/
    ├── pack.json
    ├── two_sum.json
    ├── add.json
    └── ...
```

### pack.json

```json
{
  "name": "python",
  "language": "python",
  "version": "1.0.0",
  "description": "Python fundamentals and algorithms",
  "problems": ["two_sum", "add", "reverse_string", "..."]
}
```

### Problem file (e.g., two_sum.json)

```json
{
  "id": "two_sum",
  "title": "Two Sum",
  "difficulty": "easy",
  "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input has exactly one solution, and you may not use the same element twice.",
  "skeleton": "def two_sum(nums: list[int], target: int) -> list[int]:\n    # your code here\n    pass",
  "test_cases": [
    {
      "input": {"nums": [2, 7, 11, 15], "target": 9},
      "expected": [0, 1]
    },
    {
      "input": {"nums": [3, 2, 4], "target": 6},
      "expected": [1, 2]
    }
  ],
  "test_code": "import pytest\nfrom solution import two_sum\n\ndef test_basic():\n    assert sorted(two_sum([2, 7, 11, 15], 9)) == [0, 1]\n\ndef test_middle():\n    assert sorted(two_sum([3, 2, 4], 6)) == [1, 2]\n"
}
```

### Adding new language packs

Create a new directory under `packs/` (e.g., `packs/javascript/`) with the same structure. The test runner dispatches based on the pack's `language` field (pytest for Python, node/jest for JavaScript, etc.). The skeleton and test_code fields change per language but the problem metadata stays the same.

## Test Runner

- Writes user code to a temp file (`solution.py`)
- Writes test code to a temp file (`test_solution.py`)
- Runs `pytest test_solution.py --tb=short -q` in a subprocess with a timeout (10s default)
- Captures stdout/stderr and displays in the output panel
- Runs in a background thread so tkinter stays responsive
- Run button is disabled during execution to prevent double-runs

## State Persistence

**Location:** `~/.dont-rust-bro/state.json`

```json
{
  "active_pack": "python",
  "current_problem_index": 3,
  "current_code": "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        ...",
  "daemon_pid": 12345
}
```

### Rules

- State saved on every meaningful action (code edit debounced at 1s, problem navigation, run)
- When popup re-shows, restores to the same problem with user's in-progress code
- Navigating to a different problem clears the code for the previous problem (no per-problem history)
- New problem loads the skeleton code from the JSON

## Daemon Lifecycle

- **Pidfile:** `~/.dont-rust-bro/daemon.pid`
- **Socket:** `~/.dont-rust-bro/daemon.sock` (Unix domain socket)
- `drb show` checks pidfile → if daemon running, sends "show" via socket. If not, forks daemon process and sends "show".
- `drb hide` sends "hide" via socket (force close, reset counter)
- `drb agent-stop` sends "agent-stop" via socket (decrement counter)
- Daemon exits cleanly when receiving SIGTERM or when explicitly stopped via `drb stop`

### Socket Protocol

Simple newline-delimited JSON messages:

```
→ {"command": "show"}
← {"status": "ok", "agents": 2}

→ {"command": "agent-stop"}
← {"status": "ok", "agents": 1}

→ {"command": "hide"}
← {"status": "ok", "agents": 0}
```

## Installation

### curl-pipe-bash (primary)

```bash
curl -fsSL https://raw.githubusercontent.com/peterkarman1/dont-rust-bro/main/install.sh | bash
```

The installer:
1. Clones/downloads release to `~/.dont-rust-bro/`
2. Symlinks `drb` CLI to a PATH location (`/usr/local/bin/drb` or `~/.local/bin/drb`)
3. Registers hooks in `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "SubagentStart": [{"type": "command", "command": "drb show"}],
       "SubagentStop": [{"type": "command", "command": "drb agent-stop"}],
       "Stop": [{"type": "command", "command": "drb hide"}]
     }
   }
   ```
4. Installs the default Python pack
5. Verifies pytest is available, suggests `pip install pytest` if not

### Homebrew (future)

```bash
brew install dont-rust-bro
```

### Flags

- `--packs=python,javascript` — install specific packs
- `--all` — install all available packs
- `--local` — install to project directory instead of global

## CLI Commands

| Command | Description |
|---------|-------------|
| `drb show` | Show popup (hook use) |
| `drb hide` | Hide popup, reset counter (hook use) |
| `drb agent-stop` | Decrement agent counter (hook use) |
| `drb update` | Pull latest problems from repo |
| `drb packs list` | List installed packs |
| `drb packs use <name>` | Switch active pack |
| `drb status` | Show current state |
| `drb stop` | Kill the daemon |

## Platform Support

### Current: macOS

- tkinter ships with Python on macOS (via Homebrew Python or system Python)
- Unix domain sockets for IPC
- Standard macOS paths

### Future: Windows

- tkinter available on Windows Python
- Switch from Unix socket to named pipes or TCP localhost
- Adjust paths to `%APPDATA%\dont-rust-bro\`

### Future: Linux

- tkinter requires `python3-tk` package on some distros
- Unix domain sockets work natively
- XDG paths (`~/.local/share/dont-rust-bro/`)

## Extensibility Points

- **New language packs:** Add directory under `packs/`, implement language-specific test runner
- **New IDE hooks:** Add hook config template under `hooks/` (e.g., `hooks/cursor.json`)
- **New problem sources:** Problem loader is abstracted; could pull from APIs in the future
