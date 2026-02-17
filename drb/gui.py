import os

from drb.problems import load_pack, load_problem
from drb.state import StateManager


class Api:
    """JavaScript-callable API exposed via pywebview."""

    def __init__(self, window_ref):
        self._pw = window_ref

    def get_problem(self) -> dict:
        p = self._pw.current_problem
        idx = self._pw.state.current_problem_index
        total = len(self._pw._problem_ids)
        return {
            "title": p["title"],
            "difficulty": p["difficulty"],
            "description": p["description"],
            "skeleton": p["skeleton"],
            "counter": f"{idx + 1}/{total}",
            "code": self._pw.state.current_code or p["skeleton"],
        }

    def save_code(self, code: str):
        self._pw.state.current_code = code.rstrip()
        self._pw.state.save()

    def next_problem(self) -> dict:
        self._pw.next_problem()
        return self.get_problem()

    def prev_problem(self) -> dict:
        self._pw.prev_problem()
        return self.get_problem()

    def run_tests(self, code: str) -> dict:
        from drb.runner import run_tests
        from drb.container import load_config

        self.save_code(code)
        config_path = os.path.join(self._pw._state_dir, "config.json")
        config = load_config(config_path)
        engine = config.get("engine", "docker")
        pack = self._pw._pack
        image = pack.get("image", "python:3.12-slim")
        test_command = pack.get("test_command", "pytest test_solution.py --tb=short -q")

        solution_file = pack.get("solution_file", "solution.py")
        test_file = pack.get("test_file", "test_solution.py")

        return run_tests(code, self._pw.current_problem["test_code"],
                         engine=engine, image=image,
                         test_command=test_command, timeout=30,
                         solution_file=solution_file, test_file=test_file)


class PracticeWindow:
    def __init__(self, state_dir: str, packs_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._packs_dir = packs_dir
        self._headless = headless
        self.visible = False

        self.state = StateManager(state_dir)
        self._pack = load_pack(packs_dir, self.state.active_pack)
        self._problem_ids = self._pack["problems"]
        self._current_problem = None
        self._load_current_problem()

        self.api = Api(self)
        self._window = None

    def _load_current_problem(self):
        idx = self.state.current_problem_index
        if idx >= len(self._problem_ids):
            idx = 0
            self.state.current_problem_index = 0
        problem_id = self._problem_ids[idx]
        self._current_problem = load_problem(
            self._packs_dir, self.state.active_pack, problem_id
        )

    @property
    def current_problem(self) -> dict:
        return self._current_problem

    def next_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index + 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()

    def prev_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index - 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()

    def show(self):
        self.visible = True
        if self._window and not self._headless:
            self._window.show()

    def hide(self):
        self.visible = False
        if self._window and not self._headless:
            self._window.hide()

    def run(self):
        if self._headless:
            return
        import webview
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
        self._window = webview.create_window(
            "dont-rust-bro", ui_path,
            js_api=self.api,
            width=720, height=680,
            hidden=True,
        )
        webview.start()
