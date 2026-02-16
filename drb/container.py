import shutil
import subprocess


def detect_engine() -> str:
    """Detect container engine. Prefers podman over docker."""
    for engine in ("podman", "docker"):
        if shutil.which(engine):
            return engine
    raise RuntimeError(
        "No container engine found. Install docker or podman."
    )


def ensure_image(engine: str, image: str):
    """Pull image if not already present locally."""
    result = subprocess.run(
        [engine, "image", "inspect", image],
        capture_output=True, timeout=10,
    )
    if result.returncode != 0:
        subprocess.run(
            [engine, "pull", image],
            capture_output=True, timeout=300,
        )


def run_in_container(engine: str, image: str, test_command: str,
                     work_dir: str, timeout: int = 10) -> dict:
    """Run test command in an ephemeral container.

    Mounts work_dir to /work inside the container.
    Returns dict with 'passed' (bool) and 'output' (str).
    """
    cmd = [
        engine, "run", "--rm", "--network=none",
        "-v", f"{work_dir}:/work", "-w", "/work",
        "--memory=256m", "--cpus=1",
        image, "sh", "-c", test_command,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = f"Timeout: tests did not complete within {timeout} seconds."
        passed = False

    return {"passed": passed, "output": output.strip()}
