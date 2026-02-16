import json
import os
import pytest
from drb.state import StateManager


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def test_initial_state(state_dir):
    sm = StateManager(state_dir)
    assert sm.active_pack == "python"
    assert sm.current_problem_index == 0
    assert sm.current_code == ""


def test_save_and_load(state_dir):
    sm = StateManager(state_dir)
    sm.active_pack = "python"
    sm.current_problem_index = 3
    sm.current_code = "def foo(): pass"
    sm.save()

    sm2 = StateManager(state_dir)
    assert sm2.active_pack == "python"
    assert sm2.current_problem_index == 3
    assert sm2.current_code == "def foo(): pass"


def test_clear_code(state_dir):
    sm = StateManager(state_dir)
    sm.current_code = "some code"
    sm.save()

    sm.clear_code()
    assert sm.current_code == ""

    sm2 = StateManager(state_dir)
    assert sm2.current_code == ""


def test_state_file_created(state_dir):
    sm = StateManager(state_dir)
    sm.save()
    assert os.path.isfile(os.path.join(state_dir, "state.json"))
