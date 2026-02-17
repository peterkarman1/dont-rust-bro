import json
import os
import shutil
import signal
import socket
import subprocess
import sys


DEFAULT_STATE_DIR = os.path.expanduser("~/.dont-rust-bro")
DEFAULT_BIN_DIR = os.path.expanduser("~/.local/bin")
CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")


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


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    state_dir = DEFAULT_STATE_DIR

    if not args:
        print("Usage: drb <command>")
        print("Commands: show, hide, stop, status, update, packs, uninstall")
        sys.exit(1)

    command = args[0]

    if command in ("show", "hide", "status"):
        if command == "show":
            ensure_daemon(state_dir)
        try:
            resp = send_to_daemon(state_dir, command)
            if command == "status":
                print(f"Visible: {resp.get('visible', False)}")
        except (ConnectionRefusedError, FileNotFoundError):
            if command == "hide":
                pass  # daemon not running, nothing to hide
            else:
                print("Daemon is not running.", file=sys.stderr)
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

        from drb.problems import list_packs
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
            from drb.problems import load_pack
            from drb.container import load_config, ensure_image
            pack_data = load_pack(packs_dir, pack_name)
            config = load_config(os.path.join(state_dir, "config.json"))
            engine = config.get("engine", "docker")
            pack_dir = os.path.join(packs_dir, pack_name)
            try:
                ensure_image(engine, pack_data["image"], dockerfile_dir=pack_dir)
            except Exception as e:
                print(f"Failed to build/pull image '{pack_data['image']}': {e}", file=sys.stderr)
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
        print("Update not yet implemented. Pull the repo manually.")

    elif command == "uninstall":
        # Stop daemon if running
        try:
            send_to_daemon(state_dir, "stop")
        except (ConnectionRefusedError, FileNotFoundError):
            pass

        # Remove state directory
        if os.path.isdir(state_dir):
            shutil.rmtree(state_dir)
            print(f"Removed {state_dir}")

        # Remove symlink
        symlink_path = os.path.join(DEFAULT_BIN_DIR, "drb")
        if os.path.islink(symlink_path):
            os.remove(symlink_path)
            print(f"Removed {symlink_path}")

        # Remove hooks from Claude settings
        if os.path.isfile(CLAUDE_SETTINGS):
            with open(CLAUDE_SETTINGS) as f:
                settings = json.load(f)
            hooks = settings.get("hooks", {})
            changed = False
            for event in list(hooks.keys()):
                # New format: each entry is a matcher group with a "hooks" array
                filtered = [
                    g for g in hooks[event]
                    if not any("drb" in h.get("command", "") for h in g.get("hooks", []))
                ]
                if len(filtered) != len(hooks[event]):
                    changed = True
                if filtered:
                    hooks[event] = filtered
                else:
                    del hooks[event]
            if changed:
                with open(CLAUDE_SETTINGS, "w") as f:
                    json.dump(settings, f, indent=2)
                print(f"Removed drb hooks from {CLAUDE_SETTINGS}")

        print("Uninstall complete.")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
