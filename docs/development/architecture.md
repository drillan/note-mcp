# アーキテクチャ

note-mcpの内部アーキテクチャと主要コンポーネントについて説明します。

## 全体構造

```
src/note_mcp/
├── server.py          # MCPサーバーエントリーポイント
├── models.py          # データモデル定義
├── api/               # note.com API通信
│   ├── client.py      # HTTPクライアント
│   ├── articles.py    # 記事操作
│   └── images.py      # 画像操作
├── auth/              # 認証・セッション管理
│   ├── session.py     # セッションマネージャー
│   ├── browser.py     # ブラウザログイン
│   └── file_session.py # ファイルベースセッション
├── browser/           # ブラウザ自動化
│   ├── manager.py     # ブラウザマネージャー
│   ├── create_draft.py # 下書き作成
│   ├── get_article.py # 記事取得
│   ├── update_article.py # 記事更新
│   ├── preview.py     # プレビュー表示
│   ├── insert_image.py # 画像挿入
│   ├── toc_helpers.py # 目次挿入ヘルパー
│   ├── typing_helpers.py # 入力ヘルパー
│   └── url_helpers.py # URL操作ヘルパー
├── utils/             # ユーティリティ
│   ├── markdown_to_html.py # Markdown→HTML変換
│   ├── html_to_markdown.py # HTML→Markdown変換
│   ├── markdown.py    # Markdown共通処理
│   └── logging.py     # ロギング設定
└── investigator/      # API調査ツール
    ├── __main__.py    # CLIエントリーポイント
    ├── cli.py         # CLIコマンド定義
    ├── core.py        # キャプチャセッション
    └── mcp_tools.py   # MCPツール定義
```

## コンポーネント詳細

### MCPサーバー

FastMCPを使用してMCPプロトコルを実装しています。

```python
from fastmcp import FastMCP

mcp = FastMCP("note-mcp")

@mcp.tool()
async def note_login(timeout: int = 300) -> str:
    """note.comにログインします。"""
    ...
```

### 認証システム

セッション情報はOSのセキュアストレージ（keyring）に保存されます。

```
SessionManager
├── save_session()     # Cookieを保存
├── load_session()     # Cookieを読み込み
├── clear_session()    # セッション削除
└── is_authenticated() # 認証状態確認
```

Docker環境では`USE_FILE_SESSION=1`でファイルベースストレージを使用します。

### API通信

httpxを使用した非同期HTTPクライアントでnote.com APIと通信します。

```python
class NoteClient:
    async def get(self, path: str) -> dict
    async def post(self, path: str, data: dict) -> dict
    async def put(self, path: str, data: dict) -> dict
```

### ブラウザ自動化

Playwrightを使用してChromiumブラウザを操作します。

```
BrowserManager (Singleton)
├── get_page()         # ページ取得
├── close()            # ブラウザ終了
└── ensure_logged_in() # ログイン状態確認
```

シングルトンパターンにより、複数の操作間でブラウザインスタンスを再利用します。

### Markdown変換

note.comエディタ（ProseMirror）向けにMarkdownをHTMLに変換します。

```python
from note_mcp.utils.markdown_to_html import markdown_to_html

html = markdown_to_html("# タイトル\n本文")
```

変換時にルビ記法や数式記法も処理されます。

#### 目次（TOC）機能

`[TOC]`記法はnote.comのネイティブ目次機能に変換されます。

```
Markdown入力: [TOC]
    ↓
テキストプレースホルダ: §§TOC§§
    ↓
ブラウザ自動化でnote.com目次機能を挿入
```

プレースホルダはHTMLコメントではなく、テキストマーカー（`§§TOC§§`）を使用します。
これはProseMirrorエディタでテキストノードとして認識される必要があるためです。

`toc_helpers.py`がブラウザ操作を担当します：

1. `has_toc_placeholder()` - エディタ内のプレースホルダを検出
2. `insert_toc_at_placeholder()` - note.comの[+]ボタン→[目次]でTOC挿入

#### 埋め込み（Embed）機能

対応サービスのURLは、ブラウザ自動化でnote.comの埋め込みウィジェットに変換されます。

**対応サービス:**
- YouTube（youtube.com, youtu.be）
- Twitter/X（twitter.com, x.com）
- note.com記事

```
Markdown入力: https://www.youtube.com/watch?v=abc123
    ↓
URL検出: _is_embed_url()で対応サービスかを判定
    ↓
プレースホルダ挿入: §§EMBED:url§§ 形式でエディタに入力
    ↓
ブラウザ自動化: insert_embed.pyで[+]ボタン→[埋め込み]→URL入力
    ↓
埋め込みウィジェット: note.comが自動変換
```

**モジュール構成:**

- `typing_helpers.py` - URL検出とプレースホルダ挿入
  - `_is_embed_url()` - 対応サービスURLかを判定
  - `_EMBED_YOUTUBE_PATTERN`, `_EMBED_TWITTER_PATTERN`, `_EMBED_NOTE_PATTERN`

- `embed_helpers.py` - プレースホルダ検出と埋め込み適用
  - `has_embed_placeholders()` - エディタ内のプレースホルダを検出
  - `apply_embeds()` - 全プレースホルダを埋め込みに変換

- `insert_embed.py` - ブラウザ自動化で実際に埋め込み挿入
  - `insert_embed_at_cursor()` - カーソル位置に埋め込み挿入
  - note.comの「+」→「埋め込み」メニューを操作

> **注意**: 非対応サービスのURLは通常のリンクとして表示されます。埋め込みカードにはなりません。

#### リンク（Link）機能

Markdown記法 `[text](url)` はProseMirrorエディタで自動変換されません（InputRule未実装）。
このため、ブラウザ自動化でUI経由のリンク挿入を行います。

```
Markdown入力: [テキスト](https://example.com)
    ↓
パターン検出: type_link()でリンク記法を識別
    ↓
ブラウザ自動化: insert_link.pyでUI操作
    ↓
リンク挿入: エディタにリンクmark付きテキストが挿入
```

**モジュール構成:**

- `insert_link.py` - ブラウザ自動化でリンク挿入
  - `insert_link_at_cursor()` - カーソル位置にリンクを挿入
  - `LinkResult` - 挿入結果（SUCCESS, TIMEOUT）

> **注意**: 他のMarkdown書式（`**bold**`、`~~strikethrough~~`）は自動変換されますが、
> リンクはUI経由での挿入が必要です。

### Investigatorモード

`INVESTIGATOR_MODE=1`で有効になるAPI調査機能です。

```
CaptureSessionManager
├── start_capture()    # キャプチャ開始
├── stop_capture()     # キャプチャ停止
├── get_traffic()      # トラフィック取得
└── analyze()          # パターン分析
```

mitmproxyでHTTPトラフィックをキャプチャし、Playwrightでブラウザを操作します。

## データフロー

### 記事作成フロー

```
ユーザー入力 (Markdown)
    ↓
markdown_to_html() で変換
    ↓
note.com API または ブラウザ自動化
    ↓
note.com サーバー
```

### 認証フロー

```
note_login() 呼び出し
    ↓
Chromiumブラウザ起動
    ↓
ユーザーが手動ログイン
    ↓
認証Cookie取得
    ↓
keyring に保存
```

## 依存関係

| パッケージ | 用途 |
|-----------|------|
| fastmcp | MCPプロトコル実装 |
| playwright | ブラウザ自動化 |
| keyring | セキュアストレージ |
| httpx | 非同期HTTPクライアント |
| markdown-it-py | Markdown解析 |
| pydantic | データモデル |
| mitmproxy | HTTPトラフィックキャプチャ（dev） |

## 設計方針

### シンプルさ優先

- 最小限の抽象化
- 必要な機能のみ実装
- 明確なエラーメッセージ

### 再利用性

- BrowserManagerのシングルトンパターン
- 共通のMarkdown変換ユーティリティ
- 統一されたセッション管理

### テスタビリティ

- 非同期処理はasync/awaitで統一
- 依存性注入パターンの活用
- モック可能なインターフェース
