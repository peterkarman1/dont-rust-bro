#!/usr/bin/env bash
set -euo pipefail

# Install from the local repo directory instead of cloning from GitHub.
# Usage: ./install-local.sh [--all] [--packs=python,javascript,ruby]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRB_HOME="${HOME}/.dont-rust-bro"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[drb]${NC} $*"; }
warn()  { echo -e "${YELLOW}[drb]${NC} $*"; }
error() { echo -e "${RED}[drb]${NC} $*" >&2; }

# Parse flags
PACKS="python"
INSTALL_ALL=false

for arg in "$@"; do
    case "$arg" in
        --all) INSTALL_ALL=true ;;
        --packs=*) PACKS="${arg#--packs=}" ;;
    esac
done

# Check python3
if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found."
    exit 1
fi
info "Using Python: $(python3 --version)"

# Detect container engine (prefer podman)
ENGINE=""
if command -v podman &>/dev/null; then
    ENGINE="podman"
elif command -v docker &>/dev/null; then
    ENGINE="docker"
else
    error "docker or podman is required but neither was found."
    exit 1
fi
info "Using container engine: ${ENGINE}"

# Clean existing install, then symlink local repo
if [ -d "$DRB_HOME" ] || [ -L "$DRB_HOME" ]; then
    info "Removing existing installation..."
    rm -rf "$DRB_HOME"
fi

info "Linking local repo to ${DRB_HOME}..."
ln -s "$SCRIPT_DIR" "$DRB_HOME"

# Create venv with all dependencies
info "Creating virtual environment..."
python3 -m venv "$DRB_HOME/venv"
VENV_PYTHON="$DRB_HOME/venv/bin/python"
VENV_PIP="$DRB_HOME/venv/bin/pip"

info "Installing pywebview..."
"$VENV_PIP" install --quiet pywebview

# Save engine config
"$VENV_PYTHON" -c "
import json
with open('$DRB_HOME/config.json', 'w') as f:
    json.dump({'engine': '$ENGINE'}, f, indent=2)
"

# Build default container image
DEFAULT_IMAGE=$("$VENV_PYTHON" -c "
import json
with open('$DRB_HOME/packs/python/pack.json') as f:
    print(json.load(f)['image'])
")
info "Building container image: ${DEFAULT_IMAGE}..."
$ENGINE build -t "$DEFAULT_IMAGE" "$DRB_HOME/packs/python/"

# Build JavaScript container image
JS_IMAGE=$("$VENV_PYTHON" -c "
import json
with open('$DRB_HOME/packs/javascript/pack.json') as f:
    print(json.load(f)['image'])
")
info "Building container image: ${JS_IMAGE}..."
$ENGINE build -t "$JS_IMAGE" "$DRB_HOME/packs/javascript/"

# Build Ruby container image
RUBY_IMAGE=$("$VENV_PYTHON" -c "
import json
with open('$DRB_HOME/packs/ruby/pack.json') as f:
    print(json.load(f)['image'])
")
info "Building container image: ${RUBY_IMAGE}..."
$ENGINE build -t "$RUBY_IMAGE" "$DRB_HOME/packs/ruby/"

# Create bin symlink
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "${DRB_HOME}/bin/drb"
ln -sf "${DRB_HOME}/bin/drb" "${BIN_DIR}/drb"

# Ensure PATH includes BIN_DIR
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    # Detect shell profile
    SHELL_NAME="$(basename "$SHELL")"
    case "$SHELL_NAME" in
        zsh)  PROFILE="${HOME}/.zshrc" ;;
        bash)
            if [ -f "${HOME}/.bash_profile" ]; then
                PROFILE="${HOME}/.bash_profile"
            else
                PROFILE="${HOME}/.bashrc"
            fi
            ;;
        *)    PROFILE="${HOME}/.profile" ;;
    esac

    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

    # Only add if not already present
    if ! grep -qF '.local/bin' "$PROFILE" 2>/dev/null; then
        info "Adding ${BIN_DIR} to PATH in ${PROFILE}..."
        echo "" >> "$PROFILE"
        echo "# Added by dont-rust-bro" >> "$PROFILE"
        echo "$PATH_LINE" >> "$PROFILE"
        info "Run 'source ${PROFILE}' or open a new terminal for PATH changes to take effect."
    else
        info "${BIN_DIR} already referenced in ${PROFILE}."
    fi
fi

# Register Claude Code hooks
info "Registering Claude Code hooks..."
mkdir -p "$(dirname "$CLAUDE_SETTINGS")"

if [ -f "$CLAUDE_SETTINGS" ]; then
    # Merge hooks into existing settings using python
    "$VENV_PYTHON" -c "
import json, sys

settings_path = '$CLAUDE_SETTINGS'
with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault('hooks', {})

drb_hooks = {
    'UserPromptSubmit': {'hooks': [{'type': 'command', 'command': '${BIN_DIR}/drb show'}]},
    'Stop': {'hooks': [{'type': 'command', 'command': '${BIN_DIR}/drb hide'}]},
}

for event, matcher_group in drb_hooks.items():
    event_groups = hooks.setdefault(event, [])
    # Remove existing drb matcher groups
    event_groups = [g for g in event_groups
                    if not any('drb' in h.get('command', '') for h in g.get('hooks', []))]
    event_groups.append(matcher_group)
    hooks[event] = event_groups

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
"
else
    "$VENV_PYTHON" -c "
import json
settings = {
    'hooks': {
        'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': '${BIN_DIR}/drb show'}]}],
        'Stop': [{'hooks': [{'type': 'command', 'command': '${BIN_DIR}/drb hide'}]}],
    }
}
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2)
"
fi

info "Installation complete! (local dev mode)"
info ""
info "Container engine: ${ENGINE}"
info "DRB_HOME: ${DRB_HOME} -> ${SCRIPT_DIR}"
info "Commands:"
info "  drb status     - Check daemon status"
info "  drb packs list - List installed problem packs"
info "  drb uninstall  - Remove everything"
info ""
info "The practice window will appear automatically when Claude starts working."
