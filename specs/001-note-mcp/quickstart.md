# Quickstart: note.com MCP Server

**Date**: 2025-12-20
**Feature**: 001-note-mcp

## Overview

note.com MCPサーバーを使用して、AIアシスタント（Claude等）からnote.comの記事を管理する方法を説明します。

---

## Prerequisites

1. **note.comアカウント**: 事前にnote.comでアカウントを作成しておく
2. **Python 3.11+**: インストール済み
3. **Playwright対応環境**: デスクトップPC（Windows/macOS/Linux）

---

## Installation

```bash
# リポジトリをクローン
git clone https://github.com/your-username/note-mcp.git
cd note-mcp

# 依存関係をインストール
uv sync

# Playwrightブラウザをインストール
uv run playwright install chromium
```

---

## Configuration

### Claude Desktop

`~/.config/claude-desktop/config.json`（macOS/Linux）または
`%APPDATA%\claude-desktop\config.json`（Windows）に以下を追加:

```json
{
  "mcpServers": {
    "note-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "note_mcp"],
      "cwd": "/path/to/note-mcp"
    }
  }
}
```

---

## Basic Usage

### 1. ログイン

最初に認証が必要です。ブラウザが起動するので、手動でログインしてください。

**Claude Code/Desktopで:**
```
note.comにログインしてください
```

**MCPツール呼び出し:**
```
note_login
```

ブラウザが起動し、note.comのログインページが表示されます。ログインを完了すると、セッションが保存されます。

### 2. 記事の下書き作成

**Claude Code/Desktopで:**
```
以下の内容でnote.comに下書きを作成してください:

タイトル: AIと共に記事を書く方法
本文:
# はじめに
この記事では、AIアシスタントを使って記事を執筆する方法を紹介します。

## AIとの対話
...
```

**MCPツール呼び出し:**
```
note_create_draft(
  title="AIと共に記事を書く方法",
  body="# はじめに\n..."
)
```

作成後、ブラウザで記事のプレビューが表示されます。

### 3. 記事の更新

**Claude Code/Desktopで:**
```
先ほど作成した記事に、以下のセクションを追加してください:

## まとめ
AIと協力することで、より効率的に記事を書けるようになります。
```

**MCPツール呼び出し:**
```
note_update_article(
  article_id="xxx",
  body="..."  # 更新後の全文
)
```

### 4. 画像のアップロード

**Claude Code/Desktopで:**
```
/path/to/image.png をnote.comにアップロードして、
記事に挿入できるURLを取得してください
```

**MCPツール呼び出し:**
```
note_upload_image(file_path="/path/to/image.png")
```

返されるURLを記事本文のMarkdown内で使用できます:
```markdown
![画像の説明](https://returned-image-url.com/image.png)
```

### 5. 記事の公開

**Claude Code/Desktopで:**
```
下書きを公開してください
```

**MCPツール呼び出し:**
```
note_publish_article(article_id="xxx")
```

### 6. 記事一覧の取得

**Claude Code/Desktopで:**
```
私のnote.comの下書き一覧を見せてください
```

**MCPツール呼び出し:**
```
note_list_articles(status="draft")
```

---

## Interactive Workflow Example

Claude Codeとの対話的なワークフローの例:

```
User: note.comで「プログラミング入門」という記事を書きたいです

Claude: かしこまりました。まず、note.comにログインする必要があります。
        ログインツールを実行しますか？

User: はい

[ブラウザが起動、ユーザーがログイン]

Claude: ログインが完了しました。記事の構成を考えましょう。
        どのような内容を含めたいですか？

User: Pythonの基礎、変数、ループについて

Claude: 以下の構成で下書きを作成します:
        # プログラミング入門
        ## Pythonとは
        ## 変数の基本
        ## ループ処理

        この構成でよろしいですか？

User: はい

Claude: [note_create_draft実行]
        下書きを作成しました。ブラウザでプレビューをご確認ください。
        内容を追加・修正する場合はお知らせください。

User: 「変数の基本」セクションにコード例を追加してください

Claude: [note_update_article実行]
        コード例を追加しました。プレビューで確認してください。

User: 良いですね。公開してください

Claude: [note_publish_article実行]
        記事を公開しました！URL: https://note.com/username/n/xxx
```

---

## Error Handling

### 認証エラー

```
NOT_AUTHENTICATED: 認証されていません
```

→ `note_login`ツールでログインしてください

### セッション期限切れ

```
SESSION_EXPIRED: セッションの有効期限が切れました
```

→ 再度`note_login`でログインしてください

### レート制限

```
RATE_LIMITED: リクエストが多すぎます
```

→ 1分程度待ってからリトライしてください（目安: 10リクエスト/分）

---

## Troubleshooting

### ブラウザが起動しない

Playwrightが正しくインストールされているか確認:
```bash
uv run playwright install chromium
```

### セッションが保存されない

keyringが正しく動作しているか確認:
```bash
uv run python -c "import keyring; print(keyring.get_keyring())"
```

### API呼び出しが失敗する

note.comの仕様変更の可能性があります。最新バージョンに更新してください:
```bash
git pull
uv sync
```

---

## Disclaimer

- このMCPサーバーはnote.comの非公式APIを使用しています
- note.comの仕様変更により動作しなくなる可能性があります
- **自己責任**でご使用ください
- **無保証**です
