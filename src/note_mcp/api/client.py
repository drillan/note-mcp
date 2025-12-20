"""note.com API client using httpx.

Provides authenticated access to note.com API endpoints
with rate limiting and error handling.
"""

from __future__ import annotations

import time
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

import httpx

from note_mcp.models import ErrorCode, NoteAPIError, Session

if TYPE_CHECKING:
    pass


# API base URL
NOTE_API_BASE = "https://note.com/api"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 10  # Maximum requests per minute
RATE_LIMIT_WINDOW = 60  # Window size in seconds

# Default timeout for requests (seconds)
DEFAULT_TIMEOUT = 30


class NoteAPIClient:
    """HTTP client for note.com API.

    Provides authenticated requests with rate limiting and error handling.
    Use as async context manager for proper resource management.

    Attributes:
        session: User session with authentication cookies
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialize API client.

        Args:
            session: User session for authentication (optional for public endpoints)
        """
        self.session = session
        self._client: httpx.AsyncClient | None = None
        self._request_times: list[float] = []

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=NOTE_API_BASE,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_headers(self, include_xsrf: bool = False) -> dict[str, str]:
        """Build request headers with authentication.

        Args:
            include_xsrf: Whether to include X-XSRF-TOKEN header (for POST/PUT/DELETE)

        Returns:
            Headers dictionary with Accept and Cookie if session exists
        """
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "note-mcp/0.1.0",
        }

        if self.session is not None:
            cookie_parts = [f"{k}={v}" for k, v in self.session.cookies.items()]
            headers["Cookie"] = "; ".join(cookie_parts)

            # Add XSRF token for mutating requests
            if include_xsrf:
                xsrf_token = self.session.cookies.get("XSRF-TOKEN")
                if xsrf_token:
                    headers["X-XSRF-TOKEN"] = xsrf_token

        return headers

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting.

        Cleans up old timestamps and checks if we've exceeded the limit.
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Clean up old timestamps
        self._request_times = [t for t in self._request_times if t > window_start]

        # Note: We don't actively wait here, we just track
        # The actual rate limit error will come from the server
        # This is mainly for client-side tracking

    def _track_request(self) -> None:
        """Track a request for rate limiting."""
        self._request_times.append(time.time())

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API.

        Args:
            response: HTTP response object

        Raises:
            NoteAPIError: With appropriate error code
        """
        status = response.status_code

        if status == 401:
            raise NoteAPIError(
                code=ErrorCode.NOT_AUTHENTICATED,
                message="Authentication required. Please log in first.",
                details={"status_code": status},
            )
        elif status == 403:
            raise NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Access denied.",
                details={"status_code": status, "response": response.text},
            )
        elif status == 404:
            raise NoteAPIError(
                code=ErrorCode.ARTICLE_NOT_FOUND,
                message="Resource not found.",
                details={"status_code": status, "response": response.text},
            )
        elif status == 429:
            raise NoteAPIError(
                code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded. Please wait before making more requests.",
                details={"status_code": status},
            )
        elif status >= 500:
            raise NoteAPIError(
                code=ErrorCode.API_ERROR,
                message="Server error. Please try again later.",
                details={"status_code": status, "response": response.text},
            )
        else:
            raise NoteAPIError(
                code=ErrorCode.API_ERROR,
                message=f"API request failed with status {status}.",
                details={"status_code": status, "response": response.text},
            )

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GET request to the API.

        Args:
            path: API endpoint path (e.g., "/v1/articles")
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            NoteAPIError: If request fails
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        await self._check_rate_limit()
        self._track_request()

        headers = self._build_headers()
        response = await self._client.get(path, headers=headers, params=params)

        if not response.is_success:
            self._handle_error_response(response)

        result: dict[str, Any] = response.json()
        return result

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request to the API.

        Args:
            path: API endpoint path
            json: JSON body
            data: Form data
            files: Files to upload

        Returns:
            JSON response as dictionary

        Raises:
            NoteAPIError: If request fails
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        await self._check_rate_limit()
        self._track_request()

        headers = self._build_headers(include_xsrf=True)

        # Don't set Content-Type for multipart (httpx handles it)
        if json is not None:
            headers["Content-Type"] = "application/json"

        response = await self._client.post(
            path,
            headers=headers,
            json=json,
            data=data,
            files=files,
        )

        if not response.is_success:
            self._handle_error_response(response)

        result: dict[str, Any] = response.json()
        return result

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request to the API.

        Args:
            path: API endpoint path
            json: JSON body

        Returns:
            JSON response as dictionary

        Raises:
            NoteAPIError: If request fails
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        await self._check_rate_limit()
        self._track_request()

        headers = self._build_headers(include_xsrf=True)
        if json is not None:
            headers["Content-Type"] = "application/json"

        response = await self._client.put(path, headers=headers, json=json)

        if not response.is_success:
            self._handle_error_response(response)

        result: dict[str, Any] = response.json()
        return result

    async def delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request to the API.

        Args:
            path: API endpoint path

        Returns:
            JSON response as dictionary

        Raises:
            NoteAPIError: If request fails
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        await self._check_rate_limit()
        self._track_request()

        headers = self._build_headers(include_xsrf=True)
        response = await self._client.delete(path, headers=headers)

        if not response.is_success:
            self._handle_error_response(response)

        result: dict[str, Any] = response.json()
        return result
