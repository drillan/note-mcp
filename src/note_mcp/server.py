"""FastMCP server for note.com article management.

Provides MCP tools for creating, updating, and managing note.com articles.
Supports investigator mode for API investigation via INVESTIGATOR_MODE=1.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastmcp import FastMCP

from note_mcp.api.articles import (
    create_draft,
    get_article,
    list_articles,
    publish_article,
    update_article,
)
from note_mcp.api.images import upload_body_image, upload_eyecatch_image
from note_mcp.auth.browser import login_with_browser
from note_mcp.auth.session import SessionManager
from note_mcp.browser.create_draft import create_draft_via_browser
from note_mcp.browser.insert_image import insert_image_via_browser
from note_mcp.browser.preview import show_preview
from note_mcp.browser.update_article import update_article_via_browser
from note_mcp.investigator import register_investigator_tools
from note_mcp.models import ArticleInput, ArticleStatus, NoteAPIError
from note_mcp.utils.file_parser import parse_markdown_file
from note_mcp.utils.markdown_to_html import (
    _has_toc_placeholder,
    has_embed_url,
    has_math_formula,
)

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
async def note_set_username(
    username: Annotated[str, "note.comのユーザー名（URLに表示される名前、例: your_username）"],
) -> str:
    """ユーザー名を手動で設定します。

    ログイン時にユーザー名の自動取得に失敗した場合に使用します。
    ユーザー名はnote.comのプロフィールURLから確認できます。
    例: https://note.com/your_username → your_username

    Args:
        username: note.comのユーザー名

    Returns:
        設定結果のメッセージ
    """
    from note_mcp.models import Session

    if not _session_manager.has_session():
        return "セッションが存在しません。先にnote_loginを実行してください。"

    session = _session_manager.load()
    if session is None:
        return "セッションの読み込みに失敗しました。note_loginで再ログインしてください。"

    # Validate username format
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return "無効なユーザー名です。英数字、アンダースコア、ハイフンのみ使用できます。"

    # Create updated session with new username
    updated_session = Session(
        cookies=session.cookies,
        user_id=username,  # Use username as user_id
        username=username,
        expires_at=session.expires_at,
        created_at=session.created_at,
    )

    _session_manager.save(updated_session)
    return f"ユーザー名を '{username}' に設定しました。"


@mcp.tool()
async def note_create_draft(
    title: Annotated[str, "記事のタイトル"],
    body: Annotated[str, "記事の本文（Markdown形式）"],
    tags: Annotated[list[str] | None, "記事のタグ（#なしでも可）"] = None,
) -> str:
    """note.comに下書き記事を作成します。

    Markdown形式の本文をHTMLに変換してnote.comに送信します。
    blockquote内の引用（— 出典名）はfigcaptionに自動入力されます。
    作成後、ブラウザでプレビューを表示します。

    [TOC]マーカーを含む記事は目次を自動挿入するため、
    ブラウザ自動化を使用して作成されます。

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

    # Use browser-based creation for articles with [TOC] marker, embed URLs, or math formulas
    # TOC insertion, embed insertion, and math formulas require browser automation
    toc_info = ""
    embed_info = ""
    use_browser = _has_toc_placeholder(body) or has_embed_url(body) or has_math_formula(body)

    if use_browser:
        result = await create_draft_via_browser(session, article_input)
        article = result.article
        # Add TOC status to response
        if result.toc_inserted:
            toc_info = "、目次: 挿入済み"
        elif result.toc_error:
            toc_info = f"、目次: 挿入失敗（{result.toc_error}）"
        elif result.toc_inserted is None:
            pass  # TOC not attempted (no placeholder found after typing)
        # Add embed status to response
        if result.embeds_inserted is not None and result.embeds_inserted > 0:
            embed_info = f"、埋め込み: {result.embeds_inserted}件"
        elif result.embed_error:
            embed_info = f"、埋め込み: 失敗（{result.embed_error}）"
        # Add debug info if present
        debug_info = f"、DEBUG: {result.debug_info}" if result.debug_info else ""
    else:
        article = await create_draft(session, article_input)
        # Show preview in browser (browser-based creation already shows editor)
        await show_preview(session, article.key)
        debug_info = ""

    tag_info = f"、タグ: {', '.join(article.tags)}" if article.tags else ""
    return f"下書きを作成しました。ID: {article.id}、キー: {article.key}{tag_info}{toc_info}{embed_info}{debug_info}"


@mcp.tool()
async def note_get_article(
    article_id: Annotated[str, "取得する記事のID"],
) -> str:
    """記事の内容を取得します。

    指定したIDの記事のタイトル、本文、ステータスを取得します。
    記事を編集する前に既存内容を確認する際に使用します。

    推奨ワークフロー:
    1. note_get_article で既存内容を取得
    2. 取得した内容を元に編集を決定
    3. note_update_article で更新を保存

    Args:
        article_id: 取得する記事のID

    Returns:
        記事の内容（タイトル、本文、ステータス）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    try:
        article = await get_article(session, article_id)
    except NoteAPIError as e:
        return f"記事の取得に失敗しました: {e}"

    tag_info = f"\nタグ: {', '.join(article.tags)}" if article.tags else ""

    return f"""記事を取得しました。

タイトル: {article.title}
ステータス: {article.status.value}{tag_info}

本文:
{article.body}"""


@mcp.tool()
async def note_update_article(
    article_id: Annotated[str, "更新する記事のID"],
    title: Annotated[str, "新しいタイトル"],
    body: Annotated[str, "新しい本文（Markdown形式）"],
    tags: Annotated[list[str] | None, "新しいタグ（#なしでも可）"] = None,
) -> str:
    """既存の記事を更新します。

    編集前にnote_get_articleで既存内容を取得することを推奨します。
    Markdown形式の本文をHTMLに変換してnote.comに送信します。

    [TOC]マーカーを含む記事は目次を自動挿入するため、
    ブラウザ自動化を使用して更新されます。

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

    # Use browser-based update for articles with [TOC] marker, embed URLs, or math formulas
    # TOC insertion, embed insertion, and math formulas require browser automation
    toc_info = ""
    embed_info = ""
    use_browser = _has_toc_placeholder(body) or has_embed_url(body) or has_math_formula(body)

    if use_browser:
        result = await update_article_via_browser(session, article_id, article_input)
        article = result.article
        # Add TOC status to response
        if result.toc_inserted:
            toc_info = "、目次: 挿入済み"
        elif result.toc_error:
            toc_info = f"、目次: 挿入失敗（{result.toc_error}）"
        # Add embed status to response
        if result.embeds_inserted is not None and result.embeds_inserted > 0:
            embed_info = f"、埋め込み: {result.embeds_inserted}件"
        elif result.embed_error:
            embed_info = f"、埋め込み: 失敗（{result.embed_error}）"
    else:
        article = await update_article(session, article_id, article_input)

    tag_info = f"、タグ: {', '.join(article.tags)}" if article.tags else ""
    return f"記事を更新しました。ID: {article.id}{tag_info}{toc_info}{embed_info}"


@mcp.tool()
async def note_upload_eyecatch(
    file_path: Annotated[str, "アップロードする画像ファイルのパス"],
    note_id: Annotated[str, "画像を関連付ける記事のID（数字のみ）"],
) -> str:
    """記事のアイキャッチ（見出し）画像をアップロードします。

    JPEG、PNG、GIF、WebP形式の画像をアップロードできます。
    最大ファイルサイズは10MBです。
    アップロードした画像は記事の見出し画像として設定されます。

    note_list_articlesで記事一覧を取得し、IDを確認できます。

    Args:
        file_path: アップロードする画像ファイルのパス
        note_id: 画像を関連付ける記事のID

    Returns:
        アップロード結果（画像URLを含む）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    try:
        image = await upload_eyecatch_image(session, file_path, note_id=note_id)
        return f"アイキャッチ画像をアップロードしました。URL: {image.url}"
    except NoteAPIError as e:
        return f"エラー: {e}"


@mcp.tool()
async def note_upload_body_image(
    file_path: Annotated[str, "アップロードする画像ファイルのパス"],
    note_id: Annotated[str, "画像を関連付ける記事のID（数字のみ）"],
) -> str:
    """記事本文内に埋め込む画像をアップロードします。

    JPEG、PNG、GIF、WebP形式の画像をアップロードできます。
    最大ファイルサイズは10MBです。

    **重要**: このツールは画像をアップロードしてURLを返すだけです。
    画像を記事に直接挿入するには note_insert_body_image を使用してください。

    note_list_articlesで記事一覧を取得し、IDを確認できます。

    Args:
        file_path: アップロードする画像ファイルのパス
        note_id: 画像を関連付ける記事のID

    Returns:
        アップロード結果（画像URLを含む）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    try:
        image = await upload_body_image(session, file_path, note_id=note_id)
        return (
            f"本文用画像をアップロードしました。URL: {image.url}\n\n"
            f"※画像を記事に直接挿入するには note_insert_body_image を使用してください。"
        )
    except NoteAPIError as e:
        return f"エラー: {e}"


@mcp.tool()
async def note_insert_body_image(
    file_path: Annotated[str, "挿入する画像ファイルのパス"],
    article_key: Annotated[str, "画像を挿入する記事のキー（例: n1234567890ab）"],
    caption: Annotated[str | None, "画像のキャプション（オプション）"] = None,
) -> str:
    """記事本文内に画像を直接挿入します。

    ブラウザ自動化を使用してnote.comエディタに画像を挿入します。
    JPEG、PNG、GIF、WebP形式の画像を挿入できます。
    最大ファイルサイズは10MBです。

    note.comのAPIでは画像のHTML埋め込みが正しく保存されないため、
    このツールはブラウザ経由でエディタの「画像を追加」機能を使用します。

    note_list_articlesで記事一覧を取得し、キーを確認できます。

    Args:
        file_path: 挿入する画像ファイルのパス
        article_key: 画像を挿入する記事のキー（例: n1234567890ab）
        caption: 画像のキャプション（オプション）

    Returns:
        挿入結果のメッセージ
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    result = await insert_image_via_browser(
        session=session,
        article_key=article_key,
        file_path=file_path,
        caption=caption,
    )

    if result["success"]:
        caption_info = f"、キャプション: {result['caption']}" if result.get("caption") else ""
        return f"画像を挿入しました。記事キー: {result['article_key']}{caption_info}"
    else:
        return "画像の挿入に失敗しました。"


@mcp.tool()
async def note_show_preview(
    article_key: Annotated[str, "プレビューする記事のキー（例: n1234567890ab）"],
) -> str:
    """記事のプレビューをブラウザで表示します。

    指定した記事のプレビューページをブラウザで開きます。
    下書き記事の場合、プレビュー用アクセスキーを使用して表示します。

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


@mcp.tool()
async def note_publish_article(
    article_id: Annotated[str | None, "公開する下書き記事のID（新規作成時は省略）"] = None,
    title: Annotated[str | None, "記事タイトル（新規作成時は必須）"] = None,
    body: Annotated[str | None, "記事本文（Markdown形式、新規作成時は必須）"] = None,
    tags: Annotated[list[str] | None, "記事のタグ（#なしでも可）"] = None,
) -> str:
    """記事を公開します。

    既存の下書きを公開するか、新規記事を作成して即公開できます。
    article_idを指定すると既存の下書きを公開します。
    title/bodyを指定すると新規記事を作成して公開します。

    Args:
        article_id: 公開する下書き記事のID（新規作成時は省略）
        title: 記事タイトル（新規作成時は必須）
        body: 記事本文（Markdown形式、新規作成時は必須）
        tags: 記事のタグ（オプション）

    Returns:
        公開結果のメッセージ（記事URLを含む）
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    # Determine whether to publish existing or create new
    if article_id is not None:
        # Publish existing draft
        article = await publish_article(session, article_id=article_id)
    elif title is not None and body is not None:
        # Create and publish new article
        article_input = ArticleInput(
            title=title,
            body=body,
            tags=tags or [],
        )
        article = await publish_article(session, article_input=article_input)
    else:
        return "article_idまたは（titleとbody）のいずれかを指定してください。"

    url_info = f"、URL: {article.url}" if article.url else ""
    return f"記事を公開しました。ID: {article.id}{url_info}"


@mcp.tool()
async def note_list_articles(
    status: Annotated[str | None, "フィルタするステータス（draft/published/all）"] = None,
    page: Annotated[int, "ページ番号（1から開始）"] = 1,
    limit: Annotated[int, "1ページあたりの記事数（最大10）"] = 10,
) -> str:
    """自分の記事一覧を取得します。

    ステータスでフィルタリングできます。

    Args:
        status: フィルタするステータス（draft/published/all、省略時はall）
        page: ページ番号（1から開始）
        limit: 1ページあたりの記事数（最大10）

    Returns:
        記事一覧の情報
    """
    session = _session_manager.load()
    if session is None or session.is_expired():
        return "セッションが無効です。note_loginでログインしてください。"

    # Convert status string to ArticleStatus enum
    status_filter: ArticleStatus | None = None
    if status is not None and status != "all":
        try:
            status_filter = ArticleStatus(status)
        except ValueError:
            return f"無効なステータスです: {status}。draft/published/allのいずれかを指定してください。"

    result = await list_articles(session, status=status_filter, page=page, limit=limit)

    if not result.articles:
        return "記事が見つかりませんでした。"

    # Format article list
    lines = [f"記事一覧（{result.total}件中{len(result.articles)}件、ページ{result.page}）:"]
    for article in result.articles:
        status_label = "下書き" if article.status == ArticleStatus.DRAFT else "公開済み"
        lines.append(f"  - [{status_label}] {article.title} (ID: {article.id})")

    if result.has_more:
        lines.append(f"  （続きはpage={result.page + 1}で取得できます）")

    return "\n".join(lines)


@mcp.tool()
async def note_create_from_file(
    file_path: Annotated[str, "Markdownファイルのパス"],
    upload_images: Annotated[bool, "ローカル画像をアップロードするかどうか"] = True,
) -> str:
    """Markdownファイルから下書き記事を作成します。

    ファイルからタイトル、本文、タグ、ローカル画像を抽出し、
    note.comに下書きを作成します。

    YAMLフロントマターがある場合:
    - titleフィールドからタイトルを取得
    - tagsフィールドからタグを取得

    フロントマターがない場合:
    - 最初のH1見出しをタイトルとして使用（本文から削除）
    - H1がなければH2を使用

    ローカル画像（./images/example.pngなど）は自動的にアップロードされ、
    本文内のパスがnote.comのURLに置換されます。

    Args:
        file_path: Markdownファイルのパス
        upload_images: ローカル画像をアップロードするかどうか（デフォルト: True）

    Returns:
        作成結果のメッセージ（記事IDを含む）
    """
    session = _session_manager.load()
    if session is None:
        return "ログインが必要です。note_loginを実行してください。"

    from pathlib import Path

    try:
        parsed = parse_markdown_file(Path(file_path))
    except FileNotFoundError:
        return f"ファイルが見つかりません: {file_path}"
    except ValueError as e:
        return f"ファイル解析エラー: {e}"

    article_input = ArticleInput(
        title=parsed.title,
        body=parsed.body,
        tags=parsed.tags,
    )

    # Math formulas also require browser automation for KaTeX rendering
    needs_browser = _has_toc_placeholder(parsed.body) or has_embed_url(parsed.body) or has_math_formula(parsed.body)

    try:
        if needs_browser:
            browser_result = await create_draft_via_browser(session, article_input)
            article = browser_result.article
        else:
            article = await create_draft(session, article_input)

        uploaded_count = 0
        failed_images: list[str] = []

        if upload_images and parsed.local_images:
            updated_body = parsed.body

            for img in parsed.local_images:
                if img.absolute_path.exists():
                    try:
                        upload_result = await upload_body_image(
                            session,
                            str(img.absolute_path),
                            article.id,
                        )
                        updated_body = updated_body.replace(
                            f"({img.markdown_path})",
                            f"({upload_result.url})",
                        )
                        uploaded_count += 1
                    except NoteAPIError as e:
                        failed_images.append(f"{img.markdown_path}: {e}")
                else:
                    failed_images.append(f"{img.markdown_path}: ファイルが見つかりません")

            if uploaded_count > 0:
                updated_input = ArticleInput(
                    title=parsed.title,
                    body=updated_body,
                    tags=parsed.tags,
                )
                await update_article(session, article.id, updated_input)

        result_lines = [
            "✅ 下書きを作成しました",
            f"   タイトル: {article.title}",
            f"   記事ID: {article.id}",
            f"   記事キー: {article.key}",
        ]

        if uploaded_count > 0:
            result_lines.append(f"   アップロードした画像: {uploaded_count}件")

        if failed_images:
            result_lines.append(f"   ⚠️ 画像アップロード失敗: {len(failed_images)}件")
            for msg in failed_images:
                result_lines.append(f"      - {msg}")

        return "\n".join(result_lines)

    except NoteAPIError as e:
        return f"記事作成エラー: {e}"


# Register investigator tools if in investigator mode
if os.environ.get("INVESTIGATOR_MODE") == "1":
    register_investigator_tools(mcp)
