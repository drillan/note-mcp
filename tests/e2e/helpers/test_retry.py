"""Tests for retry helper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from playwright.async_api import Error as PlaywrightError

from tests.e2e.helpers.retry import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_MAX_ATTEMPTS,
    RETRYABLE_EXCEPTIONS,
    is_retryable,
    with_retry,
)


class TestIsRetryable:
    """Tests for is_retryable function."""

    def test_timeout_error_is_retryable(self) -> None:
        """TimeoutError should be retryable."""
        assert is_retryable(TimeoutError("timeout"))

    def test_asyncio_timeout_error_is_retryable(self) -> None:
        """asyncio.TimeoutError should be retryable."""
        assert is_retryable(TimeoutError())

    def test_httpx_timeout_exception_is_retryable(self) -> None:
        """httpx.TimeoutException should be retryable."""
        assert is_retryable(httpx.TimeoutException("timeout"))

    def test_httpx_network_error_is_retryable(self) -> None:
        """httpx.NetworkError should be retryable."""
        assert is_retryable(httpx.NetworkError("network error"))

    def test_playwright_timeout_error_is_retryable(self) -> None:
        """PlaywrightError with timeout message should be retryable."""
        assert is_retryable(PlaywrightError("Timeout 30000ms exceeded"))

    def test_playwright_timed_out_is_retryable(self) -> None:
        """PlaywrightError with 'timed out' message should be retryable."""
        assert is_retryable(PlaywrightError("Element timed out"))

    def test_playwright_non_timeout_not_retryable(self) -> None:
        """PlaywrightError without timeout message should not be retryable."""
        assert not is_retryable(PlaywrightError("Element not found"))

    def test_value_error_not_retryable(self) -> None:
        """ValueError should not be retryable."""
        assert not is_retryable(ValueError("invalid"))

    def test_runtime_error_not_retryable(self) -> None:
        """RuntimeError should not be retryable."""
        assert not is_retryable(RuntimeError("error"))


class TestWithRetry:
    """Tests for with_retry function."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self) -> None:
        """Should return result without retry on success."""
        mock_func = AsyncMock(return_value="success")

        result = await with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self) -> None:
        """Should retry on TimeoutError and succeed."""
        mock_func = AsyncMock(side_effect=[TimeoutError(), "success"])

        with patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_httpx_timeout(self) -> None:
        """Should retry on httpx.TimeoutException and succeed."""
        mock_func = AsyncMock(side_effect=[httpx.TimeoutException("timeout"), "success"])

        with patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_playwright_timeout(self) -> None:
        """Should retry on PlaywrightError with timeout message."""
        mock_func = AsyncMock(side_effect=[PlaywrightError("Timeout 30000ms exceeded"), "success"])

        with patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_exception_raises_immediately(self) -> None:
        """Should raise immediately for non-retryable exceptions."""
        mock_func = AsyncMock(side_effect=ValueError("invalid"))

        with pytest.raises(ValueError, match="invalid"):
            await with_retry(mock_func)

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self) -> None:
        """Should raise after max attempts exceeded."""
        mock_func = AsyncMock(side_effect=TimeoutError("timeout"))

        with (
            patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError, match="timeout"),
        ):
            await with_retry(mock_func, max_attempts=3)

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff(self) -> None:
        """Should use exponential backoff for delays."""
        mock_func = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), "success"])
        sleep_mock = AsyncMock()

        with patch("tests.e2e.helpers.retry.asyncio.sleep", sleep_mock):
            await with_retry(mock_func, backoff_base=1.0)

        # First retry: 1.0 * 2^0 = 1.0s
        # Second retry: 1.0 * 2^1 = 2.0s
        assert sleep_mock.call_count == 2
        sleep_mock.assert_any_call(1.0)
        sleep_mock.assert_any_call(2.0)

    @pytest.mark.asyncio
    async def test_custom_max_attempts(self) -> None:
        """Should respect custom max_attempts."""
        mock_func = AsyncMock(side_effect=TimeoutError("timeout"))

        with (
            patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError),
        ):
            await with_retry(mock_func, max_attempts=5)

        assert mock_func.call_count == 5

    @pytest.mark.asyncio
    async def test_custom_backoff_base(self) -> None:
        """Should respect custom backoff_base."""
        mock_func = AsyncMock(side_effect=[TimeoutError(), "success"])
        sleep_mock = AsyncMock()

        with patch("tests.e2e.helpers.retry.asyncio.sleep", sleep_mock):
            await with_retry(mock_func, backoff_base=2.0)

        sleep_mock.assert_called_once_with(2.0)

    @pytest.mark.asyncio
    async def test_logging_on_retry(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log warning on retry."""
        mock_func = AsyncMock(side_effect=[TimeoutError(), "success"])

        with patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock):
            await with_retry(mock_func)

        assert "Attempt 1 failed" in caplog.text
        assert "TimeoutError" in caplog.text
        assert "Retrying in 1.0s" in caplog.text

    @pytest.mark.asyncio
    async def test_logging_on_final_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log error on final failure."""
        mock_func = AsyncMock(side_effect=TimeoutError("timeout"))

        with (
            patch("tests.e2e.helpers.retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(TimeoutError),
        ):
            await with_retry(mock_func, max_attempts=2)

        assert "Attempt 2 failed" in caplog.text
        assert "No more retries" in caplog.text


class TestConstants:
    """Tests for module constants."""

    def test_default_max_attempts(self) -> None:
        """DEFAULT_MAX_ATTEMPTS should be 3."""
        assert DEFAULT_MAX_ATTEMPTS == 3

    def test_default_backoff_base(self) -> None:
        """DEFAULT_BACKOFF_BASE should be 1.0."""
        assert DEFAULT_BACKOFF_BASE == 1.0

    def test_retryable_exceptions_contains_expected(self) -> None:
        """RETRYABLE_EXCEPTIONS should contain expected types."""
        assert TimeoutError in RETRYABLE_EXCEPTIONS
        assert asyncio.TimeoutError in RETRYABLE_EXCEPTIONS
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS
        assert httpx.NetworkError in RETRYABLE_EXCEPTIONS
