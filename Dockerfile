# note-mcp Dockerfile
# Playwright対応Dockerイメージ（Xvfb/X11サポート付き）
#
# ビルド:
#   docker build -t note-mcp .
#
# 実行モード:
#   1. Headless (デフォルト):
#      docker run --rm --ipc=host note-mcp pytest
#
#   2. Headed with Xvfb (テスト可視化):
#      docker run --rm --ipc=host -e USE_XVFB=1 note-mcp pytest
#
#   3. X11 forwarding (ホストディスプレイ):
#      docker run --rm --ipc=host -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix note-mcp pytest
#
# 参考:
#   https://playwright.dev/python/docs/docker
#   https://playwright.dev/docs/ci

# =============================================================================
# Stage 1: Base image with Playwright browsers
# =============================================================================
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Xvfb and X11 utilities for headed mode support
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    xauth \
    # VNC support (optional, for remote viewing)
    x11vnc \
    # Fonts for proper rendering
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 2: Application setup
# =============================================================================
FROM base AS app

# Set working directory
WORKDIR /app

# Install uv for dependency management
# https://docs.astral.sh/uv/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for better layer caching)
# README.md is needed by hatchling build backend
COPY pyproject.toml README.md ./

# Install dependencies using uv
# --no-cache: Don't cache packages to reduce image size
RUN uv sync --no-cache --no-dev

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# =============================================================================
# Stage 3: Development image with dev dependencies
# =============================================================================
FROM app AS dev

# Install dev dependencies
RUN uv sync --no-cache --group dev

# =============================================================================
# Environment configuration
# =============================================================================

# Playwright configuration
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Python configuration
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default display settings for Xvfb
ENV DISPLAY=:99
ENV XVFB_WHD=1920x1080x24

# Control flags
# USE_XVFB=1 : Start Xvfb before running command
# VNC_PORT=5900 : Enable VNC server on specified port
ENV USE_XVFB=0
ENV VNC_PORT=

# =============================================================================
# Entrypoint script
# =============================================================================
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command: run tests
CMD ["uv", "run", "pytest", "-v"]
