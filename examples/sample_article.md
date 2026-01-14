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
- ~~取り消し線~~ - 訂正や削除を示す

## ルビ（ふりがな）

note.com独自のルビ記法を使用できます：

- ｜漢字《かんじ》のテスト
- ｜東京《とうきょう》は｜日本《にほん》の｜首都《しゅと》です

ルビ記法はそのままAPIに送信され、フロントエンドで`<ruby>`タグに変換されます。

> **注意**: 太字（`**...**`）内にルビ記法を含めると正しく変換されません（Issue #169）

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

## 埋め込み

対応サービスのURLを単独の行に記述すると、埋め込みウィジェットに変換されます。

### YouTube埋め込み

https://www.youtube.com/watch?v=NMHcEDcympM

### Twitter/X埋め込み

https://x.com/patraqushe/status/1326880858007990275

### note.com記事埋め込み

https://note.com/drillan/n/n7379c02632c9

### GitHub Gist埋め込み

https://gist.github.com/drillan/71aab0a37b413be66bedf6c011d7cd37

## 水平線

セクション間の区切り：

---

## テキスト配置

テキストの配置を変更できます：

->中央寄せのテキスト<-

->右寄せのテキスト

<-左寄せのテキスト

## 数式

KaTeX記法で数式を記述できます：

インライン数式：円の面積は$${A = \pi r^2}$$で計算します。

ディスプレイ数式（独立した行）：

$${E = mc^2}$$

複雑な数式も記述できます：

$${\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}}$$

## まとめ

このサンプルファイルで以下の機能をテストできます：

1. YAMLフロントマターからのメタデータ抽出
2. 各種Markdown記法の変換
3. ローカル画像の自動アップロード
4. 目次の自動挿入
5. テキスト配置（中央・右・左寄せ）
6. 数式（KaTeX）記法
7. ルビ（ふりがな）記法
8. 埋め込み（YouTube、Twitter/X、note.com記事、GitHub Gist）

---

このサンプルは note-mcp の動作確認用です。
