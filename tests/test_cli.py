import json
import os
import socket
import threading
import time
import pytest
from unittest.mock import patch
from drb.cli import send_to_daemon, is_daemon_running, main


@pytest.fixture
def daemon_dir(tmp_path):
    # On macOS, AF_UNIX socket paths have a short max length (~104 chars).
    # Use a symlink to shorten the path if needed.
    short = "/tmp/_drb_test"
    target = str(tmp_path)
    if os.path.islink(short) or os.path.exists(short):
        os.remove(short)
    os.symlink(target, short)
    yield short
    os.remove(short)


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


def test_uninstall_removes_artifacts(tmp_path):
    """Test that uninstall removes state dir, symlink, and hooks."""
    state_dir = str(tmp_path / "state")
    bin_dir = str(tmp_path / "bin")
    settings_path = str(tmp_path / "settings.json")

    # Set up fake state dir
    os.makedirs(state_dir)
    (tmp_path / "state" / "state.json").write_text("{}")

    # Set up fake symlink
    os.makedirs(bin_dir)
    symlink = os.path.join(bin_dir, "drb")
    os.symlink("/fake/target", symlink)

    # Set up fake Claude settings with drb hooks
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"type": "command", "command": "/path/to/drb show"},
                {"type": "command", "command": "other-tool start"},
            ],
            "Stop": [
                {"type": "command", "command": "/path/to/drb hide"},
            ],
        }
    }
    with open(settings_path, "w") as f:
        json.dump(settings, f)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir), \
         patch("drb.cli.DEFAULT_BIN_DIR", bin_dir), \
         patch("drb.cli.CLAUDE_SETTINGS", settings_path), \
         patch("drb.cli.send_to_daemon", side_effect=ConnectionRefusedError):
        main(["uninstall"])

    # State dir removed
    assert not os.path.isdir(state_dir)
    # Symlink removed
    assert not os.path.islink(symlink)
    # drb hooks removed, other hooks preserved
    with open(settings_path) as f:
        updated = json.load(f)
    assert "Stop" not in updated["hooks"]
    assert len(updated["hooks"]["UserPromptSubmit"]) == 1
    assert "other-tool" in updated["hooks"]["UserPromptSubmit"][0]["command"]


def test_packs_use_rejects_missing_deps(tmp_path):
    """Test that check_pack_deps catches missing dependencies."""
    packs_dir = str(tmp_path / "packs")
    pack_dir = os.path.join(packs_dir, "badpack")
    os.makedirs(pack_dir)

    with open(os.path.join(pack_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "badpack",
            "language": "python",
            "version": "1.0.0",
            "description": "Test",
            "problems": [],
            "dependencies": {
                "executables": ["totally_bogus_binary_xyz"],
            },
        }, f)

    from drb.deps import check_pack_deps
    errors = check_pack_deps(packs_dir, "badpack")
    assert len(errors) == 1
    assert "totally_bogus_binary_xyz" in errors[0]
