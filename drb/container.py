import shutil


def detect_engine() -> str:
    """Detect container engine. Prefers podman over docker."""
    for engine in ("podman", "docker"):
        if shutil.which(engine):
            return engine
    raise RuntimeError(
        "No container engine found. Install docker or podman."
    )
