import json
import os
import socket
import threading
import time
import pytest
from drb.daemon import DaemonServer


@pytest.fixture
def daemon_dir(tmp_path):
    # Use a short symlink to avoid AF_UNIX 104-byte path limit on macOS
    import uuid
    short = "/tmp/_drb_" + uuid.uuid4().hex[:8]
    os.symlink(str(tmp_path), short)
    yield short
    os.unlink(short)


def send_command(sock_path: str, command: str) -> dict:
    """Helper to send a command and get response."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(sock_path)
    client.sendall(json.dumps({"command": command}).encode() + b"\n")
    data = client.recv(4096)
    client.close()
    return json.loads(data.decode())


def test_show_increments_agent_count(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp = send_command(server.sock_path, "show")
        assert resp["status"] == "ok"
        assert resp["agents"] == 1

        resp = send_command(server.sock_path, "show")
        assert resp["agents"] == 2
    finally:
        server.shutdown()


def test_agent_stop_decrements(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 1

        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_agent_stop_does_not_go_negative(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp = send_command(server.sock_path, "agent-stop")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_hide_resets_counter(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        send_command(server.sock_path, "show")
        resp = send_command(server.sock_path, "hide")
        assert resp["agents"] == 0
    finally:
        server.shutdown()


def test_pidfile_created(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        assert os.path.isfile(os.path.join(daemon_dir, "daemon.pid"))
    finally:
        server.shutdown()
