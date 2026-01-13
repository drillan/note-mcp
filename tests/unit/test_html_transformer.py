"""Unit tests for html_transformer Higher-Order Function."""

import re

from note_mcp.utils.markdown_to_html import html_transformer


class TestHtmlTransformer:
    """Tests for html_transformer function."""

    def test_basic_replacement(self) -> None:
        """html_transformerで基本的なパターン置換ができる."""
        pattern = re.compile(r"\[(\w+)\]")

        def transformer(m: re.Match[str]) -> str:
            return f"<{m.group(1)}>"

        transform = html_transformer(pattern, transformer)

        result = transform("Hello [world]!")
        assert result == "Hello <world>!"

    def test_multiple_matches(self) -> None:
        """複数のマッチを正しく変換できる."""
        pattern = re.compile(r"\*(\w+)\*")

        def transformer(m: re.Match[str]) -> str:
            return f"<strong>{m.group(1)}</strong>"

        transform = html_transformer(pattern, transformer)

        result = transform("*bold* and *text*")
        assert result == "<strong>bold</strong> and <strong>text</strong>"

    def test_with_group_extraction(self) -> None:
        """正規表現グループを使った変換ができる."""
        pattern = re.compile(r"<p>(\w+)</p>")

        def transformer(m: re.Match[str]) -> str:
            return f'<p class="styled">{m.group(1)}</p>'

        transform = html_transformer(pattern, transformer)

        result = transform("<p>content</p>")
        assert result == '<p class="styled">content</p>'

    def test_preserves_unmatched(self) -> None:
        """マッチしない部分は変更されない."""
        pattern = re.compile(r"\[SPECIAL\]")

        def transformer(m: re.Match[str]) -> str:
            return "<special>"

        transform = html_transformer(pattern, transformer)

        result = transform("Normal text stays normal")
        assert result == "Normal text stays normal"

    def test_no_match_returns_original(self) -> None:
        """マッチがない場合は元の文字列がそのまま返される."""
        pattern = re.compile(r"NOT_FOUND")

        def transformer(m: re.Match[str]) -> str:
            return "REPLACED"

        transform = html_transformer(pattern, transformer)

        original = "This string has no match"
        result = transform(original)
        assert result == original

    def test_empty_string(self) -> None:
        """空文字列を正しく処理できる."""
        pattern = re.compile(r"\[(\w+)\]")

        def transformer(m: re.Match[str]) -> str:
            return f"<{m.group(1)}>"

        transform = html_transformer(pattern, transformer)

        result = transform("")
        assert result == ""

    def test_complex_pattern_with_multiple_groups(self) -> None:
        """複数のグループを持つ複雑なパターンを処理できる."""
        pattern = re.compile(r"<p([^>]*)>(.*?)</p>", re.DOTALL)

        def transformer(match: re.Match[str]) -> str:
            attrs = match.group(1)
            content = match.group(2)
            return f'<p style="modified"{attrs}>{content}</p>'

        transform = html_transformer(pattern, transformer)

        result = transform('<p class="test">Hello</p>')
        assert result == '<p style="modified" class="test">Hello</p>'

    def test_case_insensitive_pattern(self) -> None:
        """大文字小文字を区別しないパターンで動作する."""
        pattern = re.compile(r"<DIV>(.*?)</DIV>", re.IGNORECASE)

        def transformer(m: re.Match[str]) -> str:
            return f"<section>{m.group(1)}</section>"

        transform = html_transformer(pattern, transformer)

        result = transform("<div>Content</div>")
        assert result == "<section>Content</section>"

    def test_dotall_pattern_for_multiline(self) -> None:
        """DOTALLフラグで改行を含むコンテンツを処理できる."""
        pattern = re.compile(r"<blockquote>(.*?)</blockquote>", re.DOTALL)

        def transformer(m: re.Match[str]) -> str:
            return f"<q>{m.group(1).replace(chr(10), '<br>')}</q>"

        transform = html_transformer(pattern, transformer)

        result = transform("<blockquote>Line1\nLine2</blockquote>")
        assert result == "<q>Line1<br>Line2</q>"

    def test_returns_callable(self) -> None:
        """html_transformerは呼び出し可能なオブジェクトを返す."""
        pattern = re.compile(r"test")

        def transformer(m: re.Match[str]) -> str:
            return "TEST"

        transform = html_transformer(pattern, transformer)

        assert callable(transform)

    def test_transformer_receives_match_object(self) -> None:
        """transformerはre.Matchオブジェクトを受け取る."""
        received_groups: list[tuple[str, ...]] = []
        pattern = re.compile(r"(\w+):(\w+)")

        def transformer(match: re.Match[str]) -> str:
            received_groups.append(match.groups())
            return f"{match.group(2)}={match.group(1)}"

        transform = html_transformer(pattern, transformer)
        result = transform("key:value")

        assert result == "value=key"
        assert received_groups == [("key", "value")]
