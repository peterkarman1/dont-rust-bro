import json
import os
import signal
import socket
import threading


class DaemonServer:
    """Unix socket server that manages GUI visibility."""

    def __init__(self, state_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._headless = headless
        self._running = False
        self._server_socket = None
        self._gui = None

        os.makedirs(state_dir, exist_ok=True)
        self.sock_path = os.path.join(state_dir, "daemon.sock")
        self._pid_path = os.path.join(state_dir, "daemon.pid")

    def _write_pidfile(self):
        with open(self._pid_path, "w") as f:
            f.write(str(os.getpid()))

    def _remove_pidfile(self):
        if os.path.isfile(self._pid_path):
            os.remove(self._pid_path)

    def _handle_command(self, command: str) -> dict:
        if command == "show":
            if self._gui and not self._headless:
                self._gui.show()
            return {"status": "ok", "visible": True}
        elif command == "hide":
            if self._gui and not self._headless:
                self._gui.hide()
            return {"status": "ok", "visible": False}
        elif command == "status":
            return {
                "status": "ok",
                "visible": self._gui.visible if self._gui else False,
            }
        elif command == "stop":
            self._running = False
            return {"status": "ok"}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    def _handle_client(self, conn: socket.socket):
        try:
            data = conn.recv(4096)
            if not data:
                return
            msg = json.loads(data.decode().strip())
            command = msg.get("command", "")
            response = self._handle_command(command)
            conn.sendall(json.dumps(response).encode() + b"\n")
        except (json.JSONDecodeError, KeyError):
            conn.sendall(json.dumps({"status": "error", "message": "Invalid message"}).encode() + b"\n")
        finally:
            conn.close()

    def set_gui(self, gui):
        self._gui = gui

    def serve_forever(self):
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_socket.bind(self.sock_path)
        self._server_socket.listen(5)
        self._server_socket.settimeout(0.5)
        self._running = True
        self._write_pidfile()

        try:
            while self._running:
                try:
                    conn, _ = self._server_socket.accept()
                    threading.Thread(
                        target=self._handle_client, args=(conn,), daemon=True
                    ).start()
                except socket.timeout:
                    continue
        finally:
            self._server_socket.close()
            if os.path.exists(self.sock_path):
                os.remove(self.sock_path)
            self._remove_pidfile()

    def shutdown(self):
        self._running = False
