import json
import os
import socket
import sys
import threading
import pytest
from unittest.mock import patch
from drb.cli import send_to_daemon, is_daemon_running, main


def _can_symlink():
    """Check if the current process can create symlinks."""
    if sys.platform != "win32":
        return True
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as td:
            os.symlink(td, os.path.join(td, "_test_link"))
        return True
    except OSError:
        return False


needs_symlink = pytest.mark.skipif(
    not _can_symlink(), reason="symlinks require admin on Windows"
)


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
    """Start a minimal TCP server and test send_to_daemon talks to it."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    server.listen(1)

    # Write port file so send_to_daemon can find it
    port_path = os.path.join(daemon_dir, "daemon.port")
    with open(port_path, "w") as f:
        f.write(str(port))

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


@needs_symlink
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


@needs_symlink
def test_uninstall_removes_symlinked_state(tmp_path):
    """Test that uninstall removes symlink to state dir without deleting target."""
    real_dir = str(tmp_path / "real")
    os.makedirs(real_dir)
    (tmp_path / "real" / "state.json").write_text("{}")

    state_link = str(tmp_path / "state")
    os.symlink(real_dir, state_link)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_link), \
         patch("drb.cli.DEFAULT_BIN_DIR", str(tmp_path / "bin")), \
         patch("drb.cli.CLAUDE_SETTINGS", str(tmp_path / "nosettings.json")), \
         patch("drb.cli.send_to_daemon", side_effect=ConnectionRefusedError):
        main(["uninstall"])

    # Symlink removed
    assert not os.path.islink(state_link)
    # Original directory preserved
    assert os.path.isdir(real_dir)
    assert os.path.isfile(os.path.join(real_dir, "state.json"))


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
        mock_ensure.assert_called_once()
        call_args = mock_ensure.call_args
        assert call_args[0][0] == "docker"
        assert call_args[0][1] == "python:3.12-slim"
        assert "dockerfile_dir" in call_args[1]


def test_tutor_on_saves_config(tmp_path):
    """Test that tutor on saves key and model to config."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "on", "--key", "sk-or-test-123"])

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_enabled"] is True
    assert config["tutor_api_key"] == "sk-or-test-123"
    assert config["tutor_model"] == "qwen/qwen3.5-122b-a10b"


def test_tutor_on_custom_model(tmp_path):
    """Test that tutor on accepts custom model."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "on", "--key", "sk-test", "--model", "anthropic/claude-sonnet-4"])

    config_path = os.path.join(state_dir, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_model"] == "anthropic/claude-sonnet-4"


def test_tutor_off(tmp_path):
    """Test that tutor off disables but preserves key/model."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        main(["tutor", "off"])

    with open(config_path) as f:
        config = json.load(f)
    assert config["tutor_enabled"] is False
    assert config["tutor_api_key"] == "sk-test"  # preserved


def test_tutor_on_requires_key(tmp_path):
    """Test that tutor on without key and no existing key fails."""
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)

    with patch("drb.cli.DEFAULT_STATE_DIR", state_dir):
        with pytest.raises(SystemExit):
            main(["tutor", "on"])
