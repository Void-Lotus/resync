#!/usr/bin/env bash
#
# resync - Modern Arch Linux System Replicator & Dotfile Sync Engine
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure we are not executing as root directly
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo "[!] Please run setup.sh as a standard user (sudo will be invoked when needed)."
    exit 1
fi

# Ensure Python 3 is installed
if ! command -v python3 &>/dev/null; then
    echo "[*] Installing python3..."
    sudo pacman -S --needed --noconfirm python
fi

# Launch resync CLI/TUI orchestrator
python3 resync.py "$@"
