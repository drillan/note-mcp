# Research: プレビューAPI対応

**Feature**: 002-preview-api
**Date**: 2025-01-13
**Status**: Complete

## Overview

note.com MCP Serverのプレビュー機能をAPI経由に改善するための技術調査結果。

## Research Topics

### 1. Preview Access Token API

**Decision**: `POST /api/v2/notes/{article_key}/access_tokens` エンドポイントを使用

**Rationale**:
- 既存の`src/note_mcp/api/articles.py`で検証済みのパターン
- リクエストボディ: `{"key": article_key}`
- レスポンス形式: `{"data": {"preview_access_token": "32文字hex文字列"}}`
- note.com APIの標準的な`data`ラッパー形式に準拠

**Alternatives Considered**:
| 代替案 | 却下理由 |
|--------|----------|
| GETリクエスト | RESTの慣例に反する（アクション系エンドポイント） |
| リクエストボディなし | APIが`{"key": article_key}`を要求 |

### 2. httpx認証パターン

**Decision**: NoteAPIClientパターンを再利用（async context manager + 手動Cookie設定）

**Rationale**:
- 既存の`src/note_mcp/api/client.py`で実装済み・テスト済み
- httpxはrequestsライブラリと異なり自動Cookie管理がないため手動設定が必要
- Context managerパターンで確実なリソース解放

**Key Implementation Patterns**:

1. **クライアントライフサイクル管理**:
   ```python
   async with NoteAPIClient(session) as client:
       response = await client.post(...)
   ```

2. **Cookie注入**:
   ```python
   cookie_parts = [f"{k}={v}" for k, v in session.cookies.items()]
   headers["Cookie"] = "; ".join(cookie_parts)
   ```

3. **XSRFトークン処理（POSTリクエスト用）**:
   ```python
   if include_xsrf:
       xsrf_token = session.cookies.get("XSRF-TOKEN")
       if xsrf_token:
           headers["X-XSRF-TOKEN"] = xsrf_token
   ```

**Alternatives Considered**:
| 代替案 | 却下理由 |
|--------|----------|
| requestsライブラリ | 同期のみ、async非対応 |
| httpx.Client(cookies=dict) | Sessionモデルとの互換性なし |

### 3. Playwrightプレビュー表示

**Decision**: API経由でトークン取得後、直接プレビューURLにナビゲート

**Rationale**:
- 現行のエディター経由方式（15秒）より80%高速化（3秒以内）
- メニューボタンクリック等のUI操作が不要になり安定性向上
- 既存のBrowserManagerシングルトンパターンを再利用

**Implementation Pattern**:
```python
# 1. APIでトークン取得（~200ms）
token = await get_preview_access_token(session, article_key)

# 2. プレビューURL構築
preview_url = f"https://note.com/preview/{article_key}?prev_access_key={token}"

# 3. 直接ナビゲート（~2-3秒）
await page.goto(preview_url, wait_until="domcontentloaded")
await page.wait_for_load_state("networkidle")
```

**Wait Strategies**:
- `domcontentloaded`: DOM解析完了（最低限）
- `networkidle`: 全リソース読込完了、JavaScript実行完了（数式レンダリングに必要）

**Alternatives Considered**:
| 代替案 | 却下理由 |
|--------|----------|
| エディター経由（現行） | 遅い（15秒）、UI操作に依存し不安定 |
| window.open() + JavaScript | 信頼性が低い |

### 4. HTML取得（プログラム用）

**Decision**: httpx.AsyncClientでプレビューURLを直接fetch

**Rationale**:
- ブラウザ起動不要で高速（~500ms vs ~3秒）
- メモリ使用量が少ない（<10MB vs >100MB）
- 静的HTML取得にはPlaywrightはオーバースペック

**Implementation Pattern**:
```python
async def get_preview_html(session: Session, article_key: str) -> str:
    # 1. APIでトークン取得
    token = await get_preview_access_token(session, article_key)

    # 2. プレビューURL構築
    preview_url = build_preview_url(article_key, token)

    # 3. httpxでHTML取得
    async with httpx.AsyncClient(timeout=30) as client:
        cookie_header = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
        response = await client.get(preview_url, headers={"Cookie": cookie_header})
        return response.text
```

**Performance Comparison**:
| 手法 | 速度 | メモリ | CPU | ユースケース |
|------|------|--------|-----|-------------|
| httpx | ~500ms | <10MB | 低 | 静的HTML取得 |
| Playwright | ~3秒 | >100MB | 高 | インタラクティブテスト |

**Alternatives Considered**:
| 代替案 | 却下理由 |
|--------|----------|
| Playwright page.content() | オーバースペック、遅い |
| requests | async非対応 |

## Version Information

調査時点での依存ライブラリバージョン（pyproject.toml確認済み）:

| ライブラリ | 現行バージョン | 備考 |
|-----------|---------------|------|
| httpx | >=0.27.0 | 既存で使用中 |
| playwright | >=1.40.0 | 既存で使用中 |
| fastmcp | >=2.0.0 | MCPサーバーフレームワーク |
| pydantic | >=2.0.0 | データ検証 |

## Constitution Compliance

| Article | 遵守状況 | 備考 |
|---------|---------|------|
| Article 3 (MCP準拠) | ✅ | Pydanticモデル使用、適切なエラーコード |
| Article 5 (コード品質) | ✅ | 型安全なhttpx使用、適切なasync/await |
| Article 6 (データ正確性) | ✅ | APIからトークン取得、ハードコード禁止 |
| Article 7 (DRY) | ✅ | NoteAPIClient再利用、既存パターン踏襲 |

## Summary

| 調査項目 | 決定事項 | 実装方式 | 性能 |
|---------|---------|---------|------|
| APIエンドポイント | POST /v2/notes/{key}/access_tokens | `json={"key": article_key}` | ~200ms |
| httpx認証 | Async context manager + 手動Cookie | NoteAPIClientパターン | ~50-100ms |
| Playwrightタブ | API経由で直接ナビゲート | open_preview_via_api() | ~3秒（15秒から改善） |
| HTML取得 | httpxでプレビューURL fetch | get_preview_html() | ~500ms |
