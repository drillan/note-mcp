"""Magazine and membership operations for note.com API."""

from __future__ import annotations

from typing import Any

from note_mcp.api.client import NoteAPIClient
from note_mcp.models import ErrorCode, NoteAPIError, Session


async def list_my_magazines(
    session: Session,
    username: str | None = None,
) -> list[dict[str, Any]]:
    """List magazines owned by the authenticated user.

    Args:
        session: Authenticated session.
        username: note.com username. Defaults to the username stored in
            the session.

    Returns:
        Magazine payloads returned by note.com.

    Raises:
        NoteAPIError: If no username is available.
    """
    target_username = username or session.username
    if not target_username:
        raise NoteAPIError(
            code=ErrorCode.INVALID_INPUT,
            message=("username is required to list magazines. Pass it explicitly or call note_set_username first."),
        )

    async with NoteAPIClient(session) as client:
        response = await client.get(
            f"/v2/creators/{target_username}/contents",
            params={"kind": "magazine"},
        )

    data = response.get("data", {})
    contents = data.get("contents", []) if isinstance(data, dict) else []
    return [content for content in contents if isinstance(content, dict)]


async def list_circle_plans(session: Session) -> list[dict[str, Any]]:
    """List connectable membership plans for article publishing.

    Args:
        session: Authenticated session.

    Returns:
        Membership plan payloads returned by note.com.
    """
    async with NoteAPIClient(session) as client:
        response = await client.get("/v3/memberships/magazines/connectable_plans")

    data = response.get("data", [])
    if isinstance(data, dict):
        data = data.get("plans", [])

    return [plan for plan in data if isinstance(plan, dict)]
