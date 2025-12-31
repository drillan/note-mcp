"""Tests for file-based session management."""

from __future__ import annotations

import time
from pathlib import Path

from note_mcp.auth.file_session import FileBasedSessionManager
from note_mcp.models import Session


class TestFileBasedSessionManager:
    """Tests for FileBasedSessionManager."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test session save and load cycle."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        session = Session(
            cookies={"test_cookie": "test_value"},
            user_id="test_user_id",
            username="test_username",
            created_at=int(time.time()),
        )

        manager.save(session)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.username == "test_username"
        assert loaded.user_id == "test_user_id"
        assert loaded.cookies == {"test_cookie": "test_value"}

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Test loading when no session file exists."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        loaded = manager.load()
        assert loaded is None

    def test_has_session(self, tmp_path: Path) -> None:
        """Test has_session returns correct values."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        session = Session(
            cookies={"test": "cookie"},
            user_id="test_user",
            username="test_username",
            created_at=int(time.time()),
        )

        assert manager.has_session() is False

        manager.save(session)
        assert manager.has_session() is True

    def test_clear(self, tmp_path: Path) -> None:
        """Test session clear deletes the file."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        session = Session(
            cookies={"test": "cookie"},
            user_id="test_user",
            username="test_username",
            created_at=int(time.time()),
        )

        manager.save(session)
        assert manager.has_session() is True

        manager.clear()
        assert manager.has_session() is False

    def test_clear_nonexistent(self, tmp_path: Path) -> None:
        """Test clear does not raise when file does not exist."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        # Should not raise
        manager.clear()
        assert manager.has_session() is False

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test that save creates the data directory if it doesn't exist."""
        nested_dir = tmp_path / "nested" / "data" / "dir"
        manager = FileBasedSessionManager(data_dir=nested_dir)
        session = Session(
            cookies={"test": "cookie"},
            user_id="test_user",
            username="test_username",
            created_at=int(time.time()),
        )

        manager.save(session)

        assert nested_dir.exists()
        assert manager.has_session() is True

    def test_load_corrupted_file(self, tmp_path: Path) -> None:
        """Test loading corrupted session file returns None."""
        manager = FileBasedSessionManager(data_dir=tmp_path)

        # Create a corrupted session file
        tmp_path.mkdir(parents=True, exist_ok=True)
        session_file = tmp_path / "session.json"
        session_file.write_text("not valid json", encoding="utf-8")

        loaded = manager.load()
        assert loaded is None

    def test_session_with_expires_at(self, tmp_path: Path) -> None:
        """Test session with expiration timestamp."""
        manager = FileBasedSessionManager(data_dir=tmp_path)
        expires_at = int(time.time()) + 3600  # 1 hour from now
        session = Session(
            cookies={"test": "cookie"},
            user_id="test_user",
            username="test_username",
            expires_at=expires_at,
            created_at=int(time.time()),
        )

        manager.save(session)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.expires_at == expires_at
        assert not loaded.is_expired()
