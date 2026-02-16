import pytest
from unittest.mock import patch
from drb.container import detect_engine


def test_detect_engine_podman_preferred():
    with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("podman", "docker") else None):
        assert detect_engine() == "podman"


def test_detect_engine_docker_fallback():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/docker" if x == "docker" else None):
        assert detect_engine() == "docker"


def test_detect_engine_none():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="docker or podman"):
            detect_engine()
