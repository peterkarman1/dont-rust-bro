#!/usr/bin/env bash
set -euo pipefail

DRB_HOME="${HOME}/.dont-rust-bro"
DRB_REPO="https://github.com/peterkarman1/dont-rust-bro.git"
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

# Check dependencies
if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found."
    exit 1
fi

if ! python3 -c "import tkinter" &>/dev/null; then
    error "tkinter is required. Install with: brew install python-tk@3.12"
    exit 1
fi

# Install or update
if [ -d "$DRB_HOME/.git" ]; then
    info "Updating existing installation..."
    git -C "$DRB_HOME" pull --quiet
else
    info "Installing dont-rust-bro to ${DRB_HOME}..."
    git clone --quiet "$DRB_REPO" "$DRB_HOME"
fi

# Ensure pytest is available
if ! python3 -c "import pytest" &>/dev/null; then
    warn "pytest not found. Installing..."
    python3 -m pip install --quiet pytest
fi

# Create bin symlink
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "${DRB_HOME}/bin/drb"
ln -sf "${DRB_HOME}/bin/drb" "${BIN_DIR}/drb"

# Check PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    warn "${BIN_DIR} is not in your PATH."
    warn "Add this to your shell profile:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Register Claude Code hooks
info "Registering Claude Code hooks..."
mkdir -p "$(dirname "$CLAUDE_SETTINGS")"

if [ -f "$CLAUDE_SETTINGS" ]; then
    # Merge hooks into existing settings using python
    python3 -c "
import json, sys

settings_path = '$CLAUDE_SETTINGS'
with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault('hooks', {})

drb_hooks = {
    'SubagentStart': {'type': 'command', 'command': '${BIN_DIR}/drb show'},
    'SubagentStop': {'type': 'command', 'command': '${BIN_DIR}/drb agent-stop'},
    'Stop': {'type': 'command', 'command': '${BIN_DIR}/drb hide'},
}

for event, hook in drb_hooks.items():
    event_hooks = hooks.setdefault(event, [])
    # Remove existing drb hooks
    event_hooks = [h for h in event_hooks if 'drb' not in h.get('command', '')]
    event_hooks.append(hook)
    hooks[event] = event_hooks

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
"
else
    python3 -c "
import json
settings = {
    'hooks': {
        'SubagentStart': [{'type': 'command', 'command': '${BIN_DIR}/drb show'}],
        'SubagentStop': [{'type': 'command', 'command': '${BIN_DIR}/drb agent-stop'}],
        'Stop': [{'type': 'command', 'command': '${BIN_DIR}/drb hide'}],
    }
}
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2)
"
fi

info "Installation complete!"
info ""
info "Commands:"
info "  drb status     - Check daemon status"
info "  drb packs list - List installed problem packs"
info "  drb update     - Pull latest problems"
info ""
info "The practice window will appear automatically when Claude agents are working."
