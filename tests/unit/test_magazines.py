"""Unit tests for magazine and membership listing helpers."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.models import ErrorCode, NoteAPIError, Session


def create_mock_session(username: str = "testuser") -> Session:
    """Create a mock session for magazine API tests."""
    return Session(
        cookies={"note_gql_auth_token": "token123", "_note_session_v5": "session456"},
        user_id="user123",
        username=username,
        expires_at=int(time.time()) + 3600,
        created_at=int(time.time()),
    )


class TestListMyMagazines:
    """Tests for list_my_magazines()."""

    @pytest.mark.asyncio
    async def test_uses_creator_contents_endpoint_with_session_username(self) -> None:
        """Magazine listing should use the creator contents endpoint."""
        from note_mcp.api.magazines import list_my_magazines

        session = create_mock_session(username="writer")
        response: dict[str, Any] = {
            "data": {
                "contents": [
                    {"key": "m123", "name": "Magazine"},
                    "invalid",
                    {"key": "md456", "name": "Subscription Magazine"},
                ]
            }
        }

        with patch("note_mcp.api.magazines.NoteAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=response)
            mock_client_class.return_value = mock_client

            magazines = await list_my_magazines(session)

        mock_client.get.assert_awaited_once_with(
            "/v2/creators/writer/contents",
            params={"kind": "magazine"},
        )
        assert magazines == [
            {"key": "m123", "name": "Magazine"},
            {"key": "md456", "name": "Subscription Magazine"},
        ]

    @pytest.mark.asyncio
    async def test_requires_username(self) -> None:
        """Missing username should fail explicitly instead of guessing."""
        from note_mcp.api.magazines import list_my_magazines

        session = create_mock_session(username="")

        with pytest.raises(NoteAPIError) as exc_info:
            await list_my_magazines(session)

        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert "username is required" in exc_info.value.message


class TestListCirclePlans:
    """Tests for list_circle_plans()."""

    @pytest.mark.asyncio
    async def test_supports_list_response_shape(self) -> None:
        """Membership plan endpoint may return a list in data."""
        from note_mcp.api.magazines import list_circle_plans

        session = create_mock_session()
        response: dict[str, Any] = {
            "data": [
                {"key": "plan1", "name": "Basic"},
                "invalid",
                {"key": "plan2", "name": "Premium"},
            ]
        }

        with patch("note_mcp.api.magazines.NoteAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=response)
            mock_client_class.return_value = mock_client

            plans = await list_circle_plans(session)

        mock_client.get.assert_awaited_once_with("/v3/memberships/magazines/connectable_plans")
        assert plans == [
            {"key": "plan1", "name": "Basic"},
            {"key": "plan2", "name": "Premium"},
        ]

    @pytest.mark.asyncio
    async def test_supports_dict_response_shape(self) -> None:
        """Membership plan endpoint may return data.plans."""
        from note_mcp.api.magazines import list_circle_plans

        session = create_mock_session()
        response: dict[str, Any] = {
            "data": {
                "plans": [
                    {"key": "plan1", "name": "Basic"},
                ]
            }
        }

        with patch("note_mcp.api.magazines.NoteAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=response)
            mock_client_class.return_value = mock_client

            plans = await list_circle_plans(session)

        assert plans == [{"key": "plan1", "name": "Basic"}]
