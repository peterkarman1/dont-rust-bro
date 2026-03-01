import json
import os
import shutil
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
    except (ValueError, ProcessLookupError):
        return False
    except PermissionError:
        # PermissionError means the process exists but we can't signal it
        return True
    except OSError:
        # On Windows, os.kill raises OSError for non-existent PIDs
        return False


def send_to_daemon(state_dir: str, command: str) -> dict:
    """Send a command to the running daemon via TCP localhost."""
    port_path = os.path.join(state_dir, "daemon.port")
    with open(port_path) as f:
        port = int(f.read().strip())
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(("127.0.0.1", port))
    client.sendall(json.dumps({"command": command}).encode() + b"\n")
    data = client.recv(4096)
    client.close()
    return json.loads(data.decode())


def launch_daemon(state_dir: str):
    """Launch the daemon as a background process."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [sys.executable, "-m", "drb.daemon_main", "--state-dir", state_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


def ensure_daemon(state_dir: str):
    """Ensure the daemon is running, launching it if needed."""
    if not is_daemon_running(state_dir):
        launch_daemon(state_dir)
        import time
        for _ in range(20):
            time.sleep(0.1)
            if os.path.exists(os.path.join(state_dir, "daemon.port")):
                break


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    state_dir = DEFAULT_STATE_DIR

    if not args:
        print("Usage: drb <command>")
        print("Commands: show, hide, stop, status, update, packs, tutor, uninstall")
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

        # Remove state directory (or symlink to it)
        if os.path.islink(state_dir):
            os.remove(state_dir)
            print(f"Removed symlink {state_dir}")
        elif os.path.isdir(state_dir):
            shutil.rmtree(state_dir)
            print(f"Removed {state_dir}")

        # Remove entry point (symlink on Unix, .bat on Windows)
        symlink_path = os.path.join(DEFAULT_BIN_DIR, "drb")
        bat_path = os.path.join(DEFAULT_BIN_DIR, "drb.bat")
        if os.path.islink(symlink_path):
            os.remove(symlink_path)
            print(f"Removed {symlink_path}")
        if os.path.isfile(bat_path):
            os.remove(bat_path)
            print(f"Removed {bat_path}")

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

    elif command == "tutor":
        from drb.container import load_config, save_config
        config_path = os.path.join(state_dir, "config.json")
        config = load_config(config_path)

        sub = args[1] if len(args) > 1 else "status"

        if sub == "on":
            key = None
            model = "qwen/qwen3.5-122b-a10b"
            i = 2
            while i < len(args):
                if args[i] == "--key" and i + 1 < len(args):
                    key = args[i + 1]
                    i += 2
                elif args[i] == "--model" and i + 1 < len(args):
                    model = args[i + 1]
                    i += 2
                else:
                    i += 1

            if not key:
                key = config.get("tutor_api_key")
            if not key:
                print("Error: --key is required (no existing key found).", file=sys.stderr)
                sys.exit(1)

            config["tutor_enabled"] = True
            config["tutor_api_key"] = key
            config["tutor_model"] = model
            save_config(config_path, config)
            print(f"Tutor enabled. Model: {model}")

        elif sub == "off":
            config["tutor_enabled"] = False
            save_config(config_path, config)
            print("Tutor disabled.")

        elif sub == "status":
            enabled = config.get("tutor_enabled", False)
            model = config.get("tutor_model", "qwen/qwen3.5-122b-a10b")
            has_key = bool(config.get("tutor_api_key"))
            key_display = "configured" if has_key else "not set"
            print(f"Tutor: {'enabled' if enabled else 'disabled'}")
            print(f"Model: {model}")
            print(f"API key: {key_display}")

        else:
            print("Usage: drb tutor [on|off|status] [--key KEY] [--model MODEL]")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
