"""Unit tests for article operations."""

from note_mcp.api.articles import _build_article_payload
from note_mcp.models import ArticleInput


class TestBuildArticlePayload:
    """Tests for _build_article_payload function."""

    def test_body_length_matches_html_not_markdown(self) -> None:
        """body_length should match HTML body length, not Markdown body length.

        This is critical because note.com API validates body_length against
        the actual body content. Using Markdown length when body is HTML
        causes 400 errors.
        """
        # Markdown body (short)
        markdown_body = "![image](https://example.com/img.png)"

        # HTML body (much longer after conversion)
        html_body = (
            '<figure name="abc123" id="abc123">'
            '<img src="https://example.com/img.png" alt="" width="620" height="457">'
            "<figcaption></figcaption></figure>"
        )

        article_input = ArticleInput(
            title="Test Article",
            body=markdown_body,
        )

        payload = _build_article_payload(article_input, html_body)

        # body_length must match HTML body length, not Markdown body length
        assert payload["body_length"] == len(html_body)
        assert payload["body_length"] != len(markdown_body)
        assert payload["body"] == html_body

    def test_body_length_with_no_body(self) -> None:
        """body_length should not be set when include_body=False."""
        article_input = ArticleInput(
            title="Test Article",
            body="Some content",
        )

        payload = _build_article_payload(article_input, include_body=False)

        assert "body" not in payload
        assert "body_length" not in payload

    def test_payload_includes_title(self) -> None:
        """Payload should always include the title."""
        article_input = ArticleInput(
            title="My Test Title",
            body="Content",
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert payload["name"] == "My Test Title"

    def test_payload_includes_tags_when_provided(self) -> None:
        """Payload should include hashtags when tags are provided."""
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
            tags=["python", "testing"],
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert "hashtags" in payload
        assert len(payload["hashtags"]) == 2
        assert payload["hashtags"][0] == {"hashtag": {"name": "python"}}
        assert payload["hashtags"][1] == {"hashtag": {"name": "testing"}}

    def test_tags_with_hash_prefix_are_normalized(self) -> None:
        """Tags with # prefix should have prefix removed."""
        article_input = ArticleInput(
            title="Test Article",
            body="Content",
            tags=["#python", "#testing"],
        )

        payload = _build_article_payload(article_input, "<p>Content</p>")

        assert payload["hashtags"][0] == {"hashtag": {"name": "python"}}
        assert payload["hashtags"][1] == {"hashtag": {"name": "testing"}}

    def test_body_not_included_when_html_body_is_none(self) -> None:
        """body and body_length should not be set when html_body is None.

        This handles the edge case where include_body=True (default) but
        html_body is not provided. The payload should omit body fields
        to avoid sending invalid data to the API.
        """
        article_input = ArticleInput(
            title="Test Article",
            body="Markdown content",
        )

        # html_body=None with include_body=True (default)
        payload = _build_article_payload(article_input, html_body=None)

        # body and body_length should NOT be in payload
        assert "body" not in payload
        assert "body_length" not in payload
        # But title should still be included
        assert payload["name"] == "Test Article"
