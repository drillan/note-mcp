"""Integration tests for investigator MCP tools.

Tests are split into:
- Local tests: Run without Docker, use mocks
- Docker tests: Require Docker environment with browser/proxy (@pytest.mark.docker)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from note_mcp.auth.file_session import FileBasedSessionManager
from note_mcp.investigator.core import CaptureSessionManager
from note_mcp.models import Session

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


class TestFileBasedSessionManagerIntegration:
    """Integration tests for FileBasedSessionManager."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> FileBasedSessionManager:
        """Create a FileBasedSessionManager with temp directory."""
        return FileBasedSessionManager(data_dir=tmp_path)

    @pytest.fixture
    def sample_session(self) -> Session:
        """Create a sample session for testing."""
        return Session(
            cookies={"note_login": "test_value", "note_session": "session123"},
            user_id="user_12345",
            username="test_username",
            created_at=int(time.time()),
        )

    def test_save_and_load_round_trip(self, manager: FileBasedSessionManager, sample_session: Session) -> None:
        """Test that session can be saved and loaded correctly."""
        manager.save(sample_session)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.username == sample_session.username
        assert loaded.user_id == sample_session.user_id
        assert loaded.cookies == sample_session.cookies

    def test_clear_removes_session(self, manager: FileBasedSessionManager, sample_session: Session) -> None:
        """Test that clear removes the session file."""
        manager.save(sample_session)
        assert manager.has_session() is True

        manager.clear()
        assert manager.has_session() is False
        assert manager.load() is None

    def test_has_session_empty(self, manager: FileBasedSessionManager) -> None:
        """Test has_session returns False when no session exists."""
        assert manager.has_session() is False

    def test_load_nonexistent(self, manager: FileBasedSessionManager) -> None:
        """Test load returns None when no session exists."""
        assert manager.load() is None

    def test_session_persistence(self, tmp_path: Path, sample_session: Session) -> None:
        """Test session persists across manager instances."""
        # Save with first manager
        manager1 = FileBasedSessionManager(data_dir=tmp_path)
        manager1.save(sample_session)

        # Load with second manager
        manager2 = FileBasedSessionManager(data_dir=tmp_path)
        loaded = manager2.load()

        assert loaded is not None
        assert loaded.username == sample_session.username


class TestCaptureSessionManagerIntegration:
    """Integration tests for CaptureSessionManager."""

    @pytest.fixture(autouse=True)
    def reset_manager(self) -> Generator[None]:
        """Reset singleton state before and after each test."""
        # Reset before test
        CaptureSessionManager._instance = None
        CaptureSessionManager._domain = None
        CaptureSessionManager._output_file = None

        yield

        # Reset after test
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

    def test_singleton_instance_is_none_initially(self) -> None:
        """Test that singleton instance is None by default."""
        assert CaptureSessionManager._instance is None


class TestInvestigatorModeEnvironment:
    """Test investigator mode environment variable handling."""

    def test_investigator_mode_env_not_set(self) -> None:
        """Test behavior when INVESTIGATOR_MODE is not set."""
        # Save original value
        original = os.environ.get("INVESTIGATOR_MODE")

        try:
            # Ensure not set
            os.environ.pop("INVESTIGATOR_MODE", None)

            # Should be able to import server without error
            # Investigator tools should not be registered
            from note_mcp.server import mcp

            # Count tools - should have base tools only (13)
            tools = list(mcp._tool_manager._tools.keys())
            assert "note_login" in tools
            assert "investigator_start_capture" not in tools

        finally:
            # Restore original value
            if original:
                os.environ["INVESTIGATOR_MODE"] = original


class TestServerIntegration:
    """Test server integration with investigator tools."""

    def test_base_tools_always_available(self) -> None:
        """Test that base note.com tools are always available."""
        from note_mcp.server import mcp

        tools = list(mcp._tool_manager._tools.keys())

        # Base tools should always be present
        base_tools = [
            "note_login",
            "note_check_auth",
            "note_logout",
            "note_create_draft",
            "note_get_article",
            "note_update_article",
            "note_list_articles",
        ]

        for tool in base_tools:
            assert tool in tools, f"Base tool {tool} not found"


# Docker-only tests
@pytest.mark.docker
class TestDockerOnlyWorkflow:
    """Tests that require Docker environment.

    These tests are skipped unless running in Docker with browser and proxy.
    Run with: pytest -m docker
    """

    @pytest.fixture(autouse=True)
    async def cleanup(self) -> AsyncGenerator[None]:
        """Clean up session after test."""
        yield
        await CaptureSessionManager.close()

    @pytest.mark.asyncio
    async def test_full_capture_workflow(self) -> None:
        """Test full capture workflow: start -> navigate -> capture -> stop.

        This test requires:
        - Docker environment
        - VNC display or Xvfb
        - mitmproxy available
        """
        pytest.skip("Requires Docker environment")

        # This would be the full workflow test
        # session = await CaptureSessionManager.get_or_create("note.com", 8080)
        # result = await session.navigate("https://note.com/")
        # assert "Navigated" in result
        # traffic = session.get_traffic()
        # assert isinstance(traffic, list)
        # await CaptureSessionManager.close()
