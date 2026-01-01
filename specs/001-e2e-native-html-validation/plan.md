# Implementation Plan: E2Eテスト - ネイティブHTML変換検証

**Branch**: `001-e2e-native-html-validation` | **Date**: 2026-01-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-e2e-native-html-validation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

既存E2Eテストの「トートロジー」問題（自己生成HTMLの自己検証）を解決するため、ブラウザ自動化でnote.comエディタにMarkdownを直接入力し、ProseMirrorがネイティブに生成するHTMLをプレビューページから取得・検証するE2Eテストを実装する。

**現状の問題点:**
- 既存テスト（tests/e2e/test_markdown_conversion.py）はAPIでHTML更新し、そのHTMLを検証
- これは `markdown_to_html()` の出力を自己検証するトートロジー

**解決アプローチ:**
- エディタに直接Markdown記法を入力（キーボード操作）
- ProseMirrorのトリガーパターン（スペース）でMarkdown変換を発動
- プレビューページでnote.comがネイティブ生成したHTMLを検証

## Technical Context

**Language/Version**: Python 3.11+ (pyproject.toml: requires-python = ">=3.11")
**Primary Dependencies**:
- playwright>=1.40.0 (ブラウザ自動化)
- pytest>=8.4.1, pytest-asyncio>=0.23.0 (テストフレームワーク)
- fastmcp>=2.0.0 (MCPサーバー)
**Storage**: N/A (テストコードのみ)
**Testing**: pytest with pytest-asyncio (asyncio_mode = "auto")
**Target Platform**: Linux/macOS (開発環境)
**Project Type**: single (既存構造を維持)
**Performance Goals**: 1記法あたり10秒以内（SC-004）
**Constraints**:
- note.comへのネットワークアクセス必須
- 有効なセッション（認証済み）必須
- note_publish_articleは絶対に呼び出し禁止（FR-002）
**Scale/Scope**: 12個のMCPツール検証、4種類以上のMarkdown記法（SC-005）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 非交渉的 Articles（例外なし）

| Article | 要件 | 準拠状況 |
|---------|------|----------|
| **Article 1: Test-First Imperative** | テストを先に作成、ユーザー承認後に実装 | ✅ PASS - E2Eテスト仕様が先に定義済み |
| **Article 5: Code Quality Standards** | コミット前に `ruff check --fix . && ruff format . && mypy .` 実行必須 | ✅ PASS - 既存CI/CD基盤を使用 |
| **Article 6: Data Accuracy Mandate** | ハードコード禁止、明示的データソース | ✅ PASS - テストデータは動的生成 |
| **Article 7: DRY Principle** | コード重複禁止、既存実装の再利用 | ✅ PASS - 既存fixtures/helpers再利用 |
| **Article 9: Python Type Safety** | 全関数に型注釈、mypy通過必須 | ✅ PASS - 既存型注釈パターン継承 |
| **Article 11: SpecKit Naming** | `<issue-number>-<name>`形式 | ✅ PASS - `001-e2e-native-html-validation` |

### 交渉可能 Articles

| Article | 要件 | 準拠状況 |
|---------|------|----------|
| **Article 2: Documentation Integrity** | 仕様との整合性 | ✅ PASS - spec.md定義済み |
| **Article 3: MCP Protocol Compliance** | MCPスキーマ定義、Pydantic検証 | ✅ PASS - 既存MCPツールをテスト対象として使用 |
| **Article 4: Simplicity** | 最大3プロジェクト、不必要なラッパー禁止 | ✅ PASS - tests/e2e/配下に追加のみ |
| **Article 8: Refactoring Policy** | 既存コード修正優先 | ✅ PASS - 新規テスト追加、既存は維持 |
| **Article 10: Python Docstring** | Google-style docstring推奨 | ✅ PASS - 既存パターンに従う |

### ゲート判定: ✅ PASS - Phase 0に進行可能

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
tests/e2e/
├── conftest.py                    # 既存 - セッション・記事fixtures
├── helpers/
│   ├── validation.py              # 既存 - PreviewValidator
│   └── typing_helpers.py          # 新規 - キーボード入力ヘルパー
├── test_markdown_conversion.py    # 既存 - API経由テスト（維持）
└── test_native_html_validation.py # 新規 - ネイティブHTML検証テスト
```

**Structure Decision**: 既存のtests/e2e/配下に新規テストファイルとヘルパーを追加。
既存のconftest.py fixtures（real_session, draft_article, preview_page）を再利用し、
新規のtyping_helpers.pyでキーボード操作を抽象化する。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Constitution Checkで全Articles PASS のため、違反の正当化は不要。*
