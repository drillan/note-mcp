"""Authentication module for note-mcp.

Provides session management and browser-based login functionality.
"""

from note_mcp.auth.session import KeyringError, SessionManager

__all__ = ["SessionManager", "KeyringError"]
