"""Contract tests for MCP tools.

Tests the schema and structure of all MCP tools without making actual API calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

from note_mcp.server import mcp


def get_tools() -> dict[str, Any]:
    """Get all registered tools synchronously."""
    return asyncio.get_event_loop().run_until_complete(mcp._tool_manager.get_tools())


class TestMCPServerConfiguration:
    """Tests for MCP server configuration."""

    def test_server_name(self) -> None:
        """Test that server has correct name."""
        assert mcp.name == "note-mcp"

    def test_server_has_tools(self) -> None:
        """Test that server has registered tools."""
        tools = get_tools()
        assert len(tools) > 0


class TestToolSchemas:
    """Tests for tool schemas."""

    def test_note_login_tool_exists(self) -> None:
        """Test that note_login tool is registered."""
        tools = get_tools()
        assert "note_login" in tools

    def test_note_login_schema(self) -> None:
        """Test note_login tool has correct schema."""
        tools = get_tools()
        login_tool = tools["note_login"]

        # note_login takes optional timeout parameter
        assert login_tool.parameters is not None
        schema = login_tool.parameters
        assert "properties" in schema
        assert "timeout" in schema["properties"]
        assert schema["properties"]["timeout"]["type"] == "integer"

    def test_note_check_auth_tool_exists(self) -> None:
        """Test that note_check_auth tool is registered."""
        tools = get_tools()
        assert "note_check_auth" in tools

    def test_note_check_auth_schema(self) -> None:
        """Test note_check_auth tool has correct schema."""
        tools = get_tools()
        check_tool = tools["note_check_auth"]

        # note_check_auth takes no required parameters
        assert check_tool.parameters is not None
        schema = check_tool.parameters
        # Should have empty properties
        assert schema.get("properties", {}) == {}

    def test_note_logout_tool_exists(self) -> None:
        """Test that note_logout tool is registered."""
        tools = get_tools()
        assert "note_logout" in tools

    def test_note_logout_schema(self) -> None:
        """Test note_logout tool has correct schema."""
        tools = get_tools()
        logout_tool = tools["note_logout"]

        # note_logout takes no required parameters
        assert logout_tool.parameters is not None
        schema = logout_tool.parameters
        required = schema.get("required", [])
        assert len(required) == 0

    def test_note_create_draft_tool_exists(self) -> None:
        """Test that note_create_draft tool is registered."""
        tools = get_tools()
        assert "note_create_draft" in tools

    def test_note_create_draft_schema(self) -> None:
        """Test note_create_draft tool has correct schema."""
        tools = get_tools()
        create_tool = tools["note_create_draft"]

        assert create_tool.parameters is not None
        schema = create_tool.parameters
        assert "properties" in schema

        # Required parameters
        assert "title" in schema["properties"]
        assert "body" in schema["properties"]

        # Optional parameters
        assert "tags" in schema["properties"]

        # Check required fields
        required = schema.get("required", [])
        assert "title" in required
        assert "body" in required

    def test_note_update_article_tool_exists(self) -> None:
        """Test that note_update_article tool is registered."""
        tools = get_tools()
        assert "note_update_article" in tools

    def test_note_update_article_schema(self) -> None:
        """Test note_update_article tool has correct schema."""
        tools = get_tools()
        update_tool = tools["note_update_article"]

        assert update_tool.parameters is not None
        schema = update_tool.parameters
        assert "properties" in schema

        # Required parameters
        assert "article_id" in schema["properties"]
        assert "title" in schema["properties"]
        assert "body" in schema["properties"]

        # Check required fields
        required = schema.get("required", [])
        assert "article_id" in required
        assert "title" in required
        assert "body" in required

    def test_note_upload_image_tool_exists(self) -> None:
        """Test that note_upload_image tool is registered."""
        tools = get_tools()
        assert "note_upload_image" in tools

    def test_note_upload_image_schema(self) -> None:
        """Test note_upload_image tool has correct schema."""
        tools = get_tools()
        upload_tool = tools["note_upload_image"]

        assert upload_tool.parameters is not None
        schema = upload_tool.parameters
        assert "properties" in schema

        # Required parameters
        assert "file_path" in schema["properties"]

        # Check required fields
        required = schema.get("required", [])
        assert "file_path" in required

    def test_note_show_preview_tool_exists(self) -> None:
        """Test that note_show_preview tool is registered."""
        tools = get_tools()
        assert "note_show_preview" in tools

    def test_note_show_preview_schema(self) -> None:
        """Test note_show_preview tool has correct schema."""
        tools = get_tools()
        preview_tool = tools["note_show_preview"]

        assert preview_tool.parameters is not None
        schema = preview_tool.parameters
        assert "properties" in schema

        # Required parameters
        assert "article_key" in schema["properties"]

        # Check required fields
        required = schema.get("required", [])
        assert "article_key" in required


class TestToolDescriptions:
    """Tests for tool descriptions."""

    def test_all_tools_have_descriptions(self) -> None:
        """Test that all tools have non-empty descriptions."""
        tools = get_tools()
        for name, tool in tools.items():
            assert tool.description, f"Tool {name} has no description"
            assert len(tool.description) > 10, f"Tool {name} has too short description"

    def test_tool_descriptions_are_in_japanese(self) -> None:
        """Test that tool descriptions contain Japanese text."""
        tools = get_tools()
        for name, tool in tools.items():
            description = tool.description or ""
            # Check for at least one Japanese character (Hiragana, Katakana, or Kanji)
            has_japanese = any(
                "\u3040" <= char <= "\u30ff"  # Hiragana and Katakana
                or "\u4e00" <= char <= "\u9fff"  # Kanji
                for char in description
            )
            assert has_japanese, f"Tool {name} description should be in Japanese"
