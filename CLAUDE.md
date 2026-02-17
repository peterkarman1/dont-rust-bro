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
                                    │ (pywebview + HTML/CSS/JS)     │
                                    │                               │
                                    │   Problem display + editor    │
                                    │   Run button → runner.py      │
                                    │                │              │
                                    │                ▼              │
                                    │         Container Runner      │
                                    │   (docker/podman, temp dir)   │
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
| `drb/daemon_main.py` | Entry point for daemon process — spawns server thread + pywebview GUI on main thread |
| `drb/gui.py` | `PracticeWindow` — pywebview UI with HTML/CSS/JS code editor, problem display, test runner |
| `drb/runner.py` | `run_tests()` — writes solution + tests to tempdir, runs in container |
| `drb/container.py` | Container engine detection, image management, ephemeral test execution |
| `drb/ui/index.html` | Web-based UI for the practice window |
| `drb/problems.py` | `list_packs()`, `load_pack()`, `load_problem()` — JSON-based pack/problem loading |
| `drb/state.py` | `StateManager` — persists active pack, problem index, user code to `state.json` |
| `hooks/claude-code.json` | Hook config: `UserPromptSubmit` → show, `Stop` → hide |
| `install.sh` | One-command installer: clean clone, dep check, symlink, hook registration |

### Data flow

- **Problem packs** live in `packs/<name>/` with a `pack.json` manifest and per-problem JSON files
- **State** persists to `~/.dont-rust-bro/state.json` (active pack, problem index, user code)
- **Container config** persists to `~/.dont-rust-bro/config.json` (container engine preference)
- **Daemon IPC** uses a Unix socket at `~/.dont-rust-bro/daemon.sock`
- **Container image** declared in `pack.json` under `image` and `test_command`
- **Per-pack Dockerfiles** live in `packs/<name>/Dockerfile` — deps (e.g. pytest) are pre-baked into the image at install time
- `ensure_image()` builds from Dockerfile if present in the pack dir, otherwise pulls from registry
- At install, `install.sh` runs `$ENGINE build -t <image> $DRB_HOME/packs/<name>/`
- At runtime, `drb packs use <name>` resolves `packs_dir` relative to `__file__` (dev) or falls back to `$state_dir/packs/` (installed at `~/.dont-rust-bro/packs/`)

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
- pywebview for GUI (requires pywebview + pyobjc-framework-WebKit on macOS)
- Docker or Podman for containerized test execution
- pytest for testing
- Tests use short `/tmp` symlinks to work around macOS AF_UNIX 104-byte path limit
- GUI tests use `headless=True` to avoid requiring a display

## Workflow rules

- Always use the **brainstorming** superpower before any creative work, new features, or behavior changes
- Always use the **writing-plans** superpower before multi-step implementation tasks
- Always use the **subagent-driven-development** superpower when executing plans with independent tasks
- Always **commit and push** when work is complete
- Always **update this CLAUDE.md** when architecture, conventions, or important project details change
