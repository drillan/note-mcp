"""FastMCP server for note.com article management.

Provides MCP tools for creating, updating, and managing note.com articles.
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP

from note_mcp.api.articles import create_draft, update_article
from note_mcp.api.images import upload_image
from note_mcp.auth.browser import login_with_browser
from note_mcp.auth.session import SessionManager
from note_mcp.browser.preview import show_preview
from note_mcp.models import ArticleInput

# Create MCP server instance
mcp = FastMCP("note-mcp")


# Session manager instance
_session_manager = SessionManager()


@mcp.tool()
async def note_login(
    timeout: Annotated[int, "ログインのタイムアウト時間（秒）。デフォルトは300秒。"] = 300,
) -> str:
    """note.comにログインします。

    ブラウザウィンドウが開き、手動でログインを行います。
    ログイン完了後、セッション情報が安全に保存されます。

    Args:
        timeout: ログインのタイムアウト時間（秒）

    Returns:
        ログイン結果のメッセージ
    """
    session = await login_with_browser(timeout=timeout)
    return f"ログインに成功しました。ユーザー名: {session.username}"


@mcp.tool()
async def note_check_auth() -> str:
    """現在の認証状態を確認します。

    保存されているセッション情報を確認し、有効かどうかを返します。

    Returns:
        認証状態のメッセージ
    """
    if not _session_manager.has_session():
        return "未認証です。note_loginを使用してログインしてください。"

    session = _session_manager.load()
    if session is None:
        return "セッションの読み込みに失敗しました。note_loginで再ログインしてください。"

    if session.is_expired():
        return "セッションの有効期限が切れています。note_loginで再ログインしてください。"

    return f"認証済みです。ユーザー名: {session.username}"


@mcp.tool()
async def note_logout() -> str:
    """note.comからログアウトします。

    保存されているセッション情報を削除します。

    Returns:
        ログアウト結果のメッセージ
    """
    _session_manager.clear()
    return "ログアウトしました。"


@mcp.tool()
async def note_create_draft(
    title: Annotated[str, "記事のタイトル"],
    body: Annotated[str, "記事の本文（Markdown形式）"],
    tags: Annotated[list[str] | None, "記事のタグ（#なしでも可）"] = None,
) -> str:
    """note.comに下書き記事を作成します。

    Markdown形式の本文をHTMLに変換してnote.comに送信します。
    作成後、ブラウザでプレビューを表示します。

    Args:
        title: 記事のタイトル
        body: 記事の本文（Markdown形式）
        tags: 記事のタグ（オプション）

    Returns:
        作成結果のメッセージ（記事IDを含む）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    article_input = ArticleInput(
        title=title,
        body=body,
        tags=tags or [],
    )

    article = await create_draft(session, article_input)

    # Show preview in browser
    await show_preview(session, article.key)

    tag_info = f"、タグ: {', '.join(article.tags)}" if article.tags else ""
    return f"下書きを作成しました。ID: {article.id}、キー: {article.key}{tag_info}"


@mcp.tool()
async def note_update_article(
    article_id: Annotated[str, "更新する記事のID"],
    title: Annotated[str, "新しいタイトル"],
    body: Annotated[str, "新しい本文（Markdown形式）"],
    tags: Annotated[list[str] | None, "新しいタグ（#なしでも可）"] = None,
) -> str:
    """既存の記事を更新します。

    Markdown形式の本文をHTMLに変換してnote.comに送信します。

    Args:
        article_id: 更新する記事のID
        title: 新しいタイトル
        body: 新しい本文（Markdown形式）
        tags: 新しいタグ（オプション）

    Returns:
        更新結果のメッセージ
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    article_input = ArticleInput(
        title=title,
        body=body,
        tags=tags or [],
    )

    article = await update_article(session, article_id, article_input)

    tag_info = f"、タグ: {', '.join(article.tags)}" if article.tags else ""
    return f"記事を更新しました。ID: {article.id}{tag_info}"


@mcp.tool()
async def note_upload_image(
    file_path: Annotated[str, "アップロードする画像ファイルのパス"],
) -> str:
    """画像をnote.comにアップロードします。

    JPEG、PNG、GIF、WebP形式の画像をアップロードできます。
    最大ファイルサイズは10MBです。

    Args:
        file_path: アップロードする画像ファイルのパス

    Returns:
        アップロード結果（画像URLを含む）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    image = await upload_image(session, file_path)
    return f"画像をアップロードしました。URL: {image.url}"


@mcp.tool()
async def note_show_preview(
    article_key: Annotated[str, "プレビューする記事のキー（例: n1234567890ab）"],
) -> str:
    """記事のプレビューをブラウザで表示します。

    指定した記事の編集ページをブラウザで開きます。

    Args:
        article_key: プレビューする記事のキー

    Returns:
        プレビュー結果のメッセージ
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    await show_preview(session, article_key)
    return f"プレビューを表示しました。記事キー: {article_key}"
