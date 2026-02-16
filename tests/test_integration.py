import json
import os
import socket
import threading
import time
import uuid

import pytest

from drb.daemon import DaemonServer
from drb.gui import PracticeWindow


@pytest.fixture
def env(tmp_path, request):
    # Use a short symlink to avoid AF_UNIX 104-byte path limit on macOS
    short = "/tmp/_drb_" + uuid.uuid4().hex[:8]
    os.symlink(str(tmp_path), short)

    state_dir = os.path.join(short, "state")
    packs_dir = os.path.join(short, "packs")
    os.makedirs(packs_dir)

    python_dir = os.path.join(packs_dir, "python")
    os.makedirs(python_dir)

    with open(os.path.join(python_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "python", "language": "python",
            "version": "1.0.0", "description": "Test",
            "problems": ["add", "sub"]
        }, f)

    for pid, title, skel, test in [
        ("add", "Add", "def add(a,b):\n    pass", "from solution import add\ndef test_add():\n    assert add(1,2)==3\n"),
        ("sub", "Subtract", "def sub(a,b):\n    pass", "from solution import sub\ndef test_sub():\n    assert sub(5,3)==2\n"),
    ]:
        with open(os.path.join(python_dir, f"{pid}.json"), "w") as f:
            json.dump({
                "id": pid, "title": title, "difficulty": "easy",
                "description": f"{title} two numbers.",
                "skeleton": skel, "test_code": test
            }, f)

    def cleanup():
        os.unlink(short)

    request.addfinalizer(cleanup)

    return state_dir, packs_dir


def send_cmd(sock_path, cmd):
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(sock_path)
    c.sendall(json.dumps({"command": cmd}).encode() + b"\n")
    data = c.recv(4096)
    c.close()
    return json.loads(data.decode())


def test_full_lifecycle(env):
    state_dir, packs_dir = env

    # Daemon headless=False so it calls gui.show/hide; GUI headless=True so no tkinter
    server = DaemonServer(state_dir, headless=False)
    gui = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    server.set_gui(gui)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)

    try:
        # Show makes GUI visible
        resp = send_cmd(server.sock_path, "show")
        assert resp["visible"] is True
        assert gui.visible is True

        # Show again is idempotent
        resp = send_cmd(server.sock_path, "show")
        assert resp["visible"] is True
        assert gui.visible is True

        # Hide makes GUI invisible
        resp = send_cmd(server.sock_path, "hide")
        assert resp["visible"] is False
        assert gui.visible is False

        # Show again after hide works
        resp = send_cmd(server.sock_path, "show")
        assert resp["visible"] is True
        assert gui.visible is True

        # Hide again
        resp = send_cmd(server.sock_path, "hide")
        assert resp["visible"] is False
        assert gui.visible is False
    finally:
        server.shutdown()


def test_problem_navigation_persists(env):
    state_dir, packs_dir = env

    gui = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert gui.current_problem["id"] == "add"

    gui.next_problem()
    assert gui.current_problem["id"] == "sub"

    # Recreate — should restore to problem index 1
    gui2 = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert gui2.current_problem["id"] == "sub"
