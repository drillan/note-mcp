# Investigatorツールリファレンス

note-mcpのInvestigatorモードが提供する11のMCPツールのリファレンスです。

## 概要

InvestigatorツールはAIエージェントによるnote.com APIの調査を支援します。mitmproxyとPlaywrightを使用してHTTPトラフィックをキャプチャ・分析します。

### 有効化

Investigatorモードを有効にするには、環境変数を設定します：

```bash
export INVESTIGATOR_MODE=1
```

### 用途

- 未ドキュメントのAPIエンドポイント調査
- リクエスト/レスポンスパターンの分析
- 新機能実装前のAPI動作確認

---

## セッション管理ツール

### investigator_start_capture

キャプチャセッションを開始します。

```
api.note.comドメインのトラフィックキャプチャを開始してください
```

**パラメータ**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|------------|------|
| `domain` | str | はい | - | キャプチャ対象ドメイン（例: api.note.com） |
| `port` | int | いいえ | 8080 | プロキシポート |

**動作**

1. mitmproxyをバックグラウンドで起動
2. Playwrightブラウザをプロキシ経由で起動
3. 指定ドメインへのHTTPトラフィックをキャプチャ開始

**戻り値**

```
Capture session started for domain: api.note.com, port: 8080
```

---

### investigator_stop_capture

キャプチャセッションを停止します。

```
キャプチャセッションを停止してください
```

**パラメータ**

なし

**動作**

1. ブラウザを閉じる
2. プロキシを停止
3. キャプチャデータをメモリに保持

**戻り値**

```
Capture session stopped
```

---

### investigator_get_status

現在のキャプチャセッション状態を取得します。

```
キャプチャセッションの状態を確認してください
```

**パラメータ**

なし

**戻り値**

```json
{
  "active": true,
  "domain": "api.note.com",
  "port": 8080,
  "captured_requests": 42
}
```

---

## ブラウザ操作ツール

### investigator_navigate

指定URLに移動します。

```
https://note.com に移動してください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `url` | str | はい | 移動先URL |

**動作**

ブラウザを指定URLに移動させます。トラフィックは自動的にキャプチャされます。

**戻り値**

```
Navigated to: note｜つくる、つながる、とどける。
```

---

### investigator_click

セレクタで指定した要素をクリックします。

```
button.login-btn をクリックしてください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `selector` | str | はい | CSSセレクタ |

**動作**

CSSセレクタを使用してページ上の要素を特定し、クリックします。クリックにより発生するHTTPリクエストはキャプチャされます。

**戻り値**

```
Clicked: button.login-btn
```

---

### investigator_type

指定要素にテキストを入力します。

```
input[name="email"] に test@example.com を入力してください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `selector` | str | はい | CSSセレクタ |
| `text` | str | はい | 入力テキスト |

**戻り値**

```
Typed text into: input[name="email"]
```

---

### investigator_screenshot

現在のページのスクリーンショットを取得します。

```
現在のページのスクリーンショットを取得してください
```

**パラメータ**

なし

**戻り値**

base64エンコードされたPNG画像データを返します。

---

### investigator_get_page_content

現在のページのHTMLを取得します。

```
現在のページのHTMLを取得してください
```

**パラメータ**

なし

**戻り値**

ページの完全なHTMLソースを返します。

---

## トラフィック分析ツール

### investigator_get_traffic

キャプチャしたトラフィック一覧を取得します。

```
キャプチャしたトラフィックを表示してください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `pattern` | str | いいえ | URLパターンでフィルタ（正規表現） |

**戻り値**

```json
[
  {
    "method": "GET",
    "url": "https://api.note.com/v3/notes/123",
    "status": 200,
    "content_type": "application/json"
  },
  {
    "method": "POST",
    "url": "https://api.note.com/v3/notes",
    "status": 201,
    "content_type": "application/json"
  }
]
```

---

### investigator_analyze

特定パターンのトラフィックを詳細分析します。

```
/v3/notes パターンのトラフィックを分析してください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `pattern` | str | はい | URLパターン（正規表現） |
| `method` | str | いいえ | HTTPメソッドでフィルタ |

**戻り値**

```
Traffic Analysis for pattern: /v3/notes

Total requests: 15
Methods:
  - GET: 10
  - POST: 3
  - PUT: 2

Status codes:
  - 200: 12
  - 201: 2
  - 400: 1

Response times (avg): 245ms
```

---

### investigator_export

キャプチャデータをJSONファイルにエクスポートします。

```
トラフィックを /tmp/capture.json にエクスポートしてください
```

**パラメータ**

| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `output_path` | str | はい | 出力ファイルパス |

**戻り値**

```
Exported 42 requests to /tmp/capture.json
```

---

## 典型的なワークフロー

### APIエンドポイント調査

1. セッション開始：
   ```
   api.note.comのキャプチャを開始してください
   ```

2. 認証（必要な場合）：
   ```
   note_loginでログインしてください
   ```

3. 対象ページに移動：
   ```
   https://note.com/your_username/n/n1234567890ab に移動してください
   ```

4. 操作を実行：
   ```
   button.like-btn をクリックしてください
   ```

5. トラフィックを分析：
   ```
   /v3/notes パターンのトラフィックを分析してください
   ```

6. 結果をエクスポート：
   ```
   トラフィックを ./api_investigation.json にエクスポートしてください
   ```

7. セッション停止：
   ```
   キャプチャを停止してください
   ```

## エラーレスポンス

セッションが開始されていない場合：

```
Error: No active capture session. Start one first.
```

タイムアウトが発生した場合：

```
Error: Navigation to https://... timed out.
```

## Docker環境での使用

Docker環境では、investigatorモードは専用のDocker Compose設定で起動します：

```bash
cd docker
docker compose up --build
```

詳細は[開発ガイド](../development/contributing.md)を参照してください。
