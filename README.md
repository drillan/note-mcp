# Python Project Template

Python プロジェクトのテンプレートリポジトリです。

## 使い方

### 1. このテンプレートを使用

GitHub の "Use this template" ボタンをクリックして新しいリポジトリを作成します。

### 2. 初期化スクリプトを実行

```bash
./scripts/python-init.sh
```

このスクリプトは以下を自動的に実行します：

- `uv` による Python プロジェクトの初期化
- Python の `.gitignore` ファイルのダウンロード
- 開発ツールのインストール（ruff, mypy, pytest）
- Sphinx ドキュメント環境のセットアップ
  - Read the Docs テーマの適用
  - MyST Parser（Markdown サポート）の設定
  - Mermaid 図のサポート

### 3. プロジェクト設定

- プロジェクト名：現在のディレクトリ名が自動的に使用されます
- 著者名：Git の `user.name` が自動的に使用されます

## 含まれるツール

- **uv**: 高速な Python パッケージマネージャー
- **ruff**: 高速な Python リンター/フォーマッター
- **mypy**: 静的型チェッカー
- **pytest**: テストフレームワーク
- **Sphinx**: ドキュメント生成ツール
  - sphinx_rtd_theme: Read the Docs テーマ
  - myst-parser: Markdown サポート
  - sphinxcontrib-mermaid: Mermaid 図のサポート

## Claude Code サポート

このテンプレートは [Claude Code](https://claude.ai/code) との統合をサポートしています。

### CLAUDE.md

プロジェクト固有の開発ガイドラインを記載するファイルです。Claude Code がこのファイルを参照して、プロジェクトの開発環境や規約を理解します。

**含まれる情報:**
- 開発環境のセットアップ方法
- コード品質ツールの使用方法
- テスト実行方法
- 型安全性の要件
- コーディング規約
- ドキュメンテーション標準

**カスタマイズ方法:**
1. プレースホルダー（`<package-manager>`, `<linter>`等）を実際のツール名に置き換え
2. プロジェクト固有の開発ルールを追加
3. Technology Stack Summary セクションを実際の依存関係に更新

### .claude/ ディレクトリ

Claude Code 用の設定とスキルを含むディレクトリです。

#### .claude/docs.md

ドキュメンテーションの作成・管理ガイドラインを記載します。

**含まれる情報:**
- ドキュメンテーションシステムの設定
- マークアップ構文のガイドライン
- トーンとスタイルの規約
- コードブロックの記述方法
- ビルド検証の手順

**カスタマイズ方法:**
1. `{{PROJECT_NAME}}` をプロジェクト名に置き換え
2. 使用するドキュメンテーションシステムに応じて設定を調整
3. プロジェクト固有のドキュメント規約を追加

#### .claude/skills/doc-updater/

コード変更時にドキュメントを自動更新する Agent Skill です。

**機能:**
- API変更の検知とドキュメント更新
- 新機能追加時の自動ドキュメント生成提案
- アーキテクチャ変更の反映
- ドキュメントビルドエラーチェック

詳細は `.claude/skills/doc-updater/README.md` を参照してください。

### セットアップ手順

1. **CLAUDE.md のカスタマイズ:**
   ```bash
   # プレースホルダーを実際のツール名に置き換え
   # 例: <package-manager> → uv
   # 例: <linter> → ruff
   ```

2. **.claude/docs.md のカスタマイズ:**
   ```bash
   # プロジェクト名を置き換え
   # {{PROJECT_NAME}} → your-project-name
   ```

3. **プロジェクト固有のルール追加:**
   - CLAUDE.md に開発規約を追加
   - .claude/docs.md にドキュメント標準を追加
   - 必要に応じて .claude/skills/ に新しいスキルを追加
