import json
import os
import pytest

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
            "name": "python",
            "language": "python",
            "version": "1.0.0",
            "description": "Test pack",
            "problems": ["add"]
        }, f)

    with open(os.path.join(python_dir, "add.json"), "w") as f:
        json.dump({
            "id": "add",
            "title": "Add",
            "difficulty": "easy",
            "description": "Add two numbers.",
            "skeleton": "def add(a, b):\n    pass",
            "test_code": "from solution import add\ndef test_add():\n    assert add(1,2)==3\n"
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
