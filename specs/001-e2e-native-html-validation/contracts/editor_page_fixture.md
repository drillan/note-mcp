# Contract: editor_page Fixture

**Feature**: `001-e2e-native-html-validation`
**Type**: pytest fixture
**Location**: `tests/e2e/conftest.py`

## 概要

note.comエディタページを開いた状態のPlaywright Pageを提供するfixture。
既存の`real_session`と`draft_article` fixtureに依存。

## 署名

```python
@pytest_asyncio.fixture
async def editor_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page, None]:
    """エディタページを開いた状態のブラウザページ。

    Args:
        real_session: 認証済みセッション
        draft_article: テスト用下書き記事

    Yields:
        Page: ProseMirrorエディタが表示されたページ

    Raises:
        TimeoutError: エディタ要素が表示されない場合
    """
```

## 前提条件

1. `real_session` が有効な認証状態を持つ
2. `draft_article` が存在する下書き記事を指す
3. ネットワーク接続が利用可能

## 事後条件

1. ページはエディタURL（`https://editor.note.com/notes/{key}/edit/`）を表示
2. `.ProseMirror` 要素が表示されている
3. セッションCookieが注入されている

## 依存関係

```
editor_page
├── real_session (既存)
│   └── Session
└── draft_article (既存)
    └── Article
```

## 実装例

```python
@pytest_asyncio.fixture
async def editor_page(
    real_session: Session,
    draft_article: Article,
) -> AsyncGenerator[Page, None]:
    """エディタページを開いた状態のブラウザページ。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # セッションCookie注入
        await _inject_session_cookies(page, real_session)

        # エディタページへ移動
        editor_url = f"https://editor.note.com/notes/{draft_article.key}/edit/"
        await page.goto(editor_url)

        # ProseMirrorエディタ要素を待機
        await page.locator(".ProseMirror").wait_for(
            state="visible",
            timeout=30000,
        )

        yield page

        await context.close()
        await browser.close()


async def _inject_session_cookies(page: Page, session: Session) -> None:
    """セッションCookieをページに注入。"""
    # 既存のセッション管理から必要なCookieを取得・設定
    cookies = session.get_cookies()
    await page.context.add_cookies(cookies)
```

## エラー処理

| エラー条件 | 期待される動作 |
|-----------|---------------|
| セッション無効 | 認証エラーページが表示され、テスト失敗 |
| 記事が存在しない | 404エラー、テスト失敗 |
| エディタ要素タイムアウト | `TimeoutError` 発生 |
| ネットワークエラー | Playwright例外、テスト失敗 |

## テスト

```python
async def test_editor_page_loads(editor_page: Page) -> None:
    """editor_page fixtureがエディタを正しく開くことを確認。"""
    # ProseMirrorエディタが表示されている
    prosemirror = editor_page.locator(".ProseMirror")
    assert await prosemirror.count() > 0

    # フォーカス可能
    await prosemirror.click()
    assert await prosemirror.is_visible()
```
