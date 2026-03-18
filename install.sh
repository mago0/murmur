#!/bin/bash
# install.sh - Install the dictation tool
# Idempotent - safe to run multiple times.

set -euo pipefail

VENV_DIR="$HOME/.local/share/dictation/venv"
BIN_DIR="$HOME/.local/bin"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
fail() { echo -e "${RED}[fail]${NC} $1"; }

# 1. Check system dependencies
echo "Checking system dependencies..."
MISSING=0

for cmd in pw-record wl-copy notify-send uv; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd found"
    else
        fail "$cmd not found"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "Install missing dependencies:"
    echo "  sudo apt install pipewire wl-clipboard libnotify-bin"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    exit 1
fi

# 2. Create venv and install package
echo ""
echo "Setting up Python environment..."
uv venv "$VENV_DIR" --python ">=3.11" -q
ok "Venv ready at $VENV_DIR"

echo ""
echo "Installing dictation package..."
uv pip install "$SCRIPT_DIR" --python "$VENV_DIR/bin/python" -q
ok "Package installed"

# 4. Symlink entry points
echo ""
echo "Creating symlinks..."
mkdir -p "$BIN_DIR"

for bin in dictation-daemon dictation-client; do
    ln -sf "$VENV_DIR/bin/$bin" "$BIN_DIR/$bin"
    ok "Linked $bin -> $BIN_DIR/$bin"
done

ln -sf "$SCRIPT_DIR/scripts/dictate-toggle.sh" "$BIN_DIR/dictate-toggle.sh"
ok "Linked dictate-toggle.sh -> $BIN_DIR/dictate-toggle.sh"

# 5. Create data directory
mkdir -p "$HOME/.local/share/dictation"
ok "Data directory ready"

# 6. Install systemd service
echo ""
echo "Installing systemd service..."
mkdir -p "$SYSTEMD_DIR"
cp "$SCRIPT_DIR/systemd/dictation.service" "$SYSTEMD_DIR/dictation.service"
systemctl --user daemon-reload
ok "Service installed"

# 7. Enable and start
systemctl --user enable dictation.service
systemctl --user restart dictation.service
ok "Service enabled and started"

echo ""
echo "============================================"
echo " Installation complete!"
echo "============================================"
echo ""
echo "Add this to your Niri config (~/.config/niri/config.kdl):"
echo ""
echo '  Mod+Shift+D { spawn "dictate-toggle.sh"; }'
echo ""
echo "Then reload: niri msg action reload-config"
echo ""
echo "First run will download the model (~500MB for small.en)."
echo "Watch progress: journalctl --user -u dictation -f"
echo ""
