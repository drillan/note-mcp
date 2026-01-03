# 認証

note-mcpはnote.comへの認証をブラウザ経由で行い、セッション情報をOSのセキュアストレージに保存します。

## 認証フロー

### 手動ログイン

`note_login`ツールを使用してログインします：

```
note.comにログインしてください
```

1. Chromiumブラウザが起動し、note.comのログインページが表示されます
2. 手動でログイン情報を入力します（メールアドレス/パスワード、またはソーシャルログイン）
3. ログイン完了後、セッション情報が自動的に保存されます
4. ブラウザは自動的に閉じられます

タイムアウトはデフォルトで300秒（5分）です。

### 自動ログイン（E2Eテスト用）

E2Eテストやスクリプト実行時に、環境変数から認証情報を読み込んで自動ログインを行います：

```python
from note_mcp.auth.browser import login_with_browser

# 認証情報を指定して自動ログイン
session = await login_with_browser(
    credentials=("username", "password")
)
```

環境変数から認証情報を設定する場合：

```bash
export NOTE_USERNAME=your_username
export NOTE_PASSWORD=your_password
```

**注意**: 自動ログイン中にreCAPTCHAや二段階認証（2FA）が検出された場合、`LoginError`例外が発生します。この場合は手動でログインし、セッションを保存してください。

#### LoginError例外

自動ログイン時に以下の状況で`LoginError`例外が発生します：

| エラーコード | 説明 | 対処法 |
|-------------|------|--------|
| `RECAPTCHA_DETECTED` | reCAPTCHAが検出された | 手動でログインしセッションを保存 |
| `TWO_FACTOR_REQUIRED` | 二段階認証が要求された | 手動でログインしセッションを保存 |
| `INVALID_CREDENTIALS` | 認証情報が無効 | ユーザー名とパスワードを確認 |
| `LOGIN_TIMEOUT` | ログインがタイムアウト | 認証情報を確認するか、手動でログイン |
| `FORM_NOT_FOUND` | ログインフォームが見つからない | ページの読み込み状態を確認 |

```python
from note_mcp.models import LoginError

try:
    session = await login_with_browser(credentials=("user", "pass"))
except LoginError as e:
    print(f"ログイン失敗: {e.code}")
    print(f"対処法: {e.resolution}")
```

### 認証状態の確認

`note_check_auth`ツールで現在の認証状態を確認できます：

```
認証状態を確認してください
```

レスポンス例：
- 認証済み: `認証済みです（ユーザー: your_username）`
- 未認証: `未認証です。note_loginを使用してログインしてください`

### ログアウト

`note_logout`ツールでセッションを削除できます：

```
ログアウトしてください
```

保存されているセッション情報がすべて削除されます。

## セッション管理

### セキュアストレージ

セッション情報は各OSのネイティブセキュアストレージに暗号化して保存されます：

| OS | 保存先 |
|----|--------|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | GNOME Keyring / libsecret |

### 保存される情報

- 認証Cookie（`_note_session_v5`など）
- ユーザーID
- ユーザー名
- セッション作成日時

### Linuxでの設定

Linuxではkeyring backendが必要です：

```bash
# Ubuntu/Debian
sudo apt install gnome-keyring

# または
sudo apt install libsecret-1-0
```

### Docker/ヘッドレス環境

keyringが利用できない環境では、ファイルベースのセッション管理を使用します：

```bash
export USE_FILE_SESSION=1
```

セッションファイルは `~/.note-mcp/session.json` に保存されます。

## ユーザー名の設定

ログイン時にユーザー名の自動取得に失敗した場合、手動で設定できます：

```
ユーザー名を your_username に設定してください
```

ユーザー名はnote.comのプロフィールURLから確認できます：
`https://note.com/your_username` → `your_username`

## トラブルシューティング

### 認証が失敗する

1. **タイムアウト**: ログインに5分以上かかった場合、再度実行してください
2. **ブラウザが起動しない**: Playwrightのインストールを確認してください
   ```bash
   playwright install chromium
   ```
3. **Keyringエラー**: Linuxの場合、上記のkeyring backendをインストールしてください

### セッションが保存されない

1. Keyringのバックエンドを確認：
   ```python
   import keyring
   print(keyring.get_keyring())
   ```
2. バックエンドが`keyrings.alt.file.PlaintextKeyring`の場合、セキュアなバックエンドをインストールしてください

### 毎回ログインが必要

セッションの有効期限が切れている可能性があります。定期的に`note_login`で再認証してください。

## セキュリティ

- **OS暗号化**: 各OSのネイティブ暗号化機能を使用
- **ユーザー分離**: ログインユーザーのみがアクセス可能
- **自動管理**: `note_login`で保存、`note_logout`で削除
- **パスワード非保存**: パスワードはブラウザに直接入力され、保存されません
