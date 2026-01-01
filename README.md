# note-mcp

note.com記事管理用MCPサーバー。AIアシスタント（Claude Code, Claude Desktop等）から直接note.comの記事を作成・編集・公開できます。

⚠️ **注意**: このプロジェクトはnote.comの非公式APIを使用しています。詳細は[DISCLAIMER.md](DISCLAIMER.md)を参照してください。

## Features

- 🔐 **ブラウザ認証**: Playwrightでnote.comにログインし、セッションを安全に保存
- 📝 **記事作成**: Markdownで記事を作成し、下書きとして保存
- 📖 **記事取得**: 既存記事の内容（タイトル、本文、タグ等）を取得
- ✏️ **記事編集**: 既存記事の更新（取得→編集→保存のワークフロー）
- 🚀 **記事公開**: 下書きから公開へのワンステップ変更
- 🖼️ **画像アップロード**: アイキャッチ画像・記事内埋め込み画像のアップロード
  - アイキャッチ画像: 記事のサムネイル用
  - 本文用画像: S3直接アップロードでアイキャッチに影響なし
- 📋 **記事一覧**: 自分の記事一覧の取得
- 🔄 **Markdown→HTML変換**: 自動的にnote.com互換のHTML形式に変換
- 📐 **数式サポート**: KaTeX互換の数式記法（`$${...}$$`）に対応
- 📑 **目次サポート**: `[TOC]`記法で見出しから目次を自動生成

## Installation

```bash
# Install from GitHub
uv pip install git+https://github.com/drillan/note-mcp.git

# Install Playwright browser
playwright install chromium
```

### 開発用インストール

```bash
# Clone the repository
git clone https://github.com/drillan/note-mcp.git
cd note-mcp

# Install dependencies
uv sync

# Install Playwright browser
uv run playwright install chromium
```

## Configuration

### Claude Desktop

`~/.config/claude-desktop/config.json`（macOS/Linux）または `%APPDATA%\claude-desktop\config.json`（Windows）に以下を追加:

```json
{
  "mcpServers": {
    "note-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "note_mcp"],
      "cwd": "/path/to/note-mcp"
    }
  }
}
```

## Usage

### 1. ログイン

```
note.comにログインしてください
```

ブラウザが起動し、note.comのログインページが表示されます。手動でログインを完了すると、セッションがOSのキーチェーンに安全に保存されます。

### 2. 記事作成

```
以下の内容でnote.comに下書きを作成してください:

タイトル: AIと記事を書く
本文:
# はじめに
AIアシスタントと一緒に記事を書いてみましょう。
```

### 3. 画像アップロード

#### アイキャッチ（見出し）画像

```
記事ID 12345678 に /path/to/eyecatch.png をアイキャッチ画像としてアップロードしてください
```

アイキャッチ画像は記事のサムネイルとして表示されます。

#### 記事内埋め込み画像

```
記事ID 12345678 に /path/to/inline.png を本文用画像としてアップロードし、記事に埋め込んでください
```

本文用画像をアップロードすると、Markdown形式の挿入コードが返されます。これを記事本文に追加することで画像を埋め込めます。

**キャプション付き画像**:

画像にキャプション（説明文）を追加するには、Markdownのtitle属性を使用します:

```markdown
![代替テキスト](画像URL "キャプションテキスト")
```

例:
```markdown
![スクリーンショット](https://example.com/image.png "図1: システム構成図")
```

キャプションはnote.comのエディタで画像の下に表示されます。

> **Note**: 本文用画像はS3への直接アップロードを使用するため、アイキャッチ画像には影響しません。

### 4. 引用と出典

引用ブロックに出典（引用元）を追加できます。Markdownの引用記法で、`— `（emダッシュ + スペース）で始まる行を出典として認識します。

**基本的な出典**:

```markdown
> 知識は力なり
> — フランシス・ベーコン
```

**出典にURLを追加**:

```markdown
> 知識は力なり
> — フランシス・ベーコン (https://ja.wikipedia.org/wiki/知識は力なり)
```

出典のURLはリンクとして変換されます。出典行がない場合は、従来通り引用のみが表示されます。

> **Tip**: 複数行の引用も対応しています。出典は引用ブロックの最後の行に記述してください。

### 5. 記事編集（推奨ワークフロー）

既存記事を編集する際は、まず内容を取得してから編集を行います:

```
記事ID ne1c111d2073c の内容を取得してください
```

取得した内容を確認後、編集を依頼:

```
取得した記事の末尾に「まとめ」セクションを追加してください
```

AIが既存内容を把握した上で適切に編集を行います。

### 6. 記事公開

```
下書きを公開してください
```

### 7. 数式の使用

note.comの数式記法をMarkdownで使用できます。

**インライン数式**（文中に埋め込む）:

```markdown
ピタゴラスの定理は $${a^2 + b^2 = c^2}$$ で表されます。
```

**ディスプレイ数式**（独立した行に表示）:

```markdown
二次方程式の解の公式：

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$
```

> **Note**: 数式はKaTeX記法に準拠しています。詳細は[数式機能ドキュメント](docs/features/math.md)を参照してください。

### 8. 目次の挿入

記事内に目次を自動生成できます。

```markdown
# 記事タイトル

[TOC]

## はじめに
導入文...

## 本論
メインコンテンツ...

### サブセクション
詳細...

## まとめ
結論...
```

`[TOC]`と記述した位置に、見出し（H2・H3）から自動生成された目次が挿入されます。

> **Note**: 詳細は[目次機能ドキュメント](docs/features/toc.md)を参照してください。

## MCP Tools

| Tool | Description |
|------|-------------|
| `note_login` | ブラウザでnote.comにログイン |
| `note_check_auth` | 認証状態を確認 |
| `note_logout` | ログアウト（セッション削除） |
| `note_set_username` | ユーザー名を設定（セッション復元時に必要） |
| `note_create_draft` | 下書き記事を作成 |
| `note_get_article` | 記事内容を取得（タイトル、本文、タグ、ステータス等） |
| `note_update_article` | 記事を更新（先にnote_get_articleで内容取得を推奨） |
| `note_publish_article` | 記事を公開 |
| `note_list_articles` | 記事一覧を取得 |
| `note_upload_eyecatch` | アイキャッチ（見出し）画像をアップロード |
| `note_upload_body_image` | 記事本文用の埋め込み画像をアップロード |
| `note_show_preview` | ブラウザで記事プレビューを表示 |

## Security

### 認証情報の保存

セッション情報（Cookie、ユーザーID等）はOSのセキュアストレージに暗号化して保存されます：

| OS | 保存先 |
|----|--------|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | GNOME Keyring / libsecret |

保存される情報：
- 認証Cookie（`_note_session_v5`等）
- ユーザーID・ユーザー名
- セッション作成日時

### セキュリティ特性

- **OS暗号化**: 各OSのネイティブ暗号化機能を使用
- **ユーザー分離**: ログインユーザーのみがアクセス可能
- **自動管理**: `note_login`で保存、`note_logout`で削除

### Linux での追加設定

Linuxでは以下のいずれかが必要です：

```bash
# Ubuntu/Debian
sudo apt install gnome-keyring

# または
sudo apt install libsecret-1-0
```

## Requirements

- Python 3.11+
- デスクトップ環境（Playwrightが動作する環境）
- note.comアカウント

## Docker

Dockerを使用してPlaywright環境を構築できます。複数の実行モードをサポートしています。

### ビルド

```bash
docker build -t note-mcp .
```

### 実行モード

#### 1. Headless（デフォルト）

CI/CD環境やバックグラウンド実行向け:

```bash
# docker-compose使用
docker compose run --rm test

# 直接実行
docker run --rm --ipc=host note-mcp uv run pytest -v
```

#### 2. Headed with Xvfb

Xvfbを使用したheadedモード（仮想ディスプレイ上でブラウザを起動）:

```bash
docker compose run --rm test-headed

# 直接実行
docker run --rm --ipc=host -e USE_XVFB=1 -e HEADED=1 note-mcp uv run pytest -v
```

> **Note**: `HEADED=1`環境変数を使用するには、テストコード内で`os.environ.get("HEADED")`をチェックしてブラウザの`headless`オプションを制御する必要があります。

#### 3. VNC経由での視覚確認

VNCクライアントまたはWebブラウザでブラウザ操作をリアルタイム確認:

```bash
# バックグラウンドで起動
docker compose up -d test-vnc

# 方法1: noVNC（Webブラウザ経由、クリップボード共有対応）
# ブラウザで http://localhost:6080/vnc.html にアクセス

# 方法2: VNCクライアント
vncviewer localhost:5900

# ログ確認（必要な場合）
docker compose logs -f test-vnc

# 終了時
docker compose down
```

> **Tip**: noVNCを使用すると、左側のクリップボードパネルからホストとコンテナ間でテキストをコピー＆ペーストできます。

#### 4. X11 forwarding（Linux/WSL2）

ホストのディスプレイに直接表示:

```bash
# X11アクセスを許可（必要な場合）
xhost +local:docker

# 実行
docker compose run --rm test-x11

# または直接
docker run --rm --ipc=host \
  -e DISPLAY=$DISPLAY \
  -e HEADED=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  note-mcp uv run pytest -v
```

### 開発用シェル

コンテナ内でインタラクティブに作業:

```bash
# VNCなしで実行（ポートマッピングなし）
docker compose run --rm dev bash

# VNC経由でブラウザを確認する場合（ポートマッピングあり）
docker compose run --rm --service-ports dev bash
```

> **Note**: `docker compose run`はデフォルトでポートマッピングを行いません。VNC（ポート5900）やnoVNC（ポート6080）にアクセスする場合は`--service-ports`フラグが必要です。

コンテナ内でブラウザを開くには:

```bash
# コンテナ内で実行
uv run python scripts/open_browser.py https://note.com --wait 120
```

ブラウザを確認するには:
- **noVNC（推奨）**: http://localhost:6080/vnc.html にアクセス（クリップボード共有対応）
- **VNCクライアント**: `vncviewer localhost:5900` で接続

### Claude Code + Chrome拡張機能

Docker開発環境にはClaude Codeがプリインストールされています。noVNC経由でClaude in Chrome拡張機能を使用できます。

#### 初回セットアップ

```bash
# 開発コンテナを起動
docker compose run --rm --service-ports dev bash

# コンテナ内でChromeを起動（--no-sandboxは必須）
google-chrome-stable --no-sandbox &
```

noVNC（http://localhost:6080/vnc.html）またはVNCクライアント（`vncviewer localhost:5900`）で接続し、以下の手順で拡張機能をインストール:

1. Chrome Web Storeにアクセス: https://chromewebstore.google.com/detail/claude/danfoghgkjjpomlapfijehgjhbhnphnf
2. 「Chromeに追加」をクリック
3. 拡張機能を有効化

#### Chrome拡張機能の永続化

Chrome拡張機能と設定はDockerボリューム（`chrome-data`）に永続化されます。コンテナを再作成しても拡張機能は保持されます。

```bash
# ボリュームの確認
docker volume ls | grep chrome-data

# ボリュームの削除（設定をリセットする場合）
docker volume rm note-mcp_chrome-data
```

#### Claude Codeの使用

```bash
# コンテナ内で
claude --version  # バージョン確認
claude            # Claude Code起動
```

### 環境変数

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `USE_XVFB` | Xvfbを起動 (`1` or `true`) | `0` |
| `VNC_PORT` | VNCサーバーポート（TigerVNC） | (無効) |
| `NOVNC_PORT` | noVNC Webアクセスポート | `6080` |
| `DISPLAY` | X11ディスプレイ | `:99` |
| `XVFB_WHD` | Xvfb解像度 | `1920x1080x24` |
| `CHROME_FLAGS` | Chrome起動オプション | `--no-sandbox` (dev) |

> **Note**: `VNC_PORT`を設定するとTigerVNCが起動し、noVNCも自動的に有効になります。クリップボード共有はnoVNC経由で利用できます。

### トラブルシューティング

**Chromiumがクラッシュする場合**:
- `--ipc=host` フラグを追加（docker-composeでは設定済み）
- 共有メモリ不足が原因の可能性があります

**Chromeが「Operation not permitted」で起動しない場合**:
- `google-chrome-stable --no-sandbox &` で起動してください
- Docker内ではChromeのサンドボックス機能が制限されます

**`claude`コマンドが見つからない場合**:
- PATHが正しく設定されているか確認: `echo $PATH`
- `/home/ubuntu/.local/bin` がPATHに含まれているべきです

**X11接続エラー**:
- `xhost +local:docker` を実行
- WSL2の場合は`/mnt/wslg/`ディレクトリの存在を確認

**VNCに接続できない場合**:
- ポート5900（VNC）または6080（noVNC）が他のプロセスで使用されていないか確認
- `docker compose logs test-vnc` でログを確認
- noVNCの場合、ブラウザで http://localhost:6080/vnc.html にアクセス

**クリップボード共有が動作しない場合**:
- noVNC（http://localhost:6080/vnc.html）を使用してください
- VNCクライアント経由ではクリップボード共有は利用できません
- noVNCの左側パネルでクリップボードアイコンをクリック

**「Server is already active for display 99」エラー**:
- 前回のコンテナが残っています
- `docker compose down` を実行してから再度起動してください

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run E2E tests
uv run pytest tests/e2e/ -v

# Run linter
uv run ruff check .

# Run type checker
uv run mypy .
```

E2Eテストの詳細は[テストガイド](docs/development/testing.md)を参照してください。

## License

MIT License

## Disclaimer

このプロジェクトはnote.comとは無関係の非公式ツールです。詳細は[DISCLAIMER.md](DISCLAIMER.md)を参照してください。
