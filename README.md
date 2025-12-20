# note-mcp

note.com記事管理用MCPサーバー。AIアシスタント（Claude Code, Claude Desktop等）から直接note.comの記事を作成・編集・公開できます。

⚠️ **注意**: このプロジェクトはnote.comの非公式APIを使用しています。詳細は[DISCLAIMER.md](DISCLAIMER.md)を参照してください。

## Features

- 🔐 **ブラウザ認証**: Playwrightでnote.comにログインし、セッションを安全に保存
- 📝 **記事作成**: Markdownで記事を作成し、下書きとして保存
- 📖 **記事取得**: 既存記事の内容（タイトル、本文、タグ等）を取得
- ✏️ **記事編集**: 既存記事の更新（取得→編集→保存のワークフロー）
- 🚀 **記事公開**: 下書きから公開へのワンステップ変更
- 🖼️ **画像アップロード**: 記事に挿入する画像のアップロード
- 📋 **記事一覧**: 自分の記事一覧の取得

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/note-mcp.git
cd note-mcp

# Install dependencies
uv sync

# Install Playwright browser
uv run playwright install chromium
```

## Configuration

### Claude Desktop

`~/.config/claude-desktop/config.json`（macOS/Linux）または `%APPDATA%\claude-desktop\config.json`（Windows）に以下を追加:

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

## Usage

### 1. ログイン

```
note.comにログインしてください
```

ブラウザが起動し、note.comのログインページが表示されます。手動でログインを完了すると、セッションがOSのキーチェーンに安全に保存されます。

### 2. 記事作成

```
以下の内容でnote.comに下書きを作成してください:

タイトル: AIと記事を書く
本文:
# はじめに
AIアシスタントと一緒に記事を書いてみましょう。
```

### 3. 画像アップロード

```
/path/to/image.png をnote.comにアップロードしてください
```

### 4. 記事編集（推奨ワークフロー）

既存記事を編集する際は、まず内容を取得してから編集を行います:

```
記事ID ne1c111d2073c の内容を取得してください
```

取得した内容を確認後、編集を依頼:

```
取得した記事の末尾に「まとめ」セクションを追加してください
```

AIが既存内容を把握した上で適切に編集を行います。

### 5. 記事公開

```
下書きを公開してください
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `note_login` | ブラウザでnote.comにログイン |
| `note_check_auth` | 認証状態を確認 |
| `note_logout` | ログアウト（セッション削除） |
| `note_create_draft` | 下書き記事を作成 |
| `note_get_article` | 記事内容を取得（タイトル、本文、タグ、ステータス等） |
| `note_update_article` | 記事を更新（先にnote_get_articleで内容取得を推奨） |
| `note_publish_article` | 記事を公開 |
| `note_list_articles` | 記事一覧を取得 |
| `note_upload_image` | 画像をアップロード |
| `note_show_preview` | ブラウザで記事プレビューを表示 |

## Requirements

- Python 3.11+
- デスクトップ環境（Playwrightが動作する環境）
- note.comアカウント

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run type checker
uv run mypy .
```

## License

MIT License

## Disclaimer

このプロジェクトはnote.comとは無関係の非公式ツールです。詳細は[DISCLAIMER.md](DISCLAIMER.md)を参照してください。
