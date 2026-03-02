#!/usr/bin/env python3
"""Cross-platform installer for dont-rust-bro.

Works on Windows, macOS, and Linux. Replaces install.sh for Windows users
and can optionally be used on all platforms.

Usage:
    python install.py
    python install.py --local        # symlink local repo instead of cloning
    python install.py --packs=python,javascript
"""

import json
import os
import shutil
import subprocess
import sys

DRB_REPO = "https://github.com/peterkarman1/dont-rust-bro.git"
IS_WINDOWS = sys.platform == "win32"


def info(msg):
    print(f"[drb] {msg}")


def error(msg):
    print(f"[drb] ERROR: {msg}", file=sys.stderr)


def get_drb_home():
    return os.path.expanduser("~/.dont-rust-bro")


def get_claude_settings_path():
    return os.path.expanduser("~/.claude/settings.json")


def get_bin_dir():
    if IS_WINDOWS:
        return os.path.expanduser("~/.local/bin")
    return os.path.expanduser("~/.local/bin")


def get_venv_python(drb_home):
    if IS_WINDOWS:
        return os.path.join(drb_home, "venv", "Scripts", "python.exe")
    return os.path.join(drb_home, "venv", "bin", "python")


def get_venv_pip(drb_home):
    if IS_WINDOWS:
        return os.path.join(drb_home, "venv", "Scripts", "pip.exe")
    return os.path.join(drb_home, "venv", "bin", "pip")


def check_python():
    version = sys.version_info
    if version < (3, 9):
        error(f"Python 3.9+ required, found {version.major}.{version.minor}")
        sys.exit(1)
    info(f"Using Python: {sys.version.split()[0]}")


def detect_engine():
    for engine in ("podman", "docker"):
        if shutil.which(engine):
            info(f"Using container engine: {engine}")
            return engine
    error("docker or podman is required but neither was found.")
    sys.exit(1)


def install_repo(drb_home, local):
    if os.path.islink(drb_home) or os.path.isdir(drb_home):
        info("Removing existing installation...")
        if os.path.islink(drb_home):
            os.remove(drb_home)
        else:
            shutil.rmtree(drb_home)

    if local:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if IS_WINDOWS:
            # Windows doesn't reliably support symlinks without admin
            # Copy the repo instead
            shutil.copytree(script_dir, drb_home, ignore=shutil.ignore_patterns("venv", ".git", "__pycache__"))
        else:
            os.symlink(script_dir, drb_home)
        info(f"Linked local repo to {drb_home}")
    else:
        info(f"Cloning to {drb_home}...")
        subprocess.run(["git", "clone", "--quiet", DRB_REPO, drb_home], check=True)


def create_venv(drb_home):
    info("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", os.path.join(drb_home, "venv")], check=True)

    pip = get_venv_pip(drb_home)
    info("Installing pywebview...")
    subprocess.run([pip, "install", "--quiet", "pywebview"], check=True)


def save_config(drb_home, engine):
    config_path = os.path.join(drb_home, "config.json")
    with open(config_path, "w") as f:
        json.dump({"engine": engine}, f, indent=2)


def build_pack_images(drb_home, engine, packs):
    packs_dir = os.path.join(drb_home, "packs")
    for pack_name in packs:
        pack_json = os.path.join(packs_dir, pack_name, "pack.json")
        if not os.path.isfile(pack_json):
            info(f"Skipping pack '{pack_name}' (not found)")
            continue
        with open(pack_json) as f:
            pack_data = json.load(f)
        image = pack_data["image"]
        pack_dir = os.path.join(packs_dir, pack_name)
        info(f"Building container image: {image}...")
        subprocess.run([engine, "build", "-t", image, pack_dir], check=True)


def install_entry_point(drb_home):
    bin_dir = get_bin_dir()
    os.makedirs(bin_dir, exist_ok=True)

    if IS_WINDOWS:
        # Copy the .bat file
        src = os.path.join(drb_home, "bin", "drb.bat")
        dst = os.path.join(bin_dir, "drb.bat")
        shutil.copy2(src, dst)
        info(f"Installed {dst}")

        # Also create a .cmd wrapper for broader compatibility
        cmd_path = os.path.join(bin_dir, "drb.cmd")
        shutil.copy2(src, cmd_path)
    else:
        drb_script = os.path.join(drb_home, "bin", "drb")
        os.chmod(drb_script, 0o755)
        link_path = os.path.join(bin_dir, "drb")
        if os.path.islink(link_path):
            os.remove(link_path)
        os.symlink(drb_script, link_path)
        info(f"Symlinked {link_path} -> {drb_script}")

    # Check if bin_dir is in PATH
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    if not any(os.path.abspath(d) == os.path.abspath(bin_dir) for d in path_dirs):
        if IS_WINDOWS:
            info(f"Add {bin_dir} to your PATH environment variable.")
            info("You can do this in Settings > System > About > Advanced system settings > Environment Variables")
        else:
            # Try to add to shell profile
            shell = os.environ.get("SHELL", "/bin/bash")
            shell_name = os.path.basename(shell)
            if shell_name == "zsh":
                profile = os.path.expanduser("~/.zshrc")
            elif shell_name == "bash":
                bp = os.path.expanduser("~/.bash_profile")
                profile = bp if os.path.isfile(bp) else os.path.expanduser("~/.bashrc")
            else:
                profile = os.path.expanduser("~/.profile")

            path_line = 'export PATH="$HOME/.local/bin:$PATH"'
            already_present = False
            if os.path.isfile(profile):
                with open(profile) as f:
                    already_present = ".local/bin" in f.read()

            if not already_present:
                info(f"Adding {bin_dir} to PATH in {profile}...")
                with open(profile, "a") as f:
                    f.write("\n# Added by dont-rust-bro\n")
                    f.write(path_line + "\n")
                info(f"Run 'source {profile}' or open a new terminal for PATH changes to take effect.")


def register_hooks(drb_home):
    info("Registering Claude Code hooks...")
    settings_path = get_claude_settings_path()
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)

    bin_dir = get_bin_dir()
    if IS_WINDOWS:
        drb_cmd = os.path.join(bin_dir, "drb.bat").replace("\\", "/")
    else:
        drb_cmd = os.path.join(bin_dir, "drb")

    drb_hooks = {
        "UserPromptSubmit": {"hooks": [{"type": "command", "command": f"{drb_cmd} show"}]},
        "Stop": {"hooks": [{"type": "command", "command": f"{drb_cmd} hide"}]},
    }

    if os.path.isfile(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})

    for event, matcher_group in drb_hooks.items():
        event_groups = hooks.setdefault(event, [])
        # Remove existing drb matcher groups
        event_groups = [
            g for g in event_groups
            if not any("drb" in h.get("command", "") for h in g.get("hooks", []))
        ]
        event_groups.append(matcher_group)
        hooks[event] = event_groups

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)


def main():
    local = "--local" in sys.argv
    packs = ["python", "javascript", "ruby"]

    for arg in sys.argv[1:]:
        if arg.startswith("--packs="):
            packs = arg.split("=", 1)[1].split(",")

    drb_home = get_drb_home()

    check_python()
    engine = detect_engine()

    install_repo(drb_home, local)
    create_venv(drb_home)
    save_config(drb_home, engine)
    build_pack_images(drb_home, engine, packs)
    install_entry_point(drb_home)
    register_hooks(drb_home)

    info("")
    info("Installation complete!")
    info(f"Container engine: {engine}")
    if local:
        info(f"DRB_HOME: {drb_home} ({'copy' if IS_WINDOWS else 'symlink'})")
    info("Commands:")
    info("  drb status     - Check daemon status")
    info("  drb packs list - List installed problem packs")
    info("  drb uninstall  - Remove everything")
    info("")
    info("The practice window will appear automatically when Claude starts working.")


if __name__ == "__main__":
    main()
