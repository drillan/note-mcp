# トラブルシューティング

note-mcpで発生する可能性のある問題と解決方法を説明します。

## 認証関連

### セッションが無効です

**症状**:
```
セッションが無効です。note_loginでログインしてください。
```

**原因**:
- 認証Cookieの期限切れ
- セッション情報が保存されていない

**解決方法**:
```
note_loginを実行してください
```

### ログインがタイムアウトする

**症状**:
```
ログインがタイムアウトしました。
```

**原因**:
- 5分以内にログイン操作が完了しなかった

**解決方法**:
```
# タイムアウトを延長してログイン
note_login(timeout=600)
```

### ユーザー名が取得できない

**症状**:
```
ユーザー名を取得できませんでした。note_set_usernameで手動設定してください。
```

**原因**:
- ログイン後のリダイレクト処理中にユーザー名を取得できなかった

**解決方法**:
```
note_set_username("your_username")
```

ユーザー名はnote.comのプロフィールURL（`https://note.com/your_username`）から確認できます。

## ブラウザ関連

### ブラウザが起動しない

**症状**:
```
Executable doesn't exist at /path/to/chromium
```

**原因**:
- Playwrightのブラウザがインストールされていない

**解決方法**:
```bash
uv run playwright install chromium
```

Linux環境では追加の依存ライブラリが必要な場合があります：

```bash
uv run playwright install-deps chromium
```

### タイムアウトエラー

**症状**:
```
Timeout 30000ms exceeded.
```

**原因**:
- ネットワーク遅延
- ページの読み込みが遅い
- 要素が見つからない

**解決方法**:
- 安定したネットワーク環境で再試行
- 再度同じ操作を実行

### Headlessモードで問題が発生する

**症状**:
- 一部の操作が失敗する
- 予期しないエラーが発生する

**原因**:
- headlessモードとheadedモードで動作が異なる場合がある

**解決方法**:
```bash
# headedモードに切り替え
unset NOTE_MCP_HEADLESS
# または
export NOTE_MCP_HEADLESS=false
```

## API関連

### 記事の取得に失敗

**症状**:
```
記事の取得に失敗しました: 404 Not Found
```

**原因**:
- 記事IDが間違っている
- 記事が削除された
- アクセス権限がない

**解決方法**:
```
# 記事一覧で正しいIDを確認
note_list_articles(status="all")
```

### 画像アップロードに失敗

**症状**:
```
File not found: /path/to/image.jpg
```

**原因**:
- ファイルパスが間違っている
- ファイルが存在しない

**解決方法**:
- 絶対パスを使用
- ファイルの存在を確認

**症状**:
```
Invalid file format: .bmp
```

**原因**:
- サポートされていない画像形式

**解決方法**:
- JPEG、PNG、GIF、WebP形式に変換

**症状**:
```
File size exceeds maximum allowed size (10485760 bytes)
```

**原因**:
- ファイルサイズが10MBを超えている

**解決方法**:
- 画像を圧縮して10MB以下にする

## 環境関連

### Docker環境でkeyringエラー

**症状**:
```
keyring.errors.NoKeyringError: No recommended backend was available.
```

**原因**:
- Docker環境ではOSのキーリングが利用できない

**解決方法**:
```bash
# ファイルベースセッションを使用
export USE_FILE_SESSION=1
```

### Investigatorモードが有効にならない

**症状**:
- investigator_* ツールが表示されない

**原因**:
- 環境変数が設定されていない

**解決方法**:
```bash
export INVESTIGATOR_MODE=1
```

### ポートが使用中

**症状**:
```
Address already in use: 8080
```

**原因**:
- mitmproxyのポートが既に使用されている

**解決方法**:
```
# 別のポートを指定
investigator_start_capture(domain="api.note.com", port=8081)
```

## ログの確認

問題が解決しない場合、ログを確認してください：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

または環境変数で設定：

```bash
export LOG_LEVEL=DEBUG
```

## 問題の報告

解決できない問題がある場合は、GitHubのIssueで報告してください：

1. 発生した問題の説明
2. 再現手順
3. エラーメッセージ（全文）
4. 環境情報（OS、Pythonバージョン）
