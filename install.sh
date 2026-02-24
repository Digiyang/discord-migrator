#!/usr/bin/env bash
set -e

REPO="https://github.com/Digiyang/discord-migrator"
INSTALL_DIR="$HOME/.local/share/discord-migrator"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/discord-migrator"

# ── Check Python 3.10+ ────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10 or higher is required (found $(python3 --version))."
    exit 1
fi

# ── Clone or update ───────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating discord-migrator …"
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "Installing discord-migrator …"
    git clone "$REPO" "$INSTALL_DIR"
fi

# ── Virtual environment & dependencies ───────────────────────────────────────
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# ── Launcher script ───────────────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
exec "\$HOME/.local/share/discord-migrator/.venv/bin/python" \\
     "\$HOME/.local/share/discord-migrator/src/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

# ── PATH hint ─────────────────────────────────────────────────────────────────
echo ""
echo "✔  Installation complete."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "  ~/.local/bin is not in your PATH."
    echo "  Add this line to your ~/.bashrc or ~/.zshrc and restart your shell:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi
echo "  Run with: discord-migrator"
echo ""
