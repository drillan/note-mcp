# リンク機能

note.comのProseMirrorエディタへリンクを挿入する機能です。

## 概要

note.comのエディタはMarkdown記法 `[text](url)` を自動変換しません（InputRuleが未実装）。
このため、リンク挿入はUI経由のブラウザ自動化で実現しています。

## 使用方法

### 基本的なリンク挿入

記事本文にリンクを含むMarkdownを記述すると、UI経由で自動的にリンクが挿入されます。

```markdown
詳細は[公式ドキュメント](https://example.com/docs)を参照してください。
```

### 技術的な動作

内部では `insert_link_at_cursor()` 関数がUI操作を行います：

1. テキストを入力
2. テキストを選択（Shift+Left × 文字数）
3. リンクダイアログを開く（Ctrl+K）
4. URLを入力
5. Enterキーで適用
6. 挿入完了を検証

## 結果タイプ

リンク挿入の結果は `LinkResult` enumで表されます：

| 値 | 説明 |
|----|------|
| `SUCCESS` | リンクが正常に挿入された |
| `TIMEOUT` | タイムアウト（予期しない失敗） |

## 制約事項

### ProseMirror制約

note.comのエディタには以下の制約があります：

- Markdown `[text](url)` はInputRuleで変換されない
- `link` markはスキーマに存在するが、自動変換ルールがない
- 他の書式（`**bold**`、`~~strikethrough~~`）は正常に変換される

### 対応策

この制約を回避するため、リンク挿入はブラウザUI経由で行います。
これは埋め込み機能（`insert_embed_at_cursor()`）と同じパターンです。

## 関連情報

- [埋め込み機能](embed.md) - 同様のUI自動化パターン
- [記事操作](../guide/articles.md) - Markdown記法一覧
