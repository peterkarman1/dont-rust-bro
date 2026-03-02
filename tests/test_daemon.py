import json
import os
import socket
import threading
import time
import pytest
from drb.daemon import DaemonServer


@pytest.fixture
def daemon_dir(tmp_path):
    return str(tmp_path)


def send_command(port: int, command: str) -> dict:
    """Helper to send a command and get response."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    client.sendall(json.dumps({"command": command}).encode() + b"\n")
    data = client.recv(4096)
    client.close()
    return json.loads(data.decode())


def test_show_makes_visible(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp = send_command(server.port, "show")
        assert resp["status"] == "ok"
        assert resp["visible"] is True
    finally:
        server.shutdown()


def test_hide_makes_invisible(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        send_command(server.port, "show")
        resp = send_command(server.port, "hide")
        assert resp["status"] == "ok"
        assert resp["visible"] is False
    finally:
        server.shutdown()


def test_show_is_idempotent(daemon_dir):
    server = DaemonServer(daemon_dir, headless=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        resp1 = send_command(server.port, "show")
        resp2 = send_command(server.port, "show")
        resp3 = send_command(server.port, "show")
        assert resp1["visible"] is True
        assert resp2["visible"] is True
        assert resp3["visible"] is True
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
