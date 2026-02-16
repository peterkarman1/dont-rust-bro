import os
import pytest
from drb.problems import load_pack, load_problem, list_packs

PACKS_DIR = os.path.join(os.path.dirname(__file__), "..", "packs")


def test_list_packs():
    packs = list_packs(PACKS_DIR)
    assert "python" in packs


def test_load_pack():
    pack = load_pack(PACKS_DIR, "python")
    assert pack["name"] == "python"
    assert pack["language"] == "python"
    assert len(pack["problems"]) >= 5


def test_load_problem():
    problem = load_problem(PACKS_DIR, "python", "two_sum")
    assert problem["id"] == "two_sum"
    assert problem["title"] == "Two Sum"
    assert problem["difficulty"] == "easy"
    assert "skeleton" in problem
    assert "test_code" in problem


def test_load_problem_not_found():
    with pytest.raises(FileNotFoundError):
        load_problem(PACKS_DIR, "python", "nonexistent")


def test_load_pack_not_found():
    with pytest.raises(FileNotFoundError):
        load_pack(PACKS_DIR, "nonexistent")
