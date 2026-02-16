import json
import os

import pytest

from drb.deps import check_executable, check_python_module, check_core_deps, check_pack_deps


def test_check_executable_found():
    assert check_executable("python3") is True


def test_check_executable_missing():
    assert check_executable("totally_bogus_binary_xyz") is False


def test_check_python_module_found():
    assert check_python_module("json") is True


def test_check_python_module_missing():
    assert check_python_module("totally_bogus_module_xyz") is False


def test_check_core_deps():
    errors = check_core_deps()
    assert errors == []


def test_check_pack_deps_all_satisfied(tmp_path):
    pack_dir = tmp_path / "testpack"
    pack_dir.mkdir()
    (pack_dir / "pack.json").write_text(json.dumps({
        "name": "testpack",
        "language": "python",
        "version": "1.0.0",
        "description": "Test",
        "problems": [],
        "dependencies": {
            "executables": ["python3"],
            "python_modules": ["json"],
        },
    }))
    errors = check_pack_deps(str(tmp_path), "testpack")
    assert errors == []


def test_check_pack_deps_missing(tmp_path):
    pack_dir = tmp_path / "badpack"
    pack_dir.mkdir()
    (pack_dir / "pack.json").write_text(json.dumps({
        "name": "badpack",
        "language": "python",
        "version": "1.0.0",
        "description": "Test",
        "problems": [],
        "dependencies": {
            "executables": ["totally_bogus_binary_xyz"],
            "python_modules": ["totally_bogus_module_xyz"],
        },
    }))
    errors = check_pack_deps(str(tmp_path), "badpack")
    assert len(errors) == 2
    assert any("totally_bogus_binary_xyz" in e for e in errors)
    assert any("totally_bogus_module_xyz" in e for e in errors)


def test_check_pack_deps_no_deps_field(tmp_path):
    pack_dir = tmp_path / "nopack"
    pack_dir.mkdir()
    (pack_dir / "pack.json").write_text(json.dumps({
        "name": "nopack",
        "language": "python",
        "version": "1.0.0",
        "description": "Test",
        "problems": [],
    }))
    errors = check_pack_deps(str(tmp_path), "nopack")
    assert errors == []


def test_check_pack_deps_pack_not_found(tmp_path):
    errors = check_pack_deps(str(tmp_path), "nonexistent")
    assert len(errors) == 1
    assert "not found" in errors[0].lower()
