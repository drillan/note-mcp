# リンク機能

note.comの記事にリンクを挿入する機能です。

## 概要

Markdown記法 `[text](url)` を使用してリンクを挿入できます。
note-mcpはMarkdownをHTMLに変換し、API経由で記事に保存します。

## 使用方法

### 基本的なリンク挿入

記事本文にリンクを含むMarkdownを記述します。

```markdown
詳細は[公式ドキュメント](https://example.com/docs)を参照してください。
```

### 技術的な動作

```
Markdown入力: [公式ドキュメント](https://example.com/docs)
    ↓
HTML変換: <a href="https://example.com/docs">公式ドキュメント</a>
    ↓
API経由で記事に保存
```

## 関連情報

- [埋め込み機能](embed.md) - 対応サービスのURL埋め込み
- [記事操作](../guide/articles.md) - Markdown記法一覧
