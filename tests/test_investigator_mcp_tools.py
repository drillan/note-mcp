"""Tests for investigator MCP tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

from note_mcp.investigator.mcp_tools import register_investigator_tools


class TestRegisterInvestigatorTools:
    """Tests for register_investigator_tools function."""

    def test_registers_tools_with_mcp(self) -> None:
        """Test that tools are registered with the MCP instance."""
        mock_mcp = MagicMock()

        # Create a list to track registered tools
        registered_tools: list[str] = []

        def tool_decorator() -> Callable[[Any], Any]:
            """Mock decorator that tracks function names."""

            def wrapper(func: Any) -> Any:
                registered_tools.append(func.__name__)
                return func

            return wrapper

        mock_mcp.tool = tool_decorator

        register_investigator_tools(mock_mcp)

        # Verify expected tools are registered
        expected_tools = [
            "investigator_start_capture",
            "investigator_stop_capture",
            "investigator_get_status",
            "investigator_navigate",
            "investigator_click",
            "investigator_type",
            "investigator_screenshot",
            "investigator_get_page_content",
            "investigator_get_traffic",
            "investigator_analyze",
            "investigator_export",
        ]

        for tool_name in expected_tools:
            assert tool_name in registered_tools, f"Tool {tool_name} not registered"

    def test_import_works(self) -> None:
        """Test that the module can be imported."""
        from note_mcp.investigator import register_investigator_tools

        assert callable(register_investigator_tools)
