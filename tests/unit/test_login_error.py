"""LoginError例外のユニットテスト。"""

from note_mcp.models import LoginError


class TestLoginError:
    """LoginError例外クラスのテスト。"""

    def test_login_error_attributes(self) -> None:
        """LoginErrorの属性が正しく設定される。"""
        error = LoginError(
            code="RECAPTCHA_DETECTED",
            message="reCAPTCHAが検出されました",
            resolution="手動でログインしてください",
        )
        assert error.code == "RECAPTCHA_DETECTED"
        assert error.message == "reCAPTCHAが検出されました"
        assert error.resolution == "手動でログインしてください"
        assert str(error) == "reCAPTCHAが検出されました"

    def test_login_error_without_resolution(self) -> None:
        """resolutionなしでLoginErrorを作成できる。"""
        error = LoginError(code="UNKNOWN", message="不明なエラー")
        assert error.code == "UNKNOWN"
        assert error.message == "不明なエラー"
        assert error.resolution is None

    def test_login_error_is_exception(self) -> None:
        """LoginErrorはExceptionを継承している。"""
        error = LoginError(code="TEST", message="test")
        assert isinstance(error, Exception)
