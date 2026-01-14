"""Contract tests for MCP tools.

Tests the schema and structure of all MCP tools without making actual API calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from note_mcp.server import mcp


def get_tools() -> dict[str, Any]:
    """Get all registered tools synchronously."""
    return asyncio.run(mcp._tool_manager.get_tools())


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

    def test_note_upload_eyecatch_tool_exists(self) -> None:
        """Test that note_upload_eyecatch tool is registered."""
        tools = get_tools()
        assert "note_upload_eyecatch" in tools

    def test_note_upload_eyecatch_schema(self) -> None:
        """Test note_upload_eyecatch tool schema matches exactly."""
        tools = get_tools()
        upload_tool = tools["note_upload_eyecatch"]

        assert upload_tool.parameters is not None
        schema = upload_tool.parameters
        assert "properties" in schema

        # Exact properties match (session must NOT be here)
        expected_properties = {"file_path", "note_id"}
        actual_properties = set(schema.get("properties", {}).keys())
        assert actual_properties == expected_properties, (
            f"Schema mismatch: "
            f"extra={actual_properties - expected_properties}, "
            f"missing={expected_properties - actual_properties}"
        )

        # Exact required match
        expected_required = {"file_path", "note_id"}
        actual_required = set(schema.get("required", []))
        assert actual_required == expected_required, (
            f"Required mismatch: "
            f"extra={actual_required - expected_required}, "
            f"missing={expected_required - actual_required}"
        )

    def test_note_upload_body_image_tool_exists(self) -> None:
        """Test that note_upload_body_image tool is registered."""
        tools = get_tools()
        assert "note_upload_body_image" in tools

    def test_note_upload_body_image_schema(self) -> None:
        """Test note_upload_body_image tool schema matches exactly."""
        tools = get_tools()
        upload_tool = tools["note_upload_body_image"]

        assert upload_tool.parameters is not None
        schema = upload_tool.parameters
        assert "properties" in schema

        # Exact properties match (session must NOT be here)
        expected_properties = {"file_path", "note_id"}
        actual_properties = set(schema.get("properties", {}).keys())
        assert actual_properties == expected_properties, (
            f"Schema mismatch: "
            f"extra={actual_properties - expected_properties}, "
            f"missing={expected_properties - actual_properties}"
        )

        # Exact required match
        expected_required = {"file_path", "note_id"}
        actual_required = set(schema.get("required", []))
        assert actual_required == expected_required, (
            f"Required mismatch: "
            f"extra={actual_required - expected_required}, "
            f"missing={expected_required - actual_required}"
        )

    def test_note_show_preview_tool_exists(self) -> None:
        """Test that note_show_preview tool is registered."""
        tools = get_tools()
        assert "note_show_preview" in tools

    def test_note_show_preview_schema(self) -> None:
        """Test note_show_preview tool schema matches exactly."""
        tools = get_tools()
        preview_tool = tools["note_show_preview"]

        assert preview_tool.parameters is not None
        schema = preview_tool.parameters
        assert "properties" in schema

        # Exact properties match (session must NOT be here)
        expected_properties = {"article_key"}
        actual_properties = set(schema.get("properties", {}).keys())
        assert actual_properties == expected_properties, (
            f"Schema mismatch: "
            f"extra={actual_properties - expected_properties}, "
            f"missing={expected_properties - actual_properties}"
        )

        # Exact required match
        expected_required = {"article_key"}
        actual_required = set(schema.get("required", []))
        assert actual_required == expected_required, (
            f"Required mismatch: "
            f"extra={actual_required - expected_required}, "
            f"missing={expected_required - actual_required}"
        )

    def test_note_get_preview_html_tool_exists(self) -> None:
        """Test that note_get_preview_html tool is registered."""
        tools = get_tools()
        assert "note_get_preview_html" in tools

    def test_note_get_preview_html_schema(self) -> None:
        """Test note_get_preview_html tool schema matches exactly."""
        tools = get_tools()
        preview_html_tool = tools["note_get_preview_html"]

        assert preview_html_tool.parameters is not None
        schema = preview_html_tool.parameters
        assert "properties" in schema

        # Exact properties match (session must NOT be here)
        expected_properties = {"article_key"}
        actual_properties = set(schema.get("properties", {}).keys())
        assert actual_properties == expected_properties, (
            f"Schema mismatch: "
            f"extra={actual_properties - expected_properties}, "
            f"missing={expected_properties - actual_properties}"
        )

        # Exact required match
        expected_required = {"article_key"}
        actual_required = set(schema.get("required", []))
        assert actual_required == expected_required, (
            f"Required mismatch: "
            f"extra={actual_required - expected_required}, "
            f"missing={expected_required - actual_required}"
        )

    def test_note_publish_article_tool_exists(self) -> None:
        """Test that note_publish_article tool is registered."""
        tools = get_tools()
        assert "note_publish_article" in tools

    def test_note_publish_article_schema(self) -> None:
        """Test note_publish_article tool has correct schema."""
        tools = get_tools()
        publish_tool = tools["note_publish_article"]

        assert publish_tool.parameters is not None
        schema = publish_tool.parameters
        assert "properties" in schema

        # Optional parameters (can publish existing draft or create new)
        assert "article_id" in schema["properties"]
        assert "title" in schema["properties"]
        assert "body" in schema["properties"]
        assert "tags" in schema["properties"]

        # All parameters are optional
        required = schema.get("required", [])
        assert len(required) == 0

    def test_note_list_articles_tool_exists(self) -> None:
        """Test that note_list_articles tool is registered."""
        tools = get_tools()
        assert "note_list_articles" in tools

    def test_note_list_articles_schema(self) -> None:
        """Test note_list_articles tool has correct schema."""
        tools = get_tools()
        list_tool = tools["note_list_articles"]

        assert list_tool.parameters is not None
        schema = list_tool.parameters
        assert "properties" in schema

        # Optional parameters
        assert "status" in schema["properties"]
        assert "page" in schema["properties"]
        assert "limit" in schema["properties"]

        # All parameters are optional
        required = schema.get("required", [])
        assert len(required) == 0


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


class TestNoInternalParamsExposed:
    """内部パラメータがMCPスキーマに漏れていないことを検証。

    Issue #238で発覚した問題の再発を防ぐためのテスト。
    セッション管理やコンテキストなど、MCP外部に公開すべきでない
    内部パラメータがスキーマに含まれていないことを全ツールで確認する。
    """

    INTERNAL_PARAMS = {"session", "ctx", "_session_manager", "self"}

    def test_all_tools_hide_internal_params(self) -> None:
        """全ツールで内部パラメータがスキーマに含まれていないことを確認。"""
        tools = get_tools()
        violations: list[str] = []

        for name, tool in tools.items():
            schema = tool.parameters or {}
            properties = set(schema.get("properties", {}).keys())
            required = set(schema.get("required", []))

            # properties と required の両方をチェック
            exposed = (properties | required) & self.INTERNAL_PARAMS
            if exposed:
                violations.append(f"{name}: {exposed}")

        assert not violations, f"Internal params exposed in tools: {violations}"


class TestRequireSessionTools:
    """@require_session を使用するツールのスキーマ検証。

    これらのツールは session パラメータを内部で使用するが、
    MCPスキーマには公開すべきでない。デコレータによって
    session パラメータがスキーマから除外されていることを検証する。
    """

    REQUIRE_SESSION_TOOLS = [
        "note_upload_eyecatch",
        "note_upload_body_image",
        "note_show_preview",
        "note_get_preview_html",
    ]

    @pytest.mark.parametrize("tool_name", REQUIRE_SESSION_TOOLS)
    def test_session_not_in_schema(self, tool_name: str) -> None:
        """session パラメータがスキーマに含まれていない。"""
        tools = get_tools()

        assert tool_name in tools, f"Tool {tool_name} not found"

        schema = tools[tool_name].parameters or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        assert "session" not in properties, f"{tool_name}: 'session' found in properties"
        assert "session" not in required, f"{tool_name}: 'session' found in required"
