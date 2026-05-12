#!/usr/bin/env sh
# ChatMarkdown one-line installer for macOS / Linux
# Usage: curl -fsSL https://www.chatmarkdown.org/install.sh | sh
#
# This script:
#   1. Detects Python >= 3.10 (offers to install if missing/outdated)
#   2. Installs pipx if not present
#   3. Installs chatmd via pipx
#   4. Verifies installation
#   5. Prints Quick Start guide
#
# Flags:
#   --dry-run   Show what would be done without executing
#
# Requirements: sh-compatible shell, curl or wget (for Python install)
# License: MIT

set -e

# --- Configuration ------------------------------------------------------------

REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
PACKAGE_NAME="chatmd"
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

# --- Helpers ------------------------------------------------------------------

info() { printf '\033[1;34m[info]\033[0m %s\n' "$1"; }
success() { printf '\033[1;32m[ok]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$1"; }
error() { printf '\033[1;31m[error]\033[0m %s\n' "$1"; exit 1; }

confirm() {
    printf '%s [Y/n] ' "$1"
    read -r answer
    case "$answer" in
        [nN]*) return 1 ;;
        *) return 0 ;;
    esac
}

run() {
    if [ "$DRY_RUN" = true ]; then
        info "[dry-run] $*"
    else
        "$@"
    fi
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

# --- Detect OS ----------------------------------------------------------------

detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Darwin) OS_TYPE="macos" ;;
        Linux)  OS_TYPE="linux" ;;
        *)      error "Unsupported OS: $OS. This script supports macOS and Linux." ;;
    esac
}

detect_linux_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
    elif command_exists lsb_release; then
        DISTRO="$(lsb_release -si | tr '[:upper:]' '[:lower:]')"
    else
        DISTRO="unknown"
    fi
}

# --- Python Detection & Installation -----------------------------------------

find_python() {
    # Try common Python binary names
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            PYTHON_CMD="$cmd"
            return 0
        fi
    done
    return 1
}

check_python_version() {
    version_output=$("$PYTHON_CMD" --version 2>&1)
    major=$(echo "$version_output" | sed 's/Python \([0-9]*\).*/\1/')
    minor=$(echo "$version_output" | sed 's/Python [0-9]*\.\([0-9]*\).*/\1/')

    if [ "$major" -ge "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
        return 0
    fi
    return 1
}

install_python_macos() {
    if command_exists brew; then
        info "Installing Python via Homebrew..."
        run brew install python
    else
        info "Homebrew not found. Installing Homebrew first..."
        if [ "$DRY_RUN" = true ]; then
            info "[dry-run] /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            info "[dry-run] brew install python"
        else
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Add brew to PATH for current session
            if [ -f /opt/homebrew/bin/brew ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [ -f /usr/local/bin/brew ]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
            brew install python
        fi
    fi
}

install_python_linux() {
    detect_linux_distro
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            info "Installing Python via apt..."
            run sudo apt update
            run sudo apt install -y python3 python3-pip python3-venv
            ;;
        fedora)
            info "Installing Python via dnf..."
            run sudo dnf install -y python3 python3-pip
            ;;
        centos|rhel|rocky|alma)
            info "Installing Python via yum/dnf..."
            if command_exists dnf; then
                run sudo dnf install -y python3 python3-pip
            else
                run sudo yum install -y python3 python3-pip
            fi
            ;;
        arch|manjaro)
            info "Installing Python via pacman..."
            run sudo pacman -Sy --noconfirm python python-pip
            ;;
        opensuse*|sles)
            info "Installing Python via zypper..."
            run sudo zypper install -y python3 python3-pip
            ;;
        *)
            error "Unsupported Linux distribution: $DISTRO. Please install Python $REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR+ manually."
            ;;
    esac
}

ensure_python() {
    if find_python && check_python_version; then
        success "Python found: $($PYTHON_CMD --version)"
        return 0
    fi

    if find_python; then
        warn "Python found but version too low: $($PYTHON_CMD --version)"
        warn "Python $REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR+ is required."
    else
        warn "Python not found on this system."
        warn "Python $REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR+ is required."
    fi

    if ! confirm "Install/update Python now?"; then
        echo ""
        echo "To install Python manually:"
        echo "  macOS:  brew install python"
        echo "  Ubuntu: sudo apt install python3 python3-pip python3-venv"
        echo "  Fedora: sudo dnf install python3 python3-pip"
        echo "  Or visit: https://www.python.org/downloads/"
        exit 1
    fi

    case "$OS_TYPE" in
        macos) install_python_macos ;;
        linux) install_python_linux ;;
    esac

    # Re-detect after install
    if ! find_python; then
        error "Python installation failed. Please install Python $REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR+ manually."
    fi
    if ! check_python_version; then
        error "Installed Python version still does not meet requirements: $($PYTHON_CMD --version)"
    fi
    success "Python installed: $($PYTHON_CMD --version)"
}

# --- pipx Detection & Installation -------------------------------------------

ensure_pipx() {
    # Prefer `python -m pipx` so we don't depend on PATH inside this shell.
    if "$PYTHON_CMD" -m pipx --version >/dev/null 2>&1; then
        success "pipx found: $($PYTHON_CMD -m pipx --version)"
        return 0
    fi

    info "Installing pipx via pip (this may take 30-60 seconds, please wait)..."
    # Stream pip output so users see download progress; do NOT suppress stderr.
    if ! run "$PYTHON_CMD" -m pip install --user --no-warn-script-location --upgrade pipx; then
        warn "pip install --user failed. Retrying with --break-system-packages..."
        run "$PYTHON_CMD" -m pip install --break-system-packages --user --no-warn-script-location --upgrade pipx \
            || error "Failed to install pipx. See the pip output above for details."
    fi

    info "Configuring PATH for pipx..."
    run "$PYTHON_CMD" -m pipx ensurepath

    # Try to make pipx available in current session
    export PATH="$HOME/.local/bin:$PATH"

    if "$PYTHON_CMD" -m pipx --version >/dev/null 2>&1; then
        success "pipx installed: $($PYTHON_CMD -m pipx --version)"
    else
        error "pipx was installed but cannot be invoked. Please open a new terminal and re-run the installer."
    fi
}

# --- ChatMD Installation -----------------------------------------------------

install_chatmd() {
    info "Installing $PACKAGE_NAME via pipx (downloading dependencies, please wait)..."
    # Always use `python -m pipx` to avoid relying on PATH in the current shell.
    run "$PYTHON_CMD" -m pipx install --force "$PACKAGE_NAME"
}

verify_installation() {
    # Refresh PATH
    export PATH="$HOME/.local/bin:$PATH"

    if command_exists chatmd; then
        success "chatmd installed: $(chatmd --version)"
        return 0
    fi

    # Try via python -m
    if "$PYTHON_CMD" -m chatmd --version >/dev/null 2>&1; then
        success "chatmd available via: $PYTHON_CMD -m chatmd"
        warn "Add ~/.local/bin to your PATH for direct 'chatmd' access."
        return 0
    fi

    error "Installation verification failed. Try restarting your terminal."
}

# --- Quick Start --------------------------------------------------------------

print_quickstart() {
    echo ""
    echo "======================================================="
    success "ChatMarkdown installed successfully!"
    echo ""
    echo "  Quick Start:"
    echo "    chatmd init my-workspace"
    echo "    cd my-workspace"
    echo "    chatmd config init"
    echo "    chatmd start"
    echo ""
    echo "  Documentation: https://chatmarkdown.org"
    echo "======================================================="
    echo ""
}

# --- Main ---------------------------------------------------------------------

main() {
    echo ""
    info "ChatMarkdown Installer"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        warn "Running in dry-run mode -- no changes will be made."
        echo ""
    fi

    detect_os
    ensure_python
    ensure_pipx
    install_chatmd
    verify_installation
    print_quickstart
}

main "$@"
