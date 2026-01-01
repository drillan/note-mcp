# 埋め込み機能

note-mcpでは、MarkdownにURLを記述することで外部コンテンツを埋め込みできます。

## 基本的な使い方

### 外部記事の埋め込み

URLを単独の行に記述すると、外部記事として埋め込まれます。

```markdown
# 参考記事まとめ

今回参考にした記事を紹介します。

https://example.com/interesting-article

上記の記事では...
```

URLの前後には空行を入れることを推奨します。

### 埋め込み結果

外部URLは自動的にnote.comの埋め込みウィジェットに変換されます。埋め込みにはリンク先のタイトル、説明文、サムネイル画像が表示されます。

## 対応フォーマット

### 単独URLパターン

URLが行の唯一のコンテンツである場合に埋め込みが有効になります。

```markdown
https://example.com/article
```

以下のパターンでは埋め込みに**変換されません**:

```markdown
<!-- リンクテキストがある場合 -->
[記事を読む](https://example.com/article)

<!-- 文中のURL -->
詳しくは https://example.com/article を参照してください。

<!-- インラインで他のテキストがある場合 -->
参考: https://example.com/article
```

## 使用例

### 技術記事での参考リンク

```markdown
# Pythonの最新機能

## 関連記事

公式ドキュメントの解説記事です。

https://docs.python.org/ja/3/whatsnew/

日本語の入門記事も参考になります。

https://example.com/python-guide
```

### ブログでの引用

```markdown
# 今週読んだ記事

## テクノロジー

AIに関する興味深い記事がありました。

https://example.com/ai-article

著者の視点が新鮮でした。
```

## 制限事項

- 埋め込みが表示されるのはnote.comのプレビュー画面以降です
- リンク先のサーバーがOGP（Open Graph Protocol）に対応していない場合、タイトルや説明が正しく取得されない場合があります
- 一部の外部サイトでは埋め込みがブロックされる場合があります

## 他の機能との組み合わせ

埋め込みは他のMarkdown機能と組み合わせて使用できます。

```markdown
# 技術ノート

[TOC]

## はじめに

この記事では $${E = mc^2}$$ について解説します。

## 参考資料

以下の記事を参考にしています。

https://example.com/physics-basics

## まとめ

物理学は面白い。
```

目次、数式、ルビなどと併用しても正しく処理されます。
