"""Tests for CaptureSessionManager singleton."""

from __future__ import annotations

import pytest

from note_mcp.investigator.core import CaptureSessionManager


class TestCaptureSessionManager:
    """Tests for CaptureSessionManager."""

    @pytest.fixture(autouse=True)
    def reset_manager(self) -> None:
        """Reset singleton state before each test."""
        # Reset singleton state
        CaptureSessionManager._instance = None
        CaptureSessionManager._domain = None
        CaptureSessionManager._output_file = None

    def test_get_status_no_session(self) -> None:
        """Test get_status when no session is active."""
        status = CaptureSessionManager.get_status()

        assert status["active"] is False
        assert "domain" not in status
        assert "output_file" not in status

    def test_get_status_returns_dict(self) -> None:
        """Test that get_status returns a dictionary."""
        status = CaptureSessionManager.get_status()
        assert isinstance(status, dict)
