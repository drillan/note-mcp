# note-mcp

note.com記事管理用MCPサーバー。AIアシスタント（Claude Code, Claude Desktop等）から直接note.comの記事を作成・編集・公開できます。

⚠️ **注意**: このプロジェクトはnote.comの非公式APIを使用しています。詳細は[DISCLAIMER.md](DISCLAIMER.md)を参照してください。

## Features

- 🔐 **ブラウザ認証**: Playwrightでnote.comにログインし、セッションを安全に保存
- 📝 **記事作成**: Markdownで記事を作成し、下書きとして保存
- 📖 **記事取得**: 既存記事の内容（タイトル、本文、タグ等）を取得
- ✏️ **記事編集**: 既存記事の更新（取得→編集→保存のワークフロー）
- 🚀 **記事公開**: 下書きから公開へのワンステップ変更
- 🖼️ **画像アップロード**: アイキャッチ画像・記事内埋め込み画像のアップロード
  - アイキャッチ画像: 記事のサムネイル用
  - 本文用画像: S3直接アップロードでアイキャッチに影響なし
- 📋 **記事一覧**: 自分の記事一覧の取得
- 🔄 **Markdown→HTML変換**: 自動的にnote.com互換のHTML形式に変換

## Installation

```bash
# Install from GitHub
uv pip install git+https://github.com/drillan/note-mcp.git

# Install Playwright browser
playwright install chromium
```

### 開発用インストール

```bash
# Clone the repository
git clone https://github.com/drillan/note-mcp.git
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

#### アイキャッチ（見出し）画像

```
記事ID 12345678 に /path/to/eyecatch.png をアイキャッチ画像としてアップロードしてください
```

アイキャッチ画像は記事のサムネイルとして表示されます。

#### 記事内埋め込み画像

```
記事ID 12345678 に /path/to/inline.png を本文用画像としてアップロードし、記事に埋め込んでください
```

本文用画像をアップロードすると、Markdown形式の挿入コードが返されます。これを記事本文に追加することで画像を埋め込めます。

> **Note**: 本文用画像はS3への直接アップロードを使用するため、アイキャッチ画像には影響しません。

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
| `note_set_username` | ユーザー名を設定（セッション復元時に必要） |
| `note_create_draft` | 下書き記事を作成 |
| `note_get_article` | 記事内容を取得（タイトル、本文、タグ、ステータス等） |
| `note_update_article` | 記事を更新（先にnote_get_articleで内容取得を推奨） |
| `note_publish_article` | 記事を公開 |
| `note_list_articles` | 記事一覧を取得 |
| `note_upload_eyecatch` | アイキャッチ（見出し）画像をアップロード |
| `note_upload_body_image` | 記事本文用の埋め込み画像をアップロード |
| `note_show_preview` | ブラウザで記事プレビューを表示 |

## Security

### 認証情報の保存

セッション情報（Cookie、ユーザーID等）はOSのセキュアストレージに暗号化して保存されます：

| OS | 保存先 |
|----|--------|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | GNOME Keyring / libsecret |

保存される情報：
- 認証Cookie（`_note_session_v5`等）
- ユーザーID・ユーザー名
- セッション作成日時

### セキュリティ特性

- **OS暗号化**: 各OSのネイティブ暗号化機能を使用
- **ユーザー分離**: ログインユーザーのみがアクセス可能
- **自動管理**: `note_login`で保存、`note_logout`で削除

### Linux での追加設定

Linuxでは以下のいずれかが必要です：

```bash
# Ubuntu/Debian
sudo apt install gnome-keyring

# または
sudo apt install libsecret-1-0
```

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
