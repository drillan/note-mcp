"""Static HTML validation using BeautifulSoup.

Provides HTML validation without Playwright for faster E2E test execution.
Use this for static element validation; use PreviewValidator for dynamic
elements like TOC and KaTeX that require JavaScript execution.
"""

from __future__ import annotations

import re
from typing import Literal

from bs4 import BeautifulSoup, Tag

from tests.e2e.helpers.validation import ValidationResult

# Type aliases for constrained values
HeadingLevel = Literal[2, 3]
TextAlignment = Literal["center", "right", "left"]


class HtmlValidator:
    """Static HTML validator using BeautifulSoup.

    Validates HTML elements without requiring Playwright/browser automation.
    All methods maintain the same signature as PreviewValidator for
    interface compatibility.

    Attributes:
        _soup: BeautifulSoup instance for HTML parsing
    """

    def __init__(self, html: str) -> None:
        """Initialize validator with HTML content.

        Args:
            html: HTML content to validate

        Raises:
            ValueError: If HTML content is empty or whitespace-only
        """
        if not html or not html.strip():
            raise ValueError("HTML content cannot be empty")
        self._soup = BeautifulSoup(html, "html.parser")

    def _find_elements_with_text(
        self,
        tag_name: str,
        text: str,
        *,
        attrs: dict[str, str] | None = None,
    ) -> list[Tag]:
        """Find elements containing specific text.

        Args:
            tag_name: HTML tag name to search
            text: Text to find (partial match)
            attrs: Optional attributes to filter by

        Returns:
            List of matching Tag elements
        """
        elements = self._soup.find_all(tag_name, attrs=attrs or {})
        return [el for el in elements if isinstance(el, Tag) and text in el.get_text()]

    async def validate_heading(self, level: HeadingLevel, text: str) -> ValidationResult:
        """Validate heading element.

        Args:
            level: Heading level (2 or 3)
            text: Expected heading text

        Returns:
            ValidationResult with success=True if <h{level}> contains text
        """
        tag_name = f"h{level}"
        elements = self._find_elements_with_text(tag_name, text)

        if elements:
            actual_text = elements[0].get_text().strip()
            return ValidationResult(
                success=True,
                expected=f"<h{level}> containing '{text}'",
                actual=actual_text,
                message=f"Found: {actual_text}",
            )
        return ValidationResult(
            success=False,
            expected=f"<h{level}> containing '{text}'",
            actual=None,
            message=f"No element found matching: <h{level}> containing '{text}'",
        )

    async def validate_bold(self, text: str) -> ValidationResult:
        """Validate bold text element.

        Args:
            text: Expected bold text

        Returns:
            ValidationResult with success=True if <strong> or <b> contains text
        """
        # Try <strong> first
        strong_elements = self._find_elements_with_text("strong", text)
        if strong_elements:
            actual_text = strong_elements[0].get_text().strip()
            return ValidationResult(
                success=True,
                expected=f"<strong> containing '{text}'",
                actual=actual_text,
                message=f"Found: {actual_text}",
            )

        # Fallback to <b>
        b_elements = self._find_elements_with_text("b", text)
        if b_elements:
            actual_text = b_elements[0].get_text().strip()
            return ValidationResult(
                success=True,
                expected=f"<b> containing '{text}'",
                actual=actual_text,
                message=f"[FALLBACK] Found <b> instead of <strong>: {actual_text}",
            )

        return ValidationResult(
            success=False,
            expected=f"<strong> or <b> containing '{text}'",
            actual=None,
            message=f"No element found matching: <strong> or <b> containing '{text}'",
        )

    async def validate_strikethrough(self, text: str) -> ValidationResult:
        """Validate strikethrough element.

        Args:
            text: Expected strikethrough text

        Returns:
            ValidationResult with success=True if <s> contains text
        """
        elements = self._find_elements_with_text("s", text)

        if elements:
            actual_text = elements[0].get_text().strip()
            return ValidationResult(
                success=True,
                expected=f"<s> containing '{text}'",
                actual=actual_text,
                message=f"Found: {actual_text}",
            )
        return ValidationResult(
            success=False,
            expected=f"<s> containing '{text}'",
            actual=None,
            message=f"No element found matching: <s> containing '{text}'",
        )

    async def validate_code_block(self, code: str) -> ValidationResult:
        """Validate code block element.

        Args:
            code: Expected code content

        Returns:
            ValidationResult with success=True if <pre><code> contains code
        """
        # Find <pre> elements containing <code>
        pre_elements = self._soup.find_all("pre")
        for pre in pre_elements:
            if not isinstance(pre, Tag):
                continue
            code_el = pre.find("code")
            if code_el and isinstance(code_el, Tag):
                code_text = code_el.get_text()
                if code in code_text:
                    display_text = code_text[:50] + "..." if len(code_text) > 50 else code_text
                    return ValidationResult(
                        success=True,
                        expected=f"<pre><code> containing '{code}'",
                        actual=code_text,
                        message=f"Found: {display_text}",
                    )

        return ValidationResult(
            success=False,
            expected=f"<pre><code> containing '{code}'",
            actual=None,
            message=f"No element found matching: <pre><code> containing '{code}'",
        )

    async def validate_alignment(self, text: str, alignment: TextAlignment) -> ValidationResult:
        """Validate text alignment.

        Args:
            text: Expected text content
            alignment: Expected alignment (center, right, left)

        Returns:
            ValidationResult with success=True if element has correct text-align
        """
        # Find elements with style containing text-align
        pattern = re.compile(rf"text-align:\s*{alignment}", re.IGNORECASE)
        elements = self._soup.find_all(style=pattern)

        for el in elements:
            if isinstance(el, Tag) and text in el.get_text():
                return ValidationResult(
                    success=True,
                    expected=f"Element with text-align: {alignment} containing '{text}'",
                    actual=el.get_text().strip(),
                    message=f"Found element with text-align: {alignment}",
                )

        return ValidationResult(
            success=False,
            expected=f"Element with text-align: {alignment} containing '{text}'",
            actual=None,
            message=f"No element found with text-align: {alignment} containing '{text}'",
        )

    async def validate_blockquote(self, text: str) -> ValidationResult:
        """Validate blockquote element.

        Args:
            text: Expected quote text

        Returns:
            ValidationResult with success=True if <blockquote> contains text
        """
        elements = self._find_elements_with_text("blockquote", text)

        if elements:
            actual_text = elements[0].get_text().strip()
            return ValidationResult(
                success=True,
                expected=f"<blockquote> containing '{text}'",
                actual=actual_text,
                message=f"Found: {actual_text}",
            )
        return ValidationResult(
            success=False,
            expected=f"<blockquote> containing '{text}'",
            actual=None,
            message=f"No element found matching: <blockquote> containing '{text}'",
        )

    async def validate_link(self, text: str, url: str) -> ValidationResult:
        """Validate link element.

        Args:
            text: Expected link text
            url: Expected href value

        Returns:
            ValidationResult with success=True if <a href="{url}">{text}</a> exists
        """
        elements = self._soup.find_all("a", href=url)

        for el in elements:
            if isinstance(el, Tag) and text in el.get_text():
                return ValidationResult(
                    success=True,
                    expected=f"<a href='{url}'> containing '{text}'",
                    actual=el.get_text().strip(),
                    message=f"Found: {el.get_text().strip()}",
                )

        return ValidationResult(
            success=False,
            expected=f"<a href='{url}'> containing '{text}'",
            actual=None,
            message=f"No element found matching: <a href='{url}'> containing '{text}'",
        )

    async def validate_horizontal_line(self) -> ValidationResult:
        """Validate horizontal line element.

        Returns:
            ValidationResult with success=True if <hr> element exists
        """
        hr_elements = self._soup.find_all("hr")
        count = len(hr_elements)

        if count > 0:
            return ValidationResult(
                success=True,
                expected="<hr> element",
                actual="<hr>",
                message=f"Found {count} <hr> element(s)",
            )
        return ValidationResult(
            success=False,
            expected="<hr> element",
            actual=None,
            message="No <hr> element found",
        )

    async def _validate_list(
        self,
        items: list[str],
        list_tag: str,
    ) -> ValidationResult:
        """Validate list elements.

        Args:
            items: Expected list items
            list_tag: List tag name (ul or ol)

        Returns:
            ValidationResult with success=True if list contains all items
        """
        if not items:
            return ValidationResult(
                success=False,
                expected=f"<{list_tag}> with items",
                actual=None,
                message="No items provided for validation",
            )

        list_elements = self._soup.find_all(list_tag)
        if not list_elements:
            return ValidationResult(
                success=False,
                expected=f"<{list_tag}> with {len(items)} item(s)",
                actual=None,
                message=f"No <{list_tag}> element found",
            )

        # Check each item
        missing_items: list[str] = []
        for item in items:
            found = False
            for list_el in list_elements:
                if not isinstance(list_el, Tag):
                    continue
                li_elements = list_el.find_all("li", recursive=False)
                for li in li_elements:
                    if isinstance(li, Tag) and item in li.get_text():
                        found = True
                        break
                if found:
                    break
            if not found:
                missing_items.append(item)

        if missing_items:
            return ValidationResult(
                success=False,
                expected=f"<{list_tag}> with items: {items}",
                actual=f"Missing: {missing_items}",
                message=f"Missing {len(missing_items)} item(s) in <{list_tag}>: {missing_items}",
            )

        return ValidationResult(
            success=True,
            expected=f"<{list_tag}> with {len(items)} item(s)",
            actual=f"Found all {len(items)} item(s)",
            message=f"Found all items in <{list_tag}>: {items}",
        )

    async def validate_unordered_list(self, items: list[str]) -> ValidationResult:
        """Validate unordered list element.

        Args:
            items: Expected list items

        Returns:
            ValidationResult with success=True if <ul><li> contains all items
        """
        return await self._validate_list(items, "ul")

    async def validate_ordered_list(self, items: list[str]) -> ValidationResult:
        """Validate ordered list element.

        Args:
            items: Expected list items

        Returns:
            ValidationResult with success=True if <ol><li> contains all items
        """
        return await self._validate_list(items, "ol")
