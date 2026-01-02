---
title: note-mcp サンプル記事
tags:
  - note-mcp
  - サンプル
  - Markdown
---

この記事は `note_create_from_file` MCPツールの機能をテストするためのサンプルです。

[TOC]

## はじめに

note-mcpを使うと、ローカルのMarkdownファイルからnote.comの記事を作成できます。

### 主な機能

- **YAMLフロントマター**からタイトルとタグを抽出
- **ローカル画像**を自動アップロード
- **目次（TOC）**の自動挿入
- **Markdown記法**をnote.com形式に変換

## テキスト装飾

基本的なテキスト装飾をテストします：

- **太字テキスト** - 強調したい部分に使用
- *イタリック* - 控えめな強調に使用
- ~~取り消し線~~ - 訂正や削除を示す
- `インラインコード` - コードやコマンドを示す

## リスト

### 箇条書きリスト

- 項目1
- 項目2
  - ネストした項目2-1
  - ネストした項目2-2
- 項目3

### 番号付きリスト

1. 最初のステップ
2. 次のステップ
3. 最後のステップ

## 引用

> これは引用ブロックです。
> 複数行にわたることもできます。
>
> — 出典: サンプルドキュメント

## コードブロック

Pythonのコード例：

```python
from note_mcp.utils.file_parser import parse_markdown_file

# Markdownファイルを解析
article = parse_markdown_file("sample_article.md")
print(f"タイトル: {article.title}")
print(f"タグ: {article.tags}")
```

## 画像

ローカル画像（自動アップロードされます）：

![サンプル画像](./images/sample_image.png)

## リンク

- [note.com公式サイト](https://note.com)
- [GitHub - note-mcp](https://github.com/example/note-mcp)

## 水平線

セクション間の区切り：

---

## 表

| 機能 | サポート | 備考 |
|------|----------|------|
| フロントマター | ✅ | title, tags |
| 画像アップロード | ✅ | ローカルファイル |
| TOC挿入 | ✅ | ブラウザ経由 |
| コードブロック | ✅ | シンタックスハイライト |

## まとめ

このサンプルファイルで以下の機能をテストできます：

1. YAMLフロントマターからのメタデータ抽出
2. 各種Markdown記法の変換
3. ローカル画像の自動アップロード
4. 目次の自動挿入

---

*このサンプルは note-mcp の動作確認用です。*
