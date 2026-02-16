import os
import threading
import tkinter as tk
from tkinter import font as tkfont

from drb.problems import load_pack, load_problem
from drb.runner import run_tests
from drb.state import StateManager


class PracticeWindow:
    def __init__(self, state_dir: str, packs_dir: str, headless: bool = False):
        self._state_dir = state_dir
        self._packs_dir = packs_dir
        self._headless = headless
        self.visible = False
        self._save_timer = None

        self.state = StateManager(state_dir)
        self._pack = load_pack(packs_dir, self.state.active_pack)
        self._problem_ids = self._pack["problems"]
        self._current_problem = None
        self._load_current_problem()

        if not headless:
            self._build_ui()

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

    def _build_ui(self):
        self._root = tk.Tk()
        self._root.title("dont-rust-bro")
        self._root.geometry("700x650")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        mono = tkfont.Font(family="Menlo", size=13)
        desc_font = tkfont.Font(family="Helvetica", size=12)

        # Header
        header = tk.Frame(self._root, padx=10, pady=5)
        header.pack(fill=tk.X)

        self._title_label = tk.Label(header, text="", font=("Helvetica", 14, "bold"), anchor="w")
        self._title_label.pack(side=tk.LEFT)

        self._counter_label = tk.Label(header, text="", font=("Helvetica", 12), anchor="e")
        self._counter_label.pack(side=tk.RIGHT)

        self._difficulty_label = tk.Label(header, text="", font=("Helvetica", 12), anchor="e")
        self._difficulty_label.pack(side=tk.RIGHT, padx=(0, 10))

        # Description
        desc_frame = tk.Frame(self._root, padx=10, pady=5)
        desc_frame.pack(fill=tk.X)

        self._desc_text = tk.Text(desc_frame, height=6, wrap=tk.WORD, font=desc_font, state=tk.DISABLED, bg="#f5f5f5", relief=tk.FLAT)
        self._desc_text.pack(fill=tk.X)

        # Code editor
        editor_frame = tk.Frame(self._root, padx=10, pady=5)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(editor_frame, text="Solution:", font=("Helvetica", 11, "bold"), anchor="w").pack(fill=tk.X)

        self._code_text = tk.Text(editor_frame, font=mono, wrap=tk.NONE, undo=True, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self._code_text.pack(fill=tk.BOTH, expand=True)
        self._code_text.bind("<<Modified>>", self._on_code_modified)

        # Output
        output_frame = tk.Frame(self._root, padx=10, pady=5)
        output_frame.pack(fill=tk.X)

        tk.Label(output_frame, text="Output:", font=("Helvetica", 11, "bold"), anchor="w").pack(fill=tk.X)

        self._output_text = tk.Text(output_frame, height=6, font=mono, state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4", relief=tk.FLAT)
        self._output_text.pack(fill=tk.X)

        # Buttons
        btn_frame = tk.Frame(self._root, padx=10, pady=10)
        btn_frame.pack(fill=tk.X)

        self._prev_btn = tk.Button(btn_frame, text="\u25c0 Prev", command=self.prev_problem)
        self._prev_btn.pack(side=tk.LEFT, padx=5)

        self._run_btn = tk.Button(btn_frame, text="Run \u25b6", command=self._run_tests, bg="#4CAF50", fg="white")
        self._run_btn.pack(side=tk.LEFT, padx=5)

        self._next_btn = tk.Button(btn_frame, text="Next \u25b6\u25b6", command=self.next_problem)
        self._next_btn.pack(side=tk.LEFT, padx=5)

        self._refresh_ui()
        self._root.withdraw()

    def _refresh_ui(self):
        if self._headless:
            return

        p = self._current_problem
        idx = self.state.current_problem_index
        total = len(self._problem_ids)

        self._title_label.config(text=p["title"])
        self._difficulty_label.config(text=f"[{p['difficulty'].capitalize()}]")
        self._counter_label.config(text=f"{idx + 1}/{total}")

        self._desc_text.config(state=tk.NORMAL)
        self._desc_text.delete("1.0", tk.END)
        self._desc_text.insert("1.0", p["description"])
        self._desc_text.config(state=tk.DISABLED)

        self._code_text.delete("1.0", tk.END)
        code = self.state.current_code if self.state.current_code else p["skeleton"]
        self._code_text.insert("1.0", code)
        self._code_text.edit_modified(False)

        self._output_text.config(state=tk.NORMAL)
        self._output_text.delete("1.0", tk.END)
        self._output_text.config(state=tk.DISABLED)

    def _on_code_modified(self, event=None):
        if self._headless:
            return
        if not self._code_text.edit_modified():
            return
        self._code_text.edit_modified(False)
        if self._save_timer:
            self._root.after_cancel(self._save_timer)
        self._save_timer = self._root.after(1000, self._save_code)

    def _save_code(self):
        if self._headless:
            return
        self.state.current_code = self._code_text.get("1.0", tk.END).rstrip()
        self.state.save()

    def _run_tests(self):
        if self._headless:
            return
        self._run_btn.config(state=tk.DISABLED, text="Running...")
        user_code = self._code_text.get("1.0", tk.END)
        test_code = self._current_problem["test_code"]

        def run():
            result = run_tests(user_code, test_code)
            self._root.after(0, lambda: self._show_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, result: dict):
        self._output_text.config(state=tk.NORMAL)
        self._output_text.delete("1.0", tk.END)
        self._output_text.insert("1.0", result["output"])
        self._output_text.config(state=tk.DISABLED)
        self._run_btn.config(state=tk.NORMAL, text="Run \u25b6")

    def next_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index + 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()
        if not self._headless:
            self._refresh_ui()

    def prev_problem(self):
        self.state.current_code = ""
        self.state.current_problem_index = (self.state.current_problem_index - 1) % len(self._problem_ids)
        self.state.save()
        self._load_current_problem()
        if not self._headless:
            self._refresh_ui()

    def show(self):
        self.visible = True
        if not self._headless:
            self._root.after(0, self._root.deiconify)

    def hide(self):
        self.visible = False
        if not self._headless:
            self._save_code()
            self._root.after(0, self._root.withdraw)

    def _on_close(self):
        self._save_code()
        self.hide()

    def run(self):
        if self._headless:
            return
        self._root.mainloop()
