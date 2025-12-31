# ブラウザ自動化

note-mcpはPlaywrightを使用したブラウザ自動化により、note.comのWeb UIを操作します。

## 概要

一部の機能（ログイン、画像挿入、下書き作成）はAPIだけでは実現できないため、Chromiumブラウザを自動操作します。

### ブラウザ自動化が必要な機能

| 機能 | 理由 |
|------|------|
| ログイン | 認証Cookieの取得 |
| 下書き作成 | ProseMirrorエディタへの入力 |
| 画像挿入 | エディタの「画像を追加」機能 |
| プレビュー表示 | 記事のブラウザ表示 |

## Playwrightセットアップ

### インストール

```bash
# パッケージインストール後、Chromiumをインストール
uv sync
uv run playwright install chromium
```

依存ブラウザがインストールされていない場合、ブラウザ操作で以下のエラーが発生します：

```
Executable doesn't exist at /path/to/chromium
```

### システム依存関係（Linux）

Linuxでは追加のシステムライブラリが必要な場合があります：

```bash
# 依存ライブラリを自動インストール
uv run playwright install-deps chromium
```

## 表示モード

### Headed（デフォルト）

デフォルトでは、ブラウザウィンドウが表示されます。ログイン操作やデバッグに便利です。

### Headless

ヘッドレスモードでは、ブラウザウィンドウを表示せずにバックグラウンドで操作します。

```bash
export NOTE_MCP_HEADLESS=true
```

**注意**: ログイン操作ではユーザーが手動でログイン情報を入力する必要があるため、headedモードが推奨されます。

## ブラウザ管理

### シングルトンパターン

BrowserManagerはシングルトンとして実装されており、複数の操作間でブラウザインスタンスを再利用します。

- **ページ再利用**: 同じページを複数の操作で使用
- **自動クリーンアップ**: プロセス終了時に自動でブラウザを閉じる
- **スレッドセーフ**: asyncio.Lockで同時アクセスを制御

### リソース管理

ブラウザは以下の階層で管理されます：

```
Playwright
└── Browser (Chromium)
    └── BrowserContext
        └── Page
```

各レベルで適切なリソース解放が行われます。

## 操作別の動作

### ログイン

1. note.comのログインページを開く
2. ユーザーがログイン情報を入力（手動）
3. 認証Cookie取得を待機（最大5分）
4. Cookieをセキュアストレージに保存
5. ブラウザを閉じる

### 下書き作成

1. note.comの新規記事作成ページを開く
2. タイトルを入力
3. 本文をMarkdown形式で入力
4. ProseMirrorがMarkdownをHTMLに変換
5. タグを追加（指定時）
6. 下書きを保存
7. ブラウザを閉じる

### 画像挿入

1. 記事の編集ページを開く
2. エディタ末尾に移動
3. 「画像を追加」ボタンをクリック
4. ファイル選択ダイアログで画像を選択
5. キャプションを入力（指定時）
6. 保存を確認
7. ブラウザを閉じる

### プレビュー表示

1. 記事のプレビューURLを生成
2. ブラウザでプレビューページを開く
3. ユーザーが確認（ブラウザは開いたまま）

## トラブルシューティング

### ブラウザが起動しない

```bash
# Chromiumを再インストール
uv run playwright install chromium

# 依存ライブラリを確認（Linux）
uv run playwright install-deps chromium
```

### タイムアウトエラー

ネットワーク遅延や重いページの場合、タイムアウトが発生することがあります。

- 安定したネットワーク環境で再試行
- ページの読み込み完了を待機

### セッション切れ

ブラウザ操作中にセッションが切れた場合：

1. `note_login`で再ログイン
2. 操作を再試行

### Headlessモードでの問題

一部の操作はheadlessモードで問題が発生する場合があります：

```bash
# headedモードに切り替え
unset NOTE_MCP_HEADLESS
# または
export NOTE_MCP_HEADLESS=false
```

## Docker環境

Docker環境ではheadlessモードを使用し、追加設定が必要です：

```yaml
# docker-compose.yml
services:
  note-mcp:
    environment:
      - NOTE_MCP_HEADLESS=true
      - USE_FILE_SESSION=1
```

詳細は[開発ガイド](../development/contributing.md)を参照してください。
