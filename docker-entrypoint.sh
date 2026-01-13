#!/bin/bash
# docker-entrypoint.sh
# Playwright用Dockerエントリポイント
#
# 環境変数:
#   USE_XVFB=1     : Xvfbを起動してheadedモードを有効化
#   VNC_PORT=5900  : VNCサーバーを指定ポートで起動
#   DISPLAY        : X11ディスプレイ（デフォルト: :99）
#   XVFB_WHD       : Xvfb解像度（デフォルト: 1920x1080x24）
#
# ユーザー設定:
#   コンテナはデフォルトでappuser（uid=1000）として実行されます。
#   --user $(id -u):$(id -g) を指定することでホストユーザーとして実行できます。

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."

    # Kill VNC server if running (started with setsid, so use pkill)
    pkill -x Xvnc 2>/dev/null || true

    # Kill websockify if running
    pkill -x websockify 2>/dev/null || true

    # Kill Xvfb if running
    if [ -n "$XVFB_PID" ]; then
        kill $XVFB_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# =============================================================================
# Xvfb Setup
# =============================================================================
start_xvfb() {
    local display="${DISPLAY:-:99}"
    local whd="${XVFB_WHD:-1920x1080x24}"

    log_info "Starting Xvfb on display $display with resolution $whd"

    # Parse resolution
    local width=$(echo $whd | cut -d'x' -f1)
    local height=$(echo $whd | cut -d'x' -f2)
    local depth=$(echo $whd | cut -d'x' -f3)

    # Start Xvfb
    Xvfb $display -screen 0 ${width}x${height}x${depth} -ac +extension GLX +render -noreset &
    XVFB_PID=$!

    # Wait for Xvfb to start
    local max_wait=10
    local waited=0
    while ! xdpyinfo -display $display >/dev/null 2>&1; do
        if [ $waited -ge $max_wait ]; then
            log_error "Xvfb failed to start within ${max_wait} seconds"
            exit 1
        fi
        sleep 0.5
        waited=$((waited + 1))
    done

    log_info "Xvfb started successfully (PID: $XVFB_PID)"
    export DISPLAY=$display
}

# =============================================================================
# VNC Server Setup (TigerVNC + noVNC)
# =============================================================================
start_vnc() {
    local port="${VNC_PORT:-5900}"
    local novnc_port="${NOVNC_PORT:-6080}"
    local display="${DISPLAY:-:99}"
    local rfb_port=$((port))
    local display_num="${display#:}"

    log_info "Starting TigerVNC server on port $port"

    # Create VNC password file (empty password for no authentication)
    mkdir -p ~/.vnc
    echo "" | vncpasswd -f > ~/.vnc/passwd 2>/dev/null || true
    chmod 600 ~/.vnc/passwd 2>/dev/null || true

    # Start TigerVNC server in a new session (setsid) so it survives exec
    # This ensures Xvnc continues running even after the shell is replaced
    setsid Xvnc :${display_num} \
        -geometry 1920x1080 \
        -depth 24 \
        -rfbport ${rfb_port} \
        -SecurityTypes None \
        -localhost no \
        -alwaysshared \
        -AcceptSetDesktopSize \
        </dev/null >/dev/null 2>&1 &

    # Update DISPLAY to use VNC display
    export DISPLAY=:${display_num}

    # Wait for Xvnc to start and verify it's running
    local max_wait=10
    local waited=0
    while ! xdpyinfo -display $DISPLAY >/dev/null 2>&1; do
        if [ $waited -ge $max_wait ]; then
            log_error "TigerVNC failed to start within ${max_wait} seconds"
            exit 1
        fi
        sleep 0.5
        waited=$((waited + 1))
    done

    log_info "TigerVNC server started on display $DISPLAY (port $port)"

    # Start noVNC (web-based VNC client) in a new session
    setsid websockify --web=/usr/share/novnc/ ${novnc_port} localhost:${rfb_port} \
        </dev/null >/dev/null 2>&1 &

    log_info "Connect with: vncviewer localhost:$port"
    log_info "Or use noVNC: http://localhost:${novnc_port}/vnc.html"
}

# =============================================================================
# Main
# =============================================================================

# Set HOME based on the running user
# This handles both default user (ubuntu:1000) and arbitrary --user overrides
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

if [ "$CURRENT_UID" = "0" ]; then
    export HOME=/root
elif [ -z "$HOME" ] || [ ! -d "$HOME" ] || [ ! -w "$HOME" ]; then
    # Try to find home from passwd, fallback to /tmp
    PASSWD_HOME=$(getent passwd "$CURRENT_UID" 2>/dev/null | cut -d: -f6)
    if [ -n "$PASSWD_HOME" ] && [ -d "$PASSWD_HOME" ] && [ -w "$PASSWD_HOME" ]; then
        export HOME="$PASSWD_HOME"
    else
        export HOME=/tmp
        log_warn "HOME not available, using /tmp as HOME"
    fi
fi

# =============================================================================
# Fix volume mount permissions (Chrome data directory)
# =============================================================================
CHROME_DATA_DIR="$HOME/.config/google-chrome"
if [ -d "$CHROME_DATA_DIR" ] && [ ! -w "$CHROME_DATA_DIR" ]; then
    log_warn "Chrome data directory not writable, attempting to fix..."
    # Try to fix ownership if we have sudo access or are root
    if [ "$CURRENT_UID" = "0" ]; then
        chown -R "$CURRENT_UID:$CURRENT_GID" "$CHROME_DATA_DIR" 2>/dev/null && \
            log_info "Fixed Chrome data directory ownership" || \
            log_warn "Failed to fix Chrome data directory ownership"
    else
        log_warn "Chrome data directory is not writable. Run as root or delete volume:"
        log_warn "  docker volume rm note-mcp_chrome-data"
    fi
fi

# =============================================================================
# Fix volume mount permissions (Application data directory)
# =============================================================================
APP_DATA_DIR="/app/data"
if [ -d "$APP_DATA_DIR" ]; then
    if [ ! -w "$APP_DATA_DIR" ]; then
        log_warn "Application data directory not writable, attempting to fix..."
        if [ "$CURRENT_UID" = "0" ]; then
            chown -R "$CURRENT_UID:$CURRENT_GID" "$APP_DATA_DIR" 2>/dev/null && \
                log_info "Fixed application data directory ownership" || \
                log_warn "Failed to fix application data directory ownership"
        else
            log_warn "Application data directory is not writable."
            log_warn "To fix, run once as root or delete the volume:"
            log_warn "  docker volume rm note-mcp_investigator-data"
            log_warn "Using /tmp as fallback for data storage."
            export APP_DATA_DIR="/tmp"
        fi
    fi
else
    # Create directory if it doesn't exist
    mkdir -p "$APP_DATA_DIR" 2>/dev/null && \
        log_info "Created application data directory: $APP_DATA_DIR" || \
        log_warn "Failed to create application data directory"
fi

# Check if we should start display server
if [ -n "${VNC_PORT}" ]; then
    # TigerVNC server provides its own X server, no need for Xvfb
    start_vnc
elif [ "${USE_XVFB}" = "1" ] || [ "${USE_XVFB}" = "true" ]; then
    start_xvfb
elif [ -n "${DISPLAY}" ] && [ "${DISPLAY}" != ":99" ]; then
    # Using external display (X11 forwarding)
    log_info "Using external display: $DISPLAY"

    # Verify display is accessible
    if ! xdpyinfo >/dev/null 2>&1; then
        log_warn "Cannot connect to display $DISPLAY. Make sure X11 forwarding is configured correctly."
    fi
else
    # Headless mode
    log_info "Running in headless mode"
    log_info "To enable headed mode, set USE_XVFB=1 or provide DISPLAY"
fi

# Print environment info
log_info "Environment:"
log_info "  User: $(id -u):$(id -g)"
log_info "  HOME=$HOME"
log_info "  DISPLAY=$DISPLAY"
log_info "  PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH:-not set}"
log_info "  INVESTIGATOR_MODE=${INVESTIGATOR_MODE:-not set}"
log_info "  Python: $(python --version 2>&1)"

# Execute the command
log_info "Executing: $@"
exec "$@"
