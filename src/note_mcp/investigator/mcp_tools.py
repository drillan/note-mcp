"""Investigator MCP tools for AI-driven API investigation.

Provides MCP tools for browser automation and HTTP traffic analysis.
These tools enable AI agents to investigate note.com's API behavior
through direct browser interaction and traffic capture.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from fastmcp import FastMCP

from note_mcp.investigator.core import CaptureSessionManager


def register_investigator_tools(mcp: FastMCP) -> None:
    """Register investigator MCP tools with the server.

    Args:
        mcp: FastMCP server instance to register tools with
    """

    @mcp.tool()
    async def investigator_start_capture(
        domain: Annotated[str, "キャプチャ対象ドメイン（例: api.note.com）"],
        port: Annotated[int, "プロキシポート"] = 8080,
    ) -> str:
        """キャプチャセッションを開始します。

        ブラウザとプロキシを起動し、指定ドメインのHTTPトラフィックを
        キャプチャ可能な状態にします。
        """
        await CaptureSessionManager.get_or_create(domain, port)
        return f"Capture session started for domain: {domain}, port: {port}"

    @mcp.tool()
    async def investigator_stop_capture() -> str:
        """キャプチャセッションを停止します。

        ブラウザとプロキシを終了し、キャプチャデータを保存します。
        """
        await CaptureSessionManager.close()
        return "Capture session stopped"

    @mcp.tool()
    async def investigator_get_status() -> str:
        """現在のキャプチャセッション状態を取得します。

        セッションがアクティブか、キャプチャ中のドメイン等の情報を返します。
        """
        status = CaptureSessionManager.get_status()
        return json.dumps(status, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def investigator_navigate(
        url: Annotated[str, "移動先URL"],
    ) -> str:
        """指定URLに移動します。

        ブラウザを指定URLに移動させ、ページタイトルを返します。
        トラフィックは自動的にキャプチャされます。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return await session.navigate(url)

    @mcp.tool()
    async def investigator_click(
        selector: Annotated[str, "CSSセレクタ"],
    ) -> str:
        """セレクタで指定した要素をクリックします。

        CSSセレクタを使用してページ上の要素を特定し、クリックします。
        クリックにより発生するHTTPリクエストはキャプチャされます。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return await session.click(selector)

    @mcp.tool()
    async def investigator_type(
        selector: Annotated[str, "CSSセレクタ"],
        text: Annotated[str, "入力テキスト"],
    ) -> str:
        """指定要素にテキストを入力します。

        CSSセレクタで特定した入力要素にテキストを入力します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return await session.type_text(selector, text)

    @mcp.tool()
    async def investigator_screenshot() -> str:
        """現在のページのスクリーンショットを取得します。

        ページ全体のスクリーンショットをbase64エンコードされたPNG形式で返します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return await session.screenshot()

    @mcp.tool()
    async def investigator_get_page_content() -> str:
        """現在のページのHTMLを取得します。

        ページの完全なHTMLソースを返します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return await session.get_page_content()

    @mcp.tool()
    async def investigator_get_traffic(
        pattern: Annotated[str | None, "URLパターンでフィルタ（正規表現）"] = None,
    ) -> str:
        """キャプチャしたトラフィック一覧を取得します。

        これまでにキャプチャしたHTTPリクエストの一覧をJSON形式で返します。
        パターンを指定すると、URLが一致するリクエストのみ返します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        traffic = session.get_traffic(pattern)
        return json.dumps(traffic, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def investigator_analyze(
        pattern: Annotated[str, "URLパターン（正規表現）"],
        method: Annotated[str | None, "HTTPメソッドでフィルタ"] = None,
    ) -> str:
        """特定パターンのトラフィックを詳細分析します。

        指定したURLパターンに一致するリクエストを集計・分析し、
        レポート形式で返します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return session.analyze_traffic(pattern, method)

    @mcp.tool()
    async def investigator_export(
        output_path: Annotated[str, "出力ファイルパス"],
    ) -> str:
        """キャプチャデータをJSONファイルにエクスポートします。

        これまでにキャプチャした全トラフィックをJSONファイルに保存します。
        """
        session = CaptureSessionManager._instance
        if not session:
            return "Error: No active capture session. Start one first."
        return session.export_traffic(output_path)
