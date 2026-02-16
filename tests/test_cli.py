import json
import os
import socket
import threading
import time
import pytest
from unittest.mock import patch
from drb.cli import send_to_daemon, is_daemon_running


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
