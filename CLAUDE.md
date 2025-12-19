# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

### Package Management

このセクションには、プロジェクトで使用するパッケージマネージャーとビルドシステムを記載してください。

例:
```bash
# 依存関係のインストール
<package-manager> install

# 開発用依存関係のインストール
<package-manager> install --dev

# 特定のグループをインストール
<package-manager> install --group <group-name>
```

### Running Tests

このセクションには、テストの実行方法を記載してください。

例:
```bash
# すべてのテストを実行
<test-command>

# 特定のテストファイルを実行
<test-command> tests/path/to/test_file.py

# 詳細出力付きで実行
<test-command> -v
```

### Code Quality

このセクションには、コード品質ツールの使用方法を記載してください。

例:
```bash
# Linterの実行
<linter> check .

# フォーマッターの実行
<formatter> format .

# 型チェックの実行
<type-checker> .

# コミット前の完全チェック（推奨）
<linter> check . && <formatter> format . && <type-checker> .
```

設定は `pyproject.toml` または各ツールの設定ファイルに記載してください。

### Type Safety

このセクションには、型安全性に関する要件を記載してください。

推奨事項:
- すべての関数、メソッド、変数に型アノテーションを付与
- 静的型チェックをコミット前に実行
- `Any`型の使用を避け、具体的な型を使用
- 型エラーは無視せず、必ず解決

## Development Principles

このセクションには、プロジェクトで遵守すべき開発原則を記載してください。

### Test-Driven Development (TDD)

テスト駆動開発を推奨します：

実装フロー:
1. ユニットテストを先に作成
2. テストをユーザーに承認してもらう
3. テストが失敗する（Redフェーズ）ことを確認
4. 実装してテストを通す（Greenフェーズ）
5. リファクタリング

テスト構成:
- 機能毎にテストファイルを作成
- 1機能 = 1テストファイルの対応
- テストファイル名は対象機能を明確に反映（例: `test_calculator.py` ← `calculator.py`）

### Code-Specification Consistency

実装とドキュメントの整合性を保ちます：

必須要件:
- 実装前に仕様を確認
- 仕様が曖昧な場合は実装を停止し、明確化を要求
- ドキュメント変更時はユーザー承認を取得
- 仕様更新完了後に実装着手

### Code Quality Standards

コード品質基準への完全準拠を推奨します：

品質チェック:
- コミット前に品質ツールを実行（リンター、フォーマッター、型チェッカー）
- すべてのエラーを解消してからコミット
- 時間制約を理由とした品質妥協は避ける

### Data Accuracy

データの正確性とトレーサビリティを保証します：

禁止事項:
- マジックナンバーや固定文字列の直接埋め込み
- 環境依存値の埋め込み
- 認証情報・APIキーのコード内保存
- データ取得失敗時の自動デフォルト値割り当て
- 推測に基づく値の生成

推奨事項:
- すべての固定値は名前付き定数として定義
- 設定値は専用の設定モジュールで一元管理
- 環境固有値は環境変数または設定ファイルで管理
- エラーは明示的に処理（例外を発生させる）

例:
```python
# ❌ 悪い例
timeout = 30  # ハードコード
if not data:
    data = "default"  # 暗黙的フォールバック

# ✅ 良い例
TIMEOUT_SECONDS = int(os.environ["API_TIMEOUT"])
if not data:
    raise ValueError("Required data is missing")
```

### DRY (Don't Repeat Yourself)

コードの重複を避けます：

実装前チェック:
- 既存の実装を検索・確認（Glob, Grepツールの活用）
- 類似機能の存在を確認
- 再利用可能なコンポーネントを特定

重複回避:
- 3回以上の繰り返しパターンは関数化・モジュール化
- 同一ロジックは共通化
- 設定駆動アプローチを検討

重複検出時:
- 作業を停止
- 既存実装の拡張可能性を評価
- リファクタリング計画を立案

### Refactoring Policy

既存コードの直接修正を優先します：

基本方針:
- V2、V3などのバージョン付きクラス作成は避ける
- 既存クラスを直接修正
- 後方互換性よりも設計の正しさを優先

リファクタリング前チェック:
- 影響範囲を特定（依存関係の分析）
- テストカバレッジを確認
- ドキュメントの更新計画を立案

## Key Development Guidelines

### Code Style

このセクションには、プロジェクトのコーディング規約を記載してください。

推奨事項:
- **命名規則**: クラスはPascalCase、関数/変数はsnake_case、定数はUPPER_SNAKE_CASE
- **型ヒント**: 型アノテーションを積極的に使用
- **Docstrings**: 標準的なフォーマット（例: Google-style）を使用
- **行の長さ**: プロジェクトで統一された最大文字数を設定
- **インポート**: ツールによる自動ソート（stdlib → サードパーティ → ローカル）

### Documentation Standards

このセクションには、ドキュメンテーション標準を記載してください。

推奨事項:
- 公開関数、クラス、モジュールには包括的なdocstringを記載
- 標準的なフォーマット（例: Google-style）を採用
- Docstringは型アノテーションと一致させる
- 複雑な関数には使用例を含める

### Testing Strategy

このセクションには、テスト戦略を記載してください。

推奨事項:
- **単体テスト**: 高速、外部依存なし（モックを使用）
- **統合テスト**: 中速、外部サービスをモック
- **E2Eテスト**: 実際の外部サービスを使用、適切にマーク
- **テストマーカー**: テストの種類や依存関係を示すマーカーを使用

## Documentation

ドキュメンテーションシステムを使用する場合、このセクションに設定を記載してください。

詳細なガイドラインは `@.claude/docs.md` を参照。

### File Locations

例:
- すべてのドキュメント: `docs/*.md`
- ドキュメント設定: `docs/conf.py`（Sphinxの場合）
- ビルドシステム: `docs/Makefile`（Sphinxの場合）

## Technology Stack Summary

このセクションには、プロジェクトで使用する主要な技術を記載してください。

例:
- **ランタイム**: Python X.X.X
- **パッケージマネージャー**: <package-manager>
- **テスト**: <test-framework> >= X.X.X
- **Linting**: <linter> >= X.X.X
- **型チェック**: <type-checker> >= X.X.X
- **ドキュメント**: <doc-generator> >= X.X.X（オプション）
