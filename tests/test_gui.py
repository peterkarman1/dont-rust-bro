import json
import os
import pytest
from unittest.mock import patch

from drb.gui import PracticeWindow


@pytest.fixture
def setup_env(tmp_path):
    state_dir = str(tmp_path / "state")
    packs_dir = str(tmp_path / "packs")
    os.makedirs(packs_dir)

    python_dir = os.path.join(packs_dir, "python")
    os.makedirs(python_dir)

    with open(os.path.join(python_dir, "pack.json"), "w") as f:
        json.dump({
            "name": "python", "language": "python",
            "version": "1.0.0", "description": "Test pack",
            "image": "python:3.12-slim",
            "test_command": "pytest test_solution.py --tb=short -q",
            "problems": ["add"],
        }, f)

    with open(os.path.join(python_dir, "add.json"), "w") as f:
        json.dump({
            "id": "add", "title": "Add", "difficulty": "easy",
            "description": "Add two numbers.",
            "skeleton": "def add(a, b):\n    pass",
            "test_code": "from solution import add\ndef test_add():\n    assert add(1,2)==3\n",
        }, f)

    return state_dir, packs_dir


def test_load_problem_data(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    problem = pw.current_problem
    assert problem["title"] == "Add"
    assert problem["difficulty"] == "easy"


def test_navigate_wraps(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    pw.next_problem()
    assert pw.state.current_problem_index == 0


def test_show_hide_state(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.visible is False
    pw.show()
    assert pw.visible is True
    pw.hide()
    assert pw.visible is False


def test_api_get_problem(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    api = pw.api
    problem = api.get_problem()
    assert problem["title"] == "Add"
    assert problem["skeleton"] == "def add(a, b):\n    pass"
    assert problem["counter"] == "1/1"


def test_api_save_code(setup_env):
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    api = pw.api
    api.save_code("def add(a,b): return a+b")
    assert pw.state.current_code == "def add(a,b): return a+b"


def test_api_is_tutor_enabled_default(setup_env):
    """Tutor disabled by default when no config."""
    state_dir, packs_dir = setup_env
    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.api.is_tutor_enabled() is False


def test_api_is_tutor_enabled_when_configured(setup_env):
    """Tutor enabled when config has tutor_enabled=True and a key."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    assert pw.api.is_tutor_enabled() is True


def test_api_get_hint(setup_env):
    """get_hint returns hint dict and updates history."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", return_value="Try a hash map."):
        result = pw.api.get_hint("def add(a, b):\n    pass", "")

    assert result["hint"] == "Try a hash map."
    assert result["error"] is None
    assert len(pw._hint_history) == 3  # system + user + assistant


def test_api_get_hint_error(setup_env):
    """get_hint returns error on failure."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", side_effect=RuntimeError("API error (401): Invalid key")):
        result = pw.api.get_hint("code", "")

    assert result["hint"] is None
    assert "401" in result["error"]
    assert len(pw._hint_history) == 0  # history not corrupted


def test_api_get_solution(setup_env):
    """get_solution returns solution dict."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)

    with patch("drb.tutor.call_openrouter", return_value="def add(a, b):\n    # Add two numbers\n    return a + b"):
        result = pw.api.get_solution("def add(a, b):\n    pass")

    assert result["solution"] is not None
    assert result["error"] is None


def test_hint_history_resets_on_navigation(setup_env):
    """Hint history clears when navigating to new problem."""
    state_dir, packs_dir = setup_env
    config_path = os.path.join(state_dir, "config.json")
    os.makedirs(state_dir, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"tutor_enabled": True, "tutor_api_key": "sk-test", "tutor_model": "qwen/qwen3.5-122b-a10b"}, f)

    pw = PracticeWindow(state_dir=state_dir, packs_dir=packs_dir, headless=True)
    pw._hint_history = [{"role": "system", "content": "test"}]

    pw.next_problem()
    assert pw._hint_history == []
