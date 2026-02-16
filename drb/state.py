import json
import os


class StateManager:
    def __init__(self, state_dir: str):
        self._state_dir = state_dir
        self._state_file = os.path.join(state_dir, "state.json")
        self.active_pack = "python"
        self.current_problem_index = 0
        self.current_code = ""
        self._load()

    def _load(self):
        if os.path.isfile(self._state_file):
            with open(self._state_file) as f:
                data = json.load(f)
            self.active_pack = data.get("active_pack", "python")
            self.current_problem_index = data.get("current_problem_index", 0)
            self.current_code = data.get("current_code", "")

    def save(self):
        os.makedirs(self._state_dir, exist_ok=True)
        with open(self._state_file, "w") as f:
            json.dump(
                {
                    "active_pack": self.active_pack,
                    "current_problem_index": self.current_problem_index,
                    "current_code": self.current_code,
                },
                f,
                indent=2,
            )

    def clear_code(self):
        self.current_code = ""
        self.save()
