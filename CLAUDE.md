# dont-rust-bro

Pop-up leetcode-style coding challenges while your AI agent is busy thinking. A Claude Code hook-driven desktop app.

## Architecture

```
User sends prompt ──► UserPromptSubmit hook ──► `drb show`
                                                    │
                                              ensure_daemon()
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │         DaemonServer          │
                                    │   (Unix socket, daemon.py)    │
                                    │                               │
                                    │   show  → gui.show()          │
                                    │   hide  → gui.hide()          │
                                    │   stop  → shutdown            │
                                    └───────────────┬───────────────┘
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │       PracticeWindow          │
                                    │     (tkinter, gui.py)         │
                                    │                               │
                                    │   Problem display + editor    │
                                    │   Run button → runner.py      │
                                    │   State persistence           │
                                    └───────────────────────────────┘

Claude finishes ──► Stop hook ──► `drb hide`
```

### Key modules

| File | Purpose |
|------|---------|
| `bin/drb` | Bash entry point, execs `python3 -m drb.cli` |
| `drb/cli.py` | CLI dispatcher: show, hide, stop, status, packs, update, uninstall |
| `drb/daemon.py` | `DaemonServer` — Unix socket server, simple show/hide (no reference counting) |
| `drb/daemon_main.py` | Entry point for daemon process — spawns server thread + tkinter GUI on main thread |
| `drb/gui.py` | `PracticeWindow` — tkinter UI with code editor, problem display, test runner |
| `drb/runner.py` | `run_tests()` — writes solution + tests to tempdir, runs `python3 -m pytest` |
| `drb/problems.py` | `list_packs()`, `load_pack()`, `load_problem()` — JSON-based pack/problem loading |
| `drb/state.py` | `StateManager` — persists active pack, problem index, user code to `state.json` |
| `drb/deps.py` | Dependency checker — validates executables and Python modules per-pack |
| `hooks/claude-code.json` | Hook config: `UserPromptSubmit` → show, `Stop` → hide |
| `install.sh` | One-command installer: clean clone, dep check, symlink, hook registration |

### Data flow

- **Problem packs** live in `packs/<name>/` with a `pack.json` manifest and per-problem JSON files
- **State** persists to `~/.dont-rust-bro/state.json` (active pack, problem index, user code)
- **Daemon IPC** uses a Unix socket at `~/.dont-rust-bro/daemon.sock`
- **Dependencies** declared in `pack.json` under `dependencies.executables` and `dependencies.python_modules`

### Hook behavior

- **Show**: Fires on `UserPromptSubmit` (when user sends a prompt)
- **Hide**: Fires on `Stop` (when Claude fully finishes)
- No reference counting — simple boolean show/hide
- Hooks use the **matcher group format**: `{"EventName": [{"hooks": [{"type": "command", "command": "..."}]}]}`

## Development

### Running tests

```bash
python3 -m pytest tests/ -v
```

### Project conventions

- Python 3.9+ (system python on macOS)
- tkinter for GUI (requires `brew install python-tk@3.12` on macOS)
- pytest for testing
- Tests use short `/tmp` symlinks to work around macOS AF_UNIX 104-byte path limit
- GUI tests use `headless=True` to avoid requiring a display

## Workflow rules

- Always use the **brainstorming** superpower before any creative work, new features, or behavior changes
- Always use the **writing-plans** superpower before multi-step implementation tasks
- Always use the **subagent-driven-development** superpower when executing plans with independent tasks
- Always **commit and push** when work is complete
- Always **update this CLAUDE.md** when architecture, conventions, or important project details change
