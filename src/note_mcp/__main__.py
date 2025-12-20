"""Entry point for note-mcp MCP server.

Run with: uv run python -m note_mcp
Or via fastmcp: uv run fastmcp run note_mcp.server:mcp
"""

from note_mcp.server import mcp


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
