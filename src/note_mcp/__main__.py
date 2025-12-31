"""Entry point for note-mcp MCP server.

Run with: uv run python -m note_mcp
Or via fastmcp: uv run fastmcp run note_mcp.server:mcp

Investigator mode:
    uv run python -m note_mcp --investigator
    Or set INVESTIGATOR_MODE=1 environment variable
"""

from __future__ import annotations

import argparse
import os


def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="note-mcp MCP server")
    parser.add_argument(
        "--investigator",
        action="store_true",
        help="Enable investigator mode for API investigation",
    )
    args = parser.parse_args()

    if args.investigator:
        os.environ["INVESTIGATOR_MODE"] = "1"

    # Import server after setting environment variable
    from note_mcp.server import mcp

    mcp.run()


if __name__ == "__main__":
    main()
