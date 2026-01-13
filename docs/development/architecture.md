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
├── browser/           # ブラウザ操作（ログイン・プレビュー用）
│   ├── manager.py     # ブラウザライフサイクル管理
│   ├── preview.py     # プレビュー表示
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

### ブラウザ操作

Playwrightを使用したブラウザ操作は、**ログイン**と**プレビュー表示**のみに限定されています。
コンテンツ操作（記事作成・更新・画像挿入等）はすべてAPI経由で行われます。

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

変換時に数式記法も処理されます。

#### 目次（TOC）機能

`[TOC]`記法はnote.comのネイティブ目次機能に変換されます。

```
Markdown入力: [TOC]
    ↓
HTML変換: note.com目次用のiframe埋め込みHTML
    ↓
API経由で記事に保存
```

目次はAPI経由でHTML形式で直接送信されます。

#### 埋め込み（Embed）機能

対応サービスのURLは、API経由でnote.comの埋め込みウィジェットに変換されます。

**対応サービス:**
- YouTube（youtube.com, youtu.be）
- Twitter/X（twitter.com, x.com）
- note.com記事

```
Markdown入力: https://www.youtube.com/watch?v=abc123
    ↓
URL検出: 対応サービスかを判定
    ↓
HTML変換: note.com埋め込み用のiframe HTML生成
    ↓
API経由で記事に保存
```

> **注意**: 非対応サービスのURLは通常のリンクとして表示されます。埋め込みカードにはなりません。

#### リンク（Link）機能

Markdown記法 `[text](url)` はAPI経由でHTMLリンクに変換されます。

```
Markdown入力: [テキスト](https://example.com)
    ↓
HTML変換: <a href="https://example.com">テキスト</a>
    ↓
API経由で記事に保存
```

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
