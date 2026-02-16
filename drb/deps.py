import importlib.util
import json
import os
import shutil


def check_executable(name: str) -> bool:
    """Check if an executable is available on PATH."""
    return shutil.which(name) is not None


def check_python_module(name: str) -> bool:
    """Check if a Python module is importable."""
    return importlib.util.find_spec(name) is not None


def check_core_deps() -> list:
    """Check core dependencies required regardless of pack.

    Returns a list of error strings (empty means all good).
    """
    errors = []
    if not check_executable("python3"):
        errors.append("python3 is required but not found on PATH.")
    if not check_python_module("tkinter"):
        errors.append(
            "tkinter is required but not found. "
            "Install with: brew install python-tk@3.12"
        )
    return errors


def check_pack_deps(packs_dir: str, pack_name: str) -> list:
    """Check dependencies declared in a pack's pack.json.

    Returns a list of error strings (empty means all good).
    """
    pack_path = os.path.join(packs_dir, pack_name, "pack.json")
    if not os.path.isfile(pack_path):
        return [f"Pack not found: {pack_name}"]

    with open(pack_path) as f:
        pack = json.load(f)

    deps = pack.get("dependencies", {})
    errors = []

    for exe in deps.get("executables", []):
        if not check_executable(exe):
            errors.append(f"Required executable not found: {exe}")

    for mod in deps.get("python_modules", []):
        if not check_python_module(mod):
            errors.append(f"Required Python module not found: {mod}")

    return errors
