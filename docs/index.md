# note-mcp ドキュメント

note.com記事管理用MCPサーバーのドキュメントです。

## 概要

note-mcpは、AIアシスタント（Claude Code、Claude Desktop等）からnote.comの記事を直接作成・編集・公開するためのMCPサーバーです。

### 主な機能

- 記事の作成・更新・公開
- 画像のアップロード・挿入
- セキュアな認証管理
- 数式・目次記法のサポート
- API調査ツール（Investigatorモード）

## ドキュメント

```{toctree}
:caption: 'ガイド'
:maxdepth: 2

quickstart
guide/authentication
guide/articles
guide/images
guide/browser
```

```{toctree}
:caption: 'APIリファレンス'
:maxdepth: 2

api/reference
api/investigator
```

```{toctree}
:caption: '機能詳細'
:maxdepth: 2

features/math
features/toc
features/embed
features/link
features/text-align
```

```{toctree}
:caption: '開発者向け'
:maxdepth: 2

development/architecture
development/testing
development/troubleshooting
development/contributing
```

## クイックスタート

### インストール

```bash
# uvを使用（推奨）
uv pip install note-mcp

# または pip
pip install note-mcp
```

### MCPクライアントの設定

Claude Desktopの`claude_desktop_config.json`に追加：

```json
{
  "mcpServers": {
    "note-mcp": {
      "command": "uv",
      "args": ["run", "--from", "note-mcp", "note-mcp"]
    }
  }
}
```

### 最初の記事を作成

```
1. note_login でログイン
2. note_create_draft でタイトルと本文を指定して下書き作成
3. note_publish_article で公開
```

詳細は[クイックスタートガイド](quickstart.md)を参照してください。

## リンク

- [GitHub リポジトリ](https://github.com/drillan/note-mcp)
- [PyPI パッケージ](https://pypi.org/project/note-mcp/)
- [note.com](https://note.com/)
