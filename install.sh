#!/bin/bash
# install.sh - Install murmur dictation tool
# Idempotent - safe to run multiple times.

set -euo pipefail

VENV_DIR="$HOME/.local/share/murmur/venv"
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
echo "Installing murmur package..."
uv pip install "$SCRIPT_DIR[cuda]" --python "$VENV_DIR/bin/python" -q
ok "Package installed"

# 3. Symlink entry points
echo ""
echo "Creating symlinks..."
mkdir -p "$BIN_DIR"

for bin in murmur-daemon murmur-client; do
    ln -sf "$VENV_DIR/bin/$bin" "$BIN_DIR/$bin"
    ok "Linked $bin -> $BIN_DIR/$bin"
done

ln -sf "$SCRIPT_DIR/scripts/murmur-toggle.sh" "$BIN_DIR/murmur-toggle.sh"
ok "Linked murmur-toggle.sh -> $BIN_DIR/murmur-toggle.sh"

# 4. Create data directory
mkdir -p "$HOME/.local/share/murmur"
ok "Data directory ready"

# 5. Install systemd service
echo ""
echo "Installing systemd service..."
mkdir -p "$SYSTEMD_DIR"
cp "$SCRIPT_DIR/systemd/murmur.service" "$SYSTEMD_DIR/murmur.service"
systemctl --user daemon-reload
ok "Service installed"

# 6. Enable and start
systemctl --user enable murmur.service
systemctl --user restart murmur.service
ok "Service enabled and started"

echo ""
echo "============================================"
echo " Installation complete!"
echo "============================================"
echo ""
echo "Add this to your Niri config (~/.config/niri/config.kdl):"
echo ""
echo '  Mod+D { spawn "murmur-toggle.sh"; }'
echo ""
echo "Then reload: niri msg action reload-config"
echo ""
echo "First run will download the model (~500MB for small.en)."
echo "Watch progress: journalctl --user -u murmur -f"
echo ""
