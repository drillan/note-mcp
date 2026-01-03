"""Integration tests for auto-login functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from note_mcp.auth.browser import (
    _check_login_obstacles,
    _perform_auto_login,
    login_with_browser,
)
from note_mcp.models import LoginError


class TestCheckLoginObstacles:
    """Tests for _check_login_obstacles helper function."""

    @pytest.mark.asyncio
    async def test_raises_login_error_on_recaptcha(self) -> None:
        """reCAPTCHA検出時にLoginErrorを送出する。"""
        mock_page = AsyncMock()

        # reCAPTCHA要素が存在
        mock_recaptcha = AsyncMock()
        mock_recaptcha.count = AsyncMock(return_value=1)

        mock_two_factor = AsyncMock()
        mock_two_factor.count = AsyncMock(return_value=0)

        mock_error = AsyncMock()
        mock_error.count = AsyncMock(return_value=0)

        def locator_side_effect(selector: str) -> AsyncMock:
            if "recaptcha" in selector:
                return mock_recaptcha
            elif "two-factor" in selector or "otp" in selector:
                return mock_two_factor
            else:
                return mock_error

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        with pytest.raises(LoginError) as exc_info:
            await _check_login_obstacles(mock_page)

        assert exc_info.value.code == "RECAPTCHA_DETECTED"
        assert "reCAPTCHA" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_raises_login_error_on_two_factor(self) -> None:
        """2FA検出時にLoginErrorを送出する。"""
        mock_page = AsyncMock()

        # reCAPTCHAなし、2FAあり
        mock_recaptcha = AsyncMock()
        mock_recaptcha.count = AsyncMock(return_value=0)

        mock_two_factor = AsyncMock()
        mock_two_factor.count = AsyncMock(return_value=1)

        mock_error = AsyncMock()
        mock_error.count = AsyncMock(return_value=0)

        def locator_side_effect(selector: str) -> AsyncMock:
            if "recaptcha" in selector:
                return mock_recaptcha
            elif "two-factor" in selector or "otp" in selector:
                return mock_two_factor
            else:
                return mock_error

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        with pytest.raises(LoginError) as exc_info:
            await _check_login_obstacles(mock_page)

        assert exc_info.value.code == "TWO_FACTOR_REQUIRED"
        assert "二段階認証" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_raises_login_error_on_invalid_credentials(self) -> None:
        """認証エラーメッセージ検出時にLoginErrorを送出する。"""
        mock_page = AsyncMock()

        # reCAPTCHAなし、2FAなし、エラーメッセージあり
        mock_recaptcha = AsyncMock()
        mock_recaptcha.count = AsyncMock(return_value=0)

        mock_two_factor = AsyncMock()
        mock_two_factor.count = AsyncMock(return_value=0)

        mock_error = AsyncMock()
        mock_error.count = AsyncMock(return_value=1)
        mock_error.first = AsyncMock()
        mock_error.first.text_content = AsyncMock(return_value="パスワードが正しくありません")

        def locator_side_effect(selector: str) -> AsyncMock:
            if "recaptcha" in selector:
                return mock_recaptcha
            elif "two-factor" in selector or "otp" in selector:
                return mock_two_factor
            else:
                return mock_error

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        with pytest.raises(LoginError) as exc_info:
            await _check_login_obstacles(mock_page)

        assert exc_info.value.code == "INVALID_CREDENTIALS"
        assert "認証情報" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_no_error_when_no_obstacles(self) -> None:
        """障害がない場合は正常終了する。"""
        mock_page = AsyncMock()

        # すべて0（障害なし）
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)

        mock_page.locator = MagicMock(return_value=mock_locator)

        # 例外が発生しないことを確認
        await _check_login_obstacles(mock_page)


class TestPerformAutoLogin:
    """Tests for _perform_auto_login helper function."""

    @pytest.mark.asyncio
    async def test_fills_credentials_and_submits(self) -> None:
        """認証情報を入力してsubmitする。"""
        mock_page = AsyncMock()

        # ロケーター設定
        mock_email = AsyncMock()
        mock_email.wait_for = AsyncMock()
        mock_email.fill = AsyncMock()

        mock_password = AsyncMock()
        mock_password.fill = AsyncMock()

        mock_submit = AsyncMock()
        mock_submit.click = AsyncMock()

        def locator_side_effect(selector: str) -> AsyncMock:
            if "email" in selector:
                return mock_email
            elif "password" in selector:
                return mock_password
            elif "submit" in selector:
                return mock_submit
            else:
                # 障害チェック用（すべて0）
                mock_locator = AsyncMock()
                mock_locator.count = AsyncMock(return_value=0)
                return mock_locator

        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        mock_page.wait_for_load_state = AsyncMock()

        await _perform_auto_login(mock_page, "test@example.com", "password123")

        # 各フィールドが正しく操作されたか確認
        mock_email.wait_for.assert_called_once_with(state="visible", timeout=10000)
        mock_email.fill.assert_called_once_with("test@example.com")
        mock_password.fill.assert_called_once_with("password123")
        mock_submit.click.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=15000)


class TestLoginWithBrowserAutoLogin:
    """Tests for login_with_browser with credentials parameter."""

    @pytest.mark.asyncio
    async def test_auto_login_success(self) -> None:
        """credentials指定時に自動ログインを実行する。"""
        with patch("note_mcp.auth.browser.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()

            # URLは最初ログインページ、自動ログイン後にホームにリダイレクト
            url_state = {"url": "https://note.com/login"}

            def get_url() -> str:
                return url_state["url"]

            # url propertyをモック
            type(mock_page).url = property(lambda self: get_url())

            # wait_for_load_stateでURLを変更（ログイン成功をシミュレート）
            async def mock_wait_for_load_state(*args: object, **kwargs: object) -> None:
                url_state["url"] = "https://note.com/"

            mock_page.wait_for_load_state = AsyncMock(side_effect=mock_wait_for_load_state)

            # ロケーター設定
            mock_email = AsyncMock()
            mock_email.wait_for = AsyncMock()
            mock_email.fill = AsyncMock()

            mock_password = AsyncMock()
            mock_password.fill = AsyncMock()

            mock_submit = AsyncMock()
            mock_submit.click = AsyncMock()

            def locator_side_effect(selector: str) -> AsyncMock:
                if "email" in selector:
                    return mock_email
                elif "password" in selector:
                    return mock_password
                elif "submit" in selector:
                    return mock_submit
                else:
                    mock_locator = AsyncMock()
                    mock_locator.count = AsyncMock(return_value=0)
                    return mock_locator

            mock_page.locator = MagicMock(side_effect=locator_side_effect)
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.wait_for_url = AsyncMock()

            mock_page.context = AsyncMock()
            mock_page.context.add_cookies = AsyncMock()
            mock_page.context.cookies = AsyncMock(
                return_value=[
                    {"name": "note_gql_auth_token", "value": "token123"},
                    {"name": "_note_session_v5", "value": "session456"},
                ]
            )
            mock_page.evaluate = AsyncMock(return_value=None)

            mock_manager.close = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            with patch("note_mcp.auth.browser.SessionManager") as mock_session_manager_class:
                mock_session_manager = MagicMock()
                mock_session_manager.load.return_value = None  # 保存済みセッションなし
                mock_session_manager_class.return_value = mock_session_manager

                with patch("note_mcp.auth.browser.get_current_user") as mock_get_user:
                    mock_get_user.return_value = {"id": "user123", "urlname": "testuser"}

                    session = await login_with_browser(
                        timeout=60,
                        credentials=("test@example.com", "password123"),
                    )

                    assert session is not None
                    assert session.user_id == "user123"
                    assert session.username == "testuser"

                    # 自動ログインが実行されたことを確認
                    mock_email.fill.assert_called_once_with("test@example.com")
                    mock_password.fill.assert_called_once_with("password123")

    @pytest.mark.asyncio
    async def test_auto_login_raises_on_recaptcha(self) -> None:
        """自動ログイン中にreCAPTCHA検出でLoginErrorを送出する。"""
        with patch("note_mcp.auth.browser.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.url = "https://note.com/login"

            # reCAPTCHA検出
            mock_recaptcha = AsyncMock()
            mock_recaptcha.count = AsyncMock(return_value=1)

            mock_email = AsyncMock()
            mock_email.wait_for = AsyncMock()
            mock_email.fill = AsyncMock()

            mock_password = AsyncMock()
            mock_password.fill = AsyncMock()

            mock_submit = AsyncMock()
            mock_submit.click = AsyncMock()

            def locator_side_effect(selector: str) -> AsyncMock:
                if "recaptcha" in selector:
                    return mock_recaptcha
                elif "email" in selector:
                    return mock_email
                elif "password" in selector:
                    return mock_password
                elif "submit" in selector:
                    return mock_submit
                else:
                    mock_locator = AsyncMock()
                    mock_locator.count = AsyncMock(return_value=0)
                    return mock_locator

            mock_page.locator = MagicMock(side_effect=locator_side_effect)
            mock_page.wait_for_load_state = AsyncMock()

            mock_page.context = AsyncMock()
            mock_page.context.add_cookies = AsyncMock()

            mock_manager.close = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            with patch("note_mcp.auth.browser.SessionManager") as mock_session_manager_class:
                mock_session_manager = MagicMock()
                mock_session_manager.load.return_value = None
                mock_session_manager_class.return_value = mock_session_manager

                with pytest.raises(LoginError) as exc_info:
                    await login_with_browser(
                        timeout=60,
                        credentials=("test@example.com", "password123"),
                    )

                assert exc_info.value.code == "RECAPTCHA_DETECTED"

    @pytest.mark.asyncio
    async def test_manual_login_when_no_credentials(self) -> None:
        """credentials未指定時は手動ログインを待機する。"""
        with patch("note_mcp.auth.browser.BrowserManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.get_instance.return_value = mock_manager

            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.url = "https://note.com/login"
            mock_page.wait_for_url = AsyncMock()

            mock_page.context = AsyncMock()
            mock_page.context.add_cookies = AsyncMock()
            mock_page.context.cookies = AsyncMock(
                return_value=[
                    {"name": "note_gql_auth_token", "value": "token123"},
                    {"name": "_note_session_v5", "value": "session456"},
                ]
            )
            mock_page.evaluate = AsyncMock(return_value=None)

            mock_manager.close = AsyncMock()
            mock_manager.get_page = AsyncMock(return_value=mock_page)

            with patch("note_mcp.auth.browser.SessionManager") as mock_session_manager_class:
                mock_session_manager = MagicMock()
                mock_session_manager.load.return_value = None
                mock_session_manager_class.return_value = mock_session_manager

                with patch("note_mcp.auth.browser.get_current_user") as mock_get_user:
                    mock_get_user.return_value = {"id": "user123", "urlname": "testuser"}

                    # credentials=None（デフォルト）で呼び出し
                    session = await login_with_browser(timeout=60)

                    assert session is not None
                    # wait_for_urlが呼ばれた（手動ログイン待機）
                    mock_page.wait_for_url.assert_called()
