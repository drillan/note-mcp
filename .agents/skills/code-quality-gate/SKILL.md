---
name: "code-quality-gate"
description: "\u30b3\u30fc\u30c9\u54c1\u8cea\u57fa\u6e96\u306e\u5b8c\u5168\u9075\u5b88\u3092\u4fdd\u8a3c\u3057\u307e\u3059\u3002\u30b3\u30df\u30c3\u30c8\u524d\u306e\u54c1\u8cea\u30c1\u30a7\u30c3\u30af\u3092\u81ea\u52d5\u5b9f\u884c\u3057\u3001\u30a8\u30e9\u30fc\u304c\u3042\u308b\u72b6\u614b\u3067\u306e\u30b3\u30df\u30c3\u30c8\u3092\u9632\u6b62\u3057\u307e\u3059\u3002"
---

# Code Quality Gate スキル

このスキルは、**Constitution Article 5: Code Quality Standards** を強制し、コード品質基準の完全遵守を保証します。

## 起動条件

以下の状況で自動起動します：

1. **コミット前**: `git commit` を実行する前の最終チェック
2. **PR作成前**: プルリクエストを作成する前
3. **品質問題検出時**: コードに品質問題がある可能性がある場合
4. **明示的な依頼**: ユーザーが品質チェックを依頼した場合

## 品質チェック項目

### 1. Ruff Linter

コードスタイルとベストプラクティスの検証

```bash
# エラーチェック
uv run ruff check .

# 自動修正
uv run ruff check --fix .
```

**チェック内容**:
- 未使用のインポート
- 未使用の変数
- コードスタイル違反
- セキュリティ問題
- パフォーマンス問題

### 2. Ruff Formatter

コードフォーマットの統一

```bash
# フォーマットチェック（差分表示）
uv run ruff format --check .

# 自動フォーマット
uv run ruff format .
```

**チェック内容**:
- インデント
- 行の長さ
- 空白の使用
- クォートの統一

### 3. Mypy Type Checker

静的型チェック

```bash
# 型チェック実行
uv run mypy .
```

**チェック内容**:
- 型アノテーションの存在（Article 9）
- 型の整合性
- `Any` 型の過剰使用
- `None` チェックの欠落

## 実行プロセス

### Quick Check（高速チェック）

```bash
# すべてのチェックを一度に実行
uv run ruff check . && uv run ruff format --check . && uv run mypy .
```

### Full Check with Auto-fix（自動修正付き完全チェック）

```bash
# 自動修正を適用して再チェック
uv run ruff check --fix . && uv run ruff format . && uv run mypy .
```

### Step-by-Step（段階的チェック）

問題を個別に解決したい場合：

```bash
# Step 1: Linter
uv run ruff check .

# Step 2: Formatter
uv run ruff format --check .

# Step 3: Type Checker
uv run mypy .
```

## 品質ゲート基準

### PASS条件

すべてのチェックがエラーなしで完了：

```
✓ ruff check: 0 errors
✓ ruff format: No changes needed
✓ mypy: Success: no issues found
```

### FAIL条件

いずれかのチェックでエラーが発生：

```
✗ ruff check: 3 errors found
✗ ruff format: 2 files would be reformatted
✗ mypy: Found 5 errors in 2 files
```

## エラー対応ガイド

### Ruff エラーの修正

```bash
# エラー一覧の確認
uv run ruff check .

# 自動修正可能なエラーを修正
uv run ruff check --fix .

# 手動修正が必要なエラーは個別対応
# エラーコードのドキュメントを参照
```

### Format エラーの修正

```bash
# 自動フォーマット適用
uv run ruff format .
```

### Mypy エラーの修正

| エラータイプ | 対応方法 |
|------------|---------|
| `missing return type` | 戻り値の型アノテーションを追加 |
| `missing argument type` | 引数の型アノテーションを追加 |
| `incompatible types` | 型の不整合を修正 |
| `None not allowed` | Optional型または None チェックを追加 |

**型アノテーション例**:

```python
# Before (エラー)
def greet(name):
    return f"Hello, {name}"

# After (修正)
def greet(name: str) -> str:
    return f"Hello, {name}"
```

## レポート形式

チェック完了後、以下の形式でレポート：

```
## Code Quality Gate Report

### チェック結果
| Tool | Status | Details |
|------|--------|---------|
| ruff check | ✓ PASS | 0 errors |
| ruff format | ✓ PASS | No changes |
| mypy | ✓ PASS | No issues |

### 総合判定: PASS

コミット/PR作成を進めてください。
```

または

```
## Code Quality Gate Report

### チェック結果
| Tool | Status | Details |
|------|--------|---------|
| ruff check | ✗ FAIL | 3 errors |
| ruff format | ✓ PASS | No changes |
| mypy | ✗ FAIL | 5 errors |

### 総合判定: FAIL

以下のエラーを修正してください：

1. ruff: E501 Line too long (src/auth.py:45)
2. ruff: F401 Unused import (src/utils.py:1)
3. mypy: Missing return type (src/auth.py:10)
...
```

## 注意事項

- **例外なし**: Article 5 は非交渉的原則
- **時間制約は理由にならない**: 品質を犠牲にしない
- **自動修正を活用**: 可能な限り自動修正を適用
- **ゲート通過必須**: PASSするまでコミット/PRは行わない

## 推奨ワークフロー

1. コードを書く
2. `uv run ruff check --fix . && uv run ruff format .` を実行
3. `uv run mypy .` を実行
4. エラーがあれば修正
5. すべてPASSしたらコミット

```bash
# 一連のコマンド
uv run ruff check --fix . && uv run ruff format . && uv run mypy . && git add . && git commit -m "message"
```

## Codex Tool Guidance

Claude `allowed-tools` metadata has been converted to guidance only. Use Codex file search, file editing, and shell commands as needed for this skill within the current session permissions.
