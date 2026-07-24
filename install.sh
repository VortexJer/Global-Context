#!/usr/bin/env bash
# Global Context installer for macOS, Linux and Git Bash on Windows.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/VortexJer/Global-Context/main/install.sh | bash
#   curl -fsSL ... | bash -s -- --ai all

set -euo pipefail

REPO="${GC_REPO:-VortexJer/Global-Context}"
BRANCH="${GC_BRANCH:-main}"

# Use Python to get the home directory in a cross-platform way (matches Path.home())
USER_HOME="${GC_USER_HOME:-$(python3 -c "from pathlib import Path; print(Path.home())" 2>/dev/null || echo "$HOME")}"
INSTALL_DIR="${GC_INSTALL_DIR:-$USER_HOME/.globalcontext}"
BIN_DIR="$INSTALL_DIR/bin"
PWSH_PROFILE="$USER_HOME/Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1"

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ai)
                shift
                SELECTED_AI="$1"
                ;;
            --local)
                LOCAL_INSTALL=1
                ;;
            --uninstall)
                UNINSTALL=1
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
        shift
    done
}

LOCAL_INSTALL=${LOCAL_INSTALL:-0}
UNINSTALL=${UNINSTALL:-0}
SELECTED_AI="${SELECTED_AI:-}"
parse_args "$@"

# Pick a Python interpreter (python3, then python, then py).
if command -v python3 >/dev/null 2>&1; then GC_PY=python3
elif command -v python >/dev/null 2>&1; then GC_PY=python
else GC_PY=py; fi

# Strip the "# Global Context" block from a file (function/export block).
strip_gc_block() {
    local target="$1"
    [[ -f "$target" ]] || return 0
    "$GC_PY" - "$target" << 'PY'
import re, sys
p = sys.argv[1]
with open(p, encoding="utf-8") as f:
    txt = f.read()
new = re.sub(r"\n?# Global Context\n.*?\n\}\n?", "\n", txt, flags=re.S)
if new != txt:
    with open(p, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"  Cleaned {p}")
PY
}

if [[ "$UNINSTALL" -eq 1 ]]; then
    echo "Uninstalling Global Context ..."

    # 1. Remove AI integrations (Claude hooks, Kimi/Codex/Gemini skills).
    if [[ -f "$BIN_DIR/globalcontext.py" ]]; then
        "$GC_PY" "$BIN_DIR/globalcontext.py" uninstall --ai all || true
    fi

    # 2. Remove the shell function / PATH block from shell rc files and PS profile.
    for rc in "$USER_HOME/.bashrc" "$USER_HOME/.zshrc" "$USER_HOME/.bash_profile" "$PWSH_PROFILE"; do
        strip_gc_block "$rc"
    done

    # 3. Remove the install directory.
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        echo "  Removed $INSTALL_DIR"
    fi

    echo "Global Context uninstalled. Restart your terminal to clear PATH."
    exit 0
fi

if command -v git >/dev/null 2>&1 && [[ "$LOCAL_INSTALL" -eq 0 ]]; then
    echo "Installing Global Context from https://github.com/$REPO ..."
    rm -rf "$INSTALL_DIR"
    git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$INSTALL_DIR"
else
    echo "Installing Global Context from local source ..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cp -R "$SCRIPT_DIR"/* "$INSTALL_DIR/"
fi

# Ensure wrapper is executable
chmod +x "$BIN_DIR/globalcontext" "$BIN_DIR/globalcontext.py" "$BIN_DIR/globalcontext.ps1" 2>/dev/null || true

# Add a shell function so the command works in bash/zsh/Git Bash.
# Windows/Git Bash often cannot run extension-less scripts from PATH.
ensure_shell_function() {
    local shell_rc=""
    if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        shell_rc="$USER_HOME/.zshrc"
    elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$SHELL" == *"bash"* ]]; then
        shell_rc="$USER_HOME/.bashrc"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        shell_rc="$USER_HOME/.bash_profile"
    fi

    # Fallback to .bashrc if nothing detected
    if [[ -z "$shell_rc" ]]; then
        shell_rc="$USER_HOME/.bashrc"
    fi

    if ! grep -q "# Global Context" "$shell_rc" 2>/dev/null; then
        mkdir -p "$(dirname "$shell_rc")"
        cat >> "$shell_rc" << EOF

# Global Context
export PATH="$BIN_DIR:\$PATH"
globalcontext() {
    python3 "$BIN_DIR/globalcontext.py" "\$@"
}
EOF
        echo "Added globalcontext function to $shell_rc" >&2
    fi
    echo "$shell_rc"
}

SHELL_RC=$(ensure_shell_function)

# Also try to add a PowerShell function for Windows users
if command -v powershell >/dev/null 2>&1 || command -v pwsh >/dev/null 2>&1; then
    mkdir -p "$(dirname "$PWSH_PROFILE")"
    if ! grep -q "# Global Context" "$PWSH_PROFILE" 2>/dev/null; then
        cat >> "$PWSH_PROFILE" << 'EOF'

# Global Context
function globalcontext {
    $gc = "$env:USERPROFILE\.globalcontext\bin\globalcontext.py"
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 $gc @args }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python $gc @args }
    else { & python3 $gc @args }
}
EOF
        echo "Added globalcontext function to PowerShell profile"
    fi
fi

# Make globalcontext available in the current shell
export PATH="$BIN_DIR:$PATH"
globalcontext() {
    python3 "$BIN_DIR/globalcontext.py" "$@"
}

# Run AI integrations setup
if [[ -n "$SELECTED_AI" ]]; then
    globalcontext install --ai "$SELECTED_AI"
else
    globalcontext install
fi

echo ""
echo "Global Context installed at $INSTALL_DIR"
echo "Restart your terminal or run: source $SHELL_RC"
