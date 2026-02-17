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


def test_list_packs_includes_javascript():
    packs = list_packs(PACKS_DIR)
    assert "javascript" in packs


def test_load_javascript_pack():
    pack = load_pack(PACKS_DIR, "javascript")
    assert pack["name"] == "javascript"
    assert pack["language"] == "javascript"
    assert len(pack["problems"]) == 35


def test_load_javascript_problem():
    problem = load_problem(PACKS_DIR, "javascript", "two_sum")
    assert problem["id"] == "two_sum"
    assert "module.exports" in problem["skeleton"]
    assert "require('./solution')" in problem["test_code"]


def test_list_packs_includes_ruby():
    packs = list_packs(PACKS_DIR)
    assert "ruby" in packs


def test_load_ruby_pack():
    pack = load_pack(PACKS_DIR, "ruby")
    assert pack["name"] == "ruby"
    assert pack["language"] == "ruby"
    assert len(pack["problems"]) == 35


def test_load_ruby_problem():
    problem = load_problem(PACKS_DIR, "ruby", "two_sum")
    assert problem["id"] == "two_sum"
    assert "def two_sum" in problem["skeleton"]
    assert "require_relative" in problem["test_code"]
