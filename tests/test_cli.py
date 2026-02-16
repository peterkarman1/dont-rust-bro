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

    # Set up fake Claude settings with drb hooks (new matcher group format)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": "/path/to/drb show"}]},
                {"hooks": [{"type": "command", "command": "other-tool start"}]},
            ],
            "Stop": [
                {"hooks": [{"type": "command", "command": "/path/to/drb hide"}]},
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
    assert "other-tool" in updated["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]


def test_packs_use_pulls_image(tmp_path):
    """Test that packs use calls ensure_image for the pack's container image."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    # Create pack under state_dir/packs so cli.py's fallback resolution finds it
    packs_dir = os.path.join(state_dir, "packs")
    pack_dir = os.path.join(packs_dir, "testpack")
    os.makedirs(pack_dir)

    with open(os.path.join(pack_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "testpack",
            "language": "python",
            "version": "1.0.0",
            "description": "Test",
            "image": "python:3.12-slim",
            "test_command": "pytest test_solution.py",
            "problems": [],
        }, f)

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump({"engine": "docker"}, f)

    # The cli resolves packs_dir relative to __file__ first, then falls back
    # to state_dir/packs. We need to force the fallback by making the first
    # os.path.isdir check return False for the repo-relative packs dir.
    real_isdir = os.path.isdir

    def fake_isdir(path):
        if "drb" in path and path.endswith("packs") and "state" not in path:
            return False
        return real_isdir(path)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir), \
         patch("drb.cli.os.path.isdir", side_effect=fake_isdir), \
         patch("drb.container.ensure_image") as mock_ensure:
        main(["packs", "use", "testpack"])
        mock_ensure.assert_called_once_with("docker", "python:3.12-slim")
