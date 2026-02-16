import json
import os


def list_packs(packs_dir: str) -> list:
    """List available pack names."""
    if not os.path.isdir(packs_dir):
        return []
    return [
        d
        for d in os.listdir(packs_dir)
        if os.path.isfile(os.path.join(packs_dir, d, "pack.json"))
    ]


def load_pack(packs_dir: str, pack_name: str) -> dict:
    """Load a pack's metadata."""
    pack_path = os.path.join(packs_dir, pack_name, "pack.json")
    if not os.path.isfile(pack_path):
        raise FileNotFoundError(f"Pack not found: {pack_name}")
    with open(pack_path) as f:
        return json.load(f)


def load_problem(packs_dir: str, pack_name: str, problem_id: str) -> dict:
    """Load a single problem definition."""
    problem_path = os.path.join(packs_dir, pack_name, f"{problem_id}.json")
    if not os.path.isfile(problem_path):
        raise FileNotFoundError(f"Problem not found: {problem_id}")
    with open(problem_path) as f:
        return json.load(f)
