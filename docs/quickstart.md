# クイックスタート

このガイドでは、note-mcpのインストールから最初の記事作成までを説明します。

## インストール

### パッケージのインストール

```bash
# GitHubからインストール
uv pip install git+https://github.com/drillan/note-mcp.git

# Playwrightブラウザのインストール
playwright install chromium
```

### 開発用インストール

```bash
# リポジトリをクローン
git clone https://github.com/drillan/note-mcp.git
cd note-mcp

# 依存関係のインストール
uv sync

# Playwrightブラウザのインストール
uv run playwright install chromium
```

## 設定

MCPクライアントの設定ファイルに以下を追加します。`cwd` はインストール方法によって異なります。

### インストール方法別の設定

#### パッケージインストールの場合

`uv pip install git+...` でインストールした場合、`cwd` は **note-mcpを使用するプロジェクトのディレクトリ** を指定します：

```json
{
  "mcpServers": {
    "note-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "note_mcp"],
      "cwd": "/path/to/your-project"
    }
  }
}
```

#### 開発用インストールの場合

`git clone` + `uv sync` でインストールした場合、`cwd` は **クローンしたリポジトリのディレクトリ** を指定します：

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

### MCPクライアント別の設定ファイル

| クライアント | 設定ファイル |
|-------------|-------------|
| Claude Code | `~/.claude.json` または `.mcp.json` |
| Claude Desktop | `~/.config/claude-desktop/config.json` (macOS/Linux) |
| | `%APPDATA%\claude-desktop\config.json` (Windows) |
| VS Code (Copilot Chat, Cline, Continue等) | `.vscode/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |

### Claude Code

グローバル設定（`~/.claude.json`）またはプロジェクト設定（`.mcp.json`）に追加：

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

### Claude Desktop

`~/.config/claude-desktop/config.json`（macOS/Linux）または `%APPDATA%\claude-desktop\config.json`（Windows）に追加：

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

### VS Code拡張 (Copilot Chat, Cline, Continue等)

`.vscode/mcp.json` に追加：

```json
{
  "servers": {
    "note-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "note_mcp"],
      "cwd": "/path/to/note-mcp"
    }
  }
}
```

### Cursor

`.cursor/mcp.json` に追加：

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

### Windsurf

`~/.codeium/windsurf/mcp_config.json` に追加：

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

## 最初のログイン

note-mcpを使用するには、まずnote.comにログインする必要があります。

```
note.comにログインしてください
```

ブラウザが起動し、note.comのログインページが表示されます。手動でログインを完了すると、セッション情報がOSのセキュアストレージに保存されます。

認証状態は以下のコマンドで確認できます：

```
認証状態を確認してください
```

詳細は[認証ガイド](guide/authentication.md)を参照してください。

## 最初の記事を作成

ログイン後、以下のようにして記事を作成できます：

```
以下の内容でnote.comに下書きを作成してください:

タイトル: AIと記事を書く
本文:
# はじめに
AIアシスタントと一緒に記事を書いてみましょう。

## Markdownの活用
note-mcpはMarkdown形式をサポートしています。
- リスト
- **太字**
- ~~取り消し線~~

すべて自動的にnote.com形式に変換されます。
```

記事が作成されると、記事IDとプレビューURLが表示されます。

## 次のステップ

- [認証ガイド](guide/authentication.md) - 認証フローの詳細
- [記事操作ガイド](guide/articles.md) - 記事の作成・編集・公開
- [画像ガイド](guide/images.md) - 画像のアップロード
- [APIリファレンス](api/reference.md) - 全MCPツールの詳細
